"""Zimmerplan → Reiter „Zimmer“: Zimmer finden und ansehen – eine Such-/Filterleiste für drei Ansichten.

* **Übersicht** – alle Zimmer als farbige Kacheln je Haus und Etage (bis 6.14 Reiter „Häuser“)
* **Karten**    – je Etage eine Spalte, je Zimmer eine Karte mit Status, Bewohnern und Zeitraum (wie der Gebäudeplan
  im Belegungssystem)
* **Liste**     – Tabelle zum Drucken, Kopieren und Bearbeiten (bis 6.14 „Zimmerliste“ im Reiter „Zimmer“)

Die Filter sind Chips mit Symbolen (an/aus), Seltenes steht unter „Filter“. Gefiltert wird für alle Ansichten mit
derselben Logik (``belegung/zimmerliste.filtern``); Ansicht und Haus werden gemerkt.
"""

from __future__ import annotations

from datetime import date
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .. import maengel as mg
from .. import speicher
from .. import zimmerliste as zl
from .. import zimmerplan as zp
from . import icons, theme
from .widgets import (DatumFeld, FlowLayout, Karte, Leer, Pille, Tabelle, knopf, label, leeren, mangel_farben,
                      mangel_html, mangel_icon)

HAEUSER = ["2", "3.1", "3.2", "3.3", "6"]
ANSICHTEN = [("uebersicht", "Übersicht", "raster", "Alle Zimmer als Kacheln – auf einen Blick"),
             ("karten", "Karten", "karten", "Je Etage eine Spalte, je Zimmer Status, Bewohner und Zeitraum"),
             ("liste", "Liste", "liste", "Tabelle zum Drucken, Kopieren und Bearbeiten")]
STATUS = [("", "Alle"), ("frei", "Frei"), ("belegt", "Belegt"), ("geplant", "Geplant"), ("gesperrt", "Gesperrt")]
SCHNELL = [("maengel", "Mängel", "ausrufe", "! Nur Zimmer mit offenen Mängeln – Bericht für das FM unter „Drucken“"),
           ("reno", "Renoviert", "farbrolle", "Renoviert (mit oder ohne Datum)"),
           ("Vinyl", "Vinyl", "boden", "Boden Vinyl – auch vermutet"),
           ("Teppich", "Teppich", "teppich", "Boden Teppich – auch laut ZKL"),
           ("tiere", "Tier", "pfote", "Tier-Zimmer"),
           ("doppel", "Doppel", "bett", "Doppelzimmer")]
KARTEN_MAX = 120          # mehr Karten auf einmal werden träge – dann hausweise

STATUS_PILLE = {"frei": ("Frei", "ok"), "teilweise": ("1 Bett frei", "knapp"), "belegt": ("Belegt", "neutral"),
                "geplant": ("Geplant", "akzent"), "gesperrt": ("Gesperrt", "ueber")}


def _status_farben() -> dict[str, tuple[str, str]]:
    t = theme.T
    return {"frei": (theme.alpha(t.ok, .20), t.text), "teilweise": (theme.alpha(t.knapp, .22), t.text),
            "belegt": (theme.alpha(t.text_3, .32), t.text),
            "geplant": (theme.alpha(t.kategorie.get("Reha", t.accent), .22), t.text),
            "gesperrt": (theme.alpha(t.ueber, .14), t.text_3)}


def _chip(text: str, icon: str | None = None, tip: str = "", pruefbar: bool = True) -> QPushButton:
    b = knopf(text, "chip", icon, tip or None)
    b.setCheckable(pruefbar)
    return b


class ZimmerFinder(QWidget):
    """Lebt im Zimmerplan; ``seite`` liefert Stand, Zustand und Druck/Excel-Helfer."""

    def __init__(self, seite):
        super().__init__()
        self.seite = seite
        self.z = seite.z
        e = speicher.einstellungen().get("zimmer_finder", {})
        self._ansicht = e.get("ansicht") if e.get("ansicht") in {a for a, *_ in ANSICHTEN} else "uebersicht"
        self._haus = e.get("haus") if e.get("haus") in HAEUSER else ""
        self._status = ""
        self._mehr: dict[str, object] = {"boeden": set(), "merkmale": set(), "renoviert": "alle", "gruppen": set(),
                                         "modus": "wohnt", "alle": False, "maengel": set()}
        self._zeilen: list[zl.Zeile] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # Zeile 1: Suche · Tag ············ Ansicht
        oben = QHBoxLayout()
        oben.setSpacing(8)
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Zimmer, Name, Notiz …")
        self.suche.setClearButtonEnabled(True)
        self.suche.addAction(icons.icon("suche", theme.T.text_3, 16), QLineEdit.LeadingPosition)
        self.suche.setMinimumWidth(180)
        self.suche.setMaximumWidth(320)
        self.suche.textChanged.connect(lambda _t: self.zeigen())
        oben.addWidget(self.suche, 1)
        self.tag = DatumFeld(date.today())
        self.tag.setToolTip("Status und Bewohner an diesem Tag")
        self.tag.geaendert.connect(lambda _d: self.zeigen())
        oben.addWidget(self.tag)
        oben.addStretch()
        self.ansicht_gruppe = QButtonGroup(self)
        self.ansicht_gruppe.setExclusive(True)
        self.ansicht_knoepfe: dict[str, QPushButton] = {}
        for schluessel, text, ic, tip in ANSICHTEN:
            b = _chip(text, ic, tip)
            b.setChecked(schluessel == self._ansicht)
            b.clicked.connect(lambda _=False, s=schluessel: self._ansicht_setzen(s))
            self.ansicht_gruppe.addButton(b)
            self.ansicht_knoepfe[schluessel] = b
            oben.addWidget(b)
        v.addLayout(oben)

        # Zeile 2: Status · Haus (je eine Auswahl)
        zwei = QWidget()
        zwei.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        fl = FlowLayout(zwei, abstand=6)
        self.status_knoepfe: dict[str, QPushButton] = {}
        sg = QButtonGroup(self)
        for schluessel, text in STATUS:
            b = _chip(text)
            b.setChecked(schluessel == self._status)
            b.clicked.connect(lambda _=False, s=schluessel: self._status_setzen(s))
            sg.addButton(b)
            self.status_knoepfe[schluessel] = b
            fl.addWidget(b)
        fl.addWidget(self._strich())
        self.haus_knoepfe: dict[str, QPushButton] = {}
        hg = QButtonGroup(self)
        for h in [""] + HAEUSER:
            b = _chip("Alle" if not h else h, "haus" if not h else None, "Alle Häuser" if not h else f"Haus {h}")
            b.setChecked(h == self._haus)
            b.clicked.connect(lambda _=False, h=h: self._haus_setzen(h))
            hg.addButton(b)
            self.haus_knoepfe[h] = b
            fl.addWidget(b)
        v.addWidget(zwei)

        # Zeile 3: Eigenschaften als Symbol-Chips (an/aus) · Filter ▾ · Zurücksetzen
        drei = QWidget()
        drei.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        fl3 = FlowLayout(drei, abstand=6)
        self.schnell: dict[str, QPushButton] = {}
        for schluessel, text, ic, tip in SCHNELL:
            b = _chip(text, ic, tip)
            b.toggled.connect(lambda _a: self.zeigen())
            self.schnell[schluessel] = b
            fl3.addWidget(b)
        self.b_filter = knopf("Filter", "chip", "filter", "Weitere Filter: andere Böden, Renovierung seit, Bad über "
                                                         "den Flur, Gästezimmer, Personengruppen …")
        self.m_filter = QMenu(self.b_filter)
        self.m_filter.aboutToShow.connect(self._filter_menue)
        self.b_filter.setMenu(self.m_filter)
        fl3.addWidget(self.b_filter)
        self.b_reset = knopf("Zurücksetzen", "ghost", "schliessen", "Alle Filter aus")
        self.b_reset.clicked.connect(self._zuruecksetzen)
        fl3.addWidget(self.b_reset)
        v.addWidget(drei)

        # Zeile 4: Kennzahlen der Auswahl ······ Drucken ▾ · Bearbeiten ▾
        vier = QHBoxLayout()
        vier.setSpacing(8)
        self.kpi = label("", "muted")
        self.kpi.setTextFormat(Qt.RichText)
        vier.addWidget(self.kpi, 1)
        self.b_drucken = knopf("Drucken", "ghost", "drucker", "Die angezeigten Zimmer drucken, als PDF oder für Excel")
        m = QMenu(self.b_drucken)
        m.addAction("Zimmerliste drucken …", lambda: self._drucken(False))
        m.addAction("Zimmerliste als PDF …", lambda: self._drucken(True))
        self.a_namen = m.addAction("Bewohner mitdrucken")
        self.a_namen.setCheckable(True)
        self.a_namen.setChecked(True)
        m.addSeparator()
        m.addAction("Kopieren (für Excel)", self._kopieren)
        m.addSeparator()
        fm = m.addMenu(icons.icon("ausrufe", theme.T.ueber, 16), "Mängelbericht für das FM")
        fm.addAction("Drucken …", lambda: self._maengel_drucken(False))
        fm.addAction("Als PDF …", lambda: self._maengel_drucken(True))
        fm.addAction("Als Excel zum Abarbeiten …", self._maengel_excel)
        fm.addAction("Kopieren (für eine Mail)", self._maengel_kopieren)
        fm.addSeparator()
        fm.addAction("Erledigte aus der FM-Excel übernehmen …", self._maengel_erledigt_einlesen)
        m.addSeparator()
        m.addAction("Belegung am Tag als Excel …", self._excel)
        self.b_drucken.setMenu(m)
        vier.addWidget(self.b_drucken)
        self.b_bearbeiten = knopf("Bearbeiten", "ghost", "neu", "Renovierung/Boden für markierte Zimmer setzen, "
                                                                 "Renovierungsliste einfügen")
        mb = QMenu(self.b_bearbeiten)
        mb.addAction("Eigenschaften der markierten Zimmer setzen …", self._eigenschaften_setzen)
        mb.addAction("Renovierungsliste einfügen …", self._renovierungen_einfuegen)
        self.b_bearbeiten.setMenu(mb)
        vier.addWidget(self.b_bearbeiten)
        v.addLayout(vier)

        # Ansichten
        self.w_uebersicht = QWidget()
        self.l_uebersicht = QVBoxLayout(self.w_uebersicht)
        self.l_uebersicht.setContentsMargins(0, 0, 0, 0)
        self.l_uebersicht.setSpacing(16)
        self.w_karten = QWidget()
        self.l_karten = QVBoxLayout(self.w_karten)
        self.l_karten.setContentsMargins(0, 0, 0, 0)
        self.l_karten.setSpacing(18)
        self.tab = Tabelle(["Zimmer", "Etage", "Merkmale", "Renoviert", "Boden", "Am Tag", "Notiz"], ["l"] * 7, dehnen=5)
        self.tab.setTextElideMode(Qt.ElideRight)
        self.tab.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tab.setToolTip("Mehrere Zeilen markieren (Strg/Umschalt) → „Bearbeiten“ · Doppelklick: Zimmerkarte")
        self.tab.cellDoubleClicked.connect(self._liste_oeffnen)
        self.w_liste = QWidget()
        lv = QVBoxLayout(self.w_liste)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.tab)
        self.hinweis_haus = label("", "klein")
        v.addWidget(self.hinweis_haus)
        for w in (self.w_uebersicht, self.w_karten, self.w_liste):
            v.addWidget(w)
        self.leer = Leer("suche", "Keine Zimmer für diese Auswahl", "Filter lockern oder „Zurücksetzen“.")
        v.addWidget(self.leer)
        self.legende = QWidget()
        self.l_legende = FlowLayout(self.legende, abstand=10)
        v.addWidget(self.legende)

    # ---- Bausteine ---------------------------------------------------------------------------

    @staticmethod
    def _strich() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setFixedWidth(9)
        f.setStyleSheet(f"color: {theme.alpha(theme.T.text_3, .45)};")
        return f

    def _merken(self) -> None:
        speicher.einstellung_setzen("zimmer_finder", {"ansicht": self._ansicht, "haus": self._haus})

    def _ansicht_setzen(self, s: str) -> None:
        self._ansicht = s
        self.ansicht_knoepfe[s].setChecked(True)
        self._merken()
        self.zeigen()

    def _status_setzen(self, s: str) -> None:
        self._status = s
        self.status_knoepfe[s].setChecked(True)
        self.zeigen()

    def _haus_setzen(self, h: str) -> None:
        self._haus = h
        self.haus_knoepfe[h].setChecked(True)
        self._merken()
        self.zeigen()

    def status_filtern(self, s: str) -> None:
        """Von außen (z. B. Kennzahl „frei“ im Kopf)."""
        self._status_setzen(s if s in self.status_knoepfe else "")

    def _filter_menue(self) -> None:
        m, mehr = self.m_filter, self._mehr
        m.clear()

        def schalter(menue, text, an, fn):
            a = menue.addAction(text, fn)
            a.setCheckable(True)
            a.setChecked(an)
            return a

        boden = m.addMenu("Boden")
        for b in [x for x in zl.BOEDEN if x not in ("Vinyl", "Teppich")] + ["unbekannt"]:
            schalter(boden, "Boden unbekannt" if b == "unbekannt" else b, b in mehr["boeden"],
                     lambda b=b: self._mehr_umschalten("boeden", b))
        from .. import maengel as mg

        mm = m.addMenu("Mangel")
        for st in (3, 2, 1):
            a = schalter(mm, f"{mg.STUFEN[st][3].capitalize()} – {mg.STUFEN[st][0]}", f"stufe:{st}" in mehr["maengel"],
                         lambda st=st: self._mehr_umschalten("maengel", f"stufe:{st}"))
            a.setIcon(mangel_icon(st))
        mm.addSeparator()
        for art, text in mg.KATALOG:
            schalter(mm, text, art in mehr["maengel"], lambda a=art: self._mehr_umschalten("maengel", a))
        reno = m.addMenu("Renovierung")
        jahr = date.today().year
        for text, wert in [("egal", "alle"), ("nicht renoviert / unbekannt", "nein")] + \
                [(f"renoviert seit {j}", f"seit:{j}") for j in range(jahr - 1, jahr - 6, -1)]:
            schalter(reno, text, mehr["renoviert"] == wert, lambda w=wert: self._mehr_setzen("renoviert", w))
        m.addSeparator()
        for k, text in (("maenner", "Bad über den Flur (nur Männer)"), ("gaeste", "Gästezimmer")):
            schalter(m, text, k in mehr["merkmale"], lambda k=k: self._mehr_umschalten("merkmale", k))
        m.addSeparator()
        gr = m.addMenu("Personengruppe")
        for modus, text in (("wohnt", "… wohnt dort"), ("darf", "… darf dort wohnen (Regeln)")):
            schalter(gr, text, mehr["modus"] == modus, lambda md=modus: self._mehr_setzen("modus", md))
        gr.addSeparator()
        for g in zp.GRUPPEN:
            schalter(gr, zp.GRUPPE_LABEL.get(g, g), g in mehr["gruppen"], lambda g=g: self._mehr_umschalten("gruppen", g))
        m.addSeparator()
        schalter(m, "Auch Zimmer außer Betrieb (Lager, Jugendhilfe …)", mehr["alle"],
                 lambda: self._mehr_setzen("alle", not mehr["alle"]))

    def _mehr_umschalten(self, art: str, wert: str) -> None:
        self._mehr[art] ^= {wert}
        self.zeigen()

    def _mehr_setzen(self, art: str, wert) -> None:
        self._mehr[art] = wert
        self.zeigen()

    def _zuruecksetzen(self) -> None:
        for b in self.schnell.values():
            b.blockSignals(True)
            b.setChecked(False)
            b.blockSignals(False)
        self._mehr = {"boeden": set(), "merkmale": set(), "renoviert": "alle", "gruppen": set(), "modus": "wohnt",
                      "alle": False, "maengel": set()}
        self.suche.blockSignals(True)
        self.suche.clear()
        self.suche.blockSignals(False)
        self._status_setzen("")

    def filter(self) -> zl.Filter:
        an = {k for k, b in self.schnell.items() if b.isChecked()}
        mehr = self._mehr
        return zl.Filter(haus=self._haus, renoviert="ja" if "reno" in an else mehr["renoviert"],
                         boeden=set(mehr["boeden"]) | ({"Vinyl", "Teppich"} & an),
                         merkmale=set(mehr["merkmale"]) | ({"tiere", "doppel"} & an), nur_internat=not mehr["alle"],
                         text=self.suche.text().strip(), status=self._status, gruppen=set(mehr["gruppen"]),
                         gruppen_modus=mehr["modus"],
                         maengel=set(mehr["maengel"]) | ({"*"} if "maengel" in an else set()))

    # ---- Anzeigen ----------------------------------------------------------------------------

    def zeigen(self) -> None:
        st = self.seite.stand
        if st is None:
            return
        f, tag = self.filter(), self.tag.datum()
        alle = zl.filtern(st, zl.Filter(nur_internat=f.nur_internat, haus=f.haus), tag)
        self._zeilen = sorted(zl.filtern(st, f, tag), key=lambda r: (zp._haus_sort(r.zimmer.haus), r.zimmer.nummer))
        # Zähler an den Status-Chips (für das gewählte Haus)
        n = {s: sum(1 for r in alle if r.status == s or (s == "frei" and r.status == "teilweise")) for s, _t in STATUS if s}
        mit_maengeln = sum(1 for r in alle if r.maengel)
        self.schnell["maengel"].setText(f"Mängel {mit_maengeln}" if mit_maengeln else "Mängel")
        for s, text in STATUS:
            self.status_knoepfe[s].setText(text if not s else f"{text} {n.get(s, 0)}")
        extra = bool(self._mehr["boeden"] or self._mehr["merkmale"] or self._mehr["gruppen"] or self._mehr["maengel"]
                     or self._mehr["renoviert"] != "alle" or self._mehr["alle"])
        self.b_filter.setProperty("aktiv", "true" if extra else "false")
        self.b_filter.style().unpolish(self.b_filter)
        self.b_filter.style().polish(self.b_filter)
        self.b_reset.setVisible(f.aktiv)
        # Kennzahlen wie im Gebäudeplan: Zimmer · belegt · frei · Auslastung
        z_n = len(self._zeilen)
        bel = sum(1 for r in self._zeilen if r.status in ("belegt", "geplant"))
        frei = sum(1 for r in self._zeilen if r.status in ("frei", "teilweise"))
        nutzbar = sum(1 for r in self._zeilen if r.status != "gesperrt")
        quote = f" · Auslastung <b>{bel / nutzbar:.0%}</b>".replace("%", " %") if nutzbar else ""
        self.kpi.setText(f"<b>{z_n}</b> Zimmer · <b>{bel}</b> belegt/geplant · <b>{frei}</b> frei{quote}"
                         f" · {tag:%d.%m.%Y}")
        self.b_bearbeiten.setVisible(self._ansicht == "liste")
        self.leer.setVisible(not self._zeilen)
        self.legende.setVisible(self._ansicht == "uebersicht" and bool(self._zeilen))
        for schluessel, w in zip([a for a, *_ in ANSICHTEN], (self.w_uebersicht, self.w_karten, self.w_liste)):
            w.setVisible(schluessel == self._ansicht and bool(self._zeilen))
        self.hinweis_haus.setVisible(False)
        {"uebersicht": self._uebersicht, "karten": self._karten, "liste": self._liste}[self._ansicht](tag)

    def _nach_haus(self) -> dict[str, list[zl.Zeile]]:
        erg: dict[str, list[zl.Zeile]] = {}
        for r in self._zeilen:
            erg.setdefault(r.zimmer.haus, []).append(r)
        return erg

    def _tooltip(self, r: zl.Zeile, tag: date) -> str:
        z = r.zimmer
        zeilen = [f"<b>{z.kurz}</b> · {zp.flur_text(z)} · {STATUS_PILLE.get(r.status, (r.status,))[0]}"]
        for b in r.belegungen:
            text, _art = zp.balken_text(b)
            zeilen.append(f"{escape(text)} bis {b.bis:%d.%m.%Y}")
        if r.status in ("frei", "teilweise"):
            bis = self.seite.stand.lage.frei_bis(z.id, tag)
            zeilen.append(f"frei bis {bis:%d.%m.%Y}" if bis else "frei ohne Folgebelegung")
        if r.maengel:
            st = mg.stufe(r.maengel)
            zeilen.append(f"{mangel_html(st)} <b>{mg.stufe_text(st)}</b>"
                          + (" – wird nicht zugeteilt" if st == 3 else ""))
            zeilen.append(escape("; ".join(f"{m.text} (seit {m.seit:%d.%m.})" for m in r.maengel)))
        reno = zl.reno_text(z)
        if reno or r.boden:
            zeilen.append(" · ".join(x for x in (f"renoviert {reno}" if reno else "", r.boden) if x))
        zeilen.append("<i>Klicken für Details</i>")
        return "<br>".join(zeilen)

    def _oeffnen(self, zid: str) -> None:
        from .zimmerkarte import karte_oeffnen

        karte_oeffnen(self.seite, self.z, zid)

    # Übersicht: farbige Kacheln je Etage
    def _uebersicht(self, tag: date) -> None:
        leeren(self.l_uebersicht)
        leeren(self.l_legende)
        farben = _status_farben()
        for status, text in (("frei", "frei"), ("teilweise", "1 Bett frei (Doppelzimmer)"), ("belegt", "belegt"),
                             ("geplant", "geplant"), ("gesperrt", "gesperrt")):
            bg, fg = farben[status]
            muster = label(text, "klein")
            muster.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:5px; padding:2px 7px;")
            self.l_legende.addWidget(muster)
        self.l_legende.addWidget(label("D Doppel · T Tier · M Bad über den Flur · G Gäste · R renoviert", "klein"))
        for st in (3, 2, 1):                       # Mängel-Stufen: Zeichen + Farbe (nicht nur Farbe)
            bg, fg = mangel_farben(st)
            muster = label(f"! {mg.STUFEN[st][0]}", "klein")
            muster.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:5px; padding:2px 8px; font-weight:800;")
            self.l_legende.addWidget(muster)
        for haus, zeilen in self._nach_haus().items():
            frei = sum(1 for r in zeilen if r.status in ("frei", "teilweise"))
            karte = Karte(f"Haus {haus}", f"{len(zeilen)} Zimmer · {frei} frei am {tag:%d.%m.%Y}")
            karte.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            gitter = QGridLayout()
            gitter.setHorizontalSpacing(18)
            gitter.setVerticalSpacing(10)
            etagen = sorted({r.zimmer.etage for r in zeilen}, key=zp._etage_sort, reverse=True)
            for i, e in enumerate(etagen):
                gitter.addWidget(label(zp.etage_text(e), "fett"), i, 0, Qt.AlignTop)
                feld = QWidget()
                fl = FlowLayout(feld, abstand=4)
                for r in (r for r in zeilen if r.zimmer.etage == e):
                    z = r.zimmer
                    bg, fg = farben.get(r.status, farben["belegt"])
                    merk = "".join(k for k, an in (("D", z.betten > 1), ("T", z.tiere), ("M", z.nur_maenner),
                                                   ("G", z.gaeste), ("R", bool(z.renoviert))) if an)
                    st = mg.stufe(r.maengel)
                    b = QPushButton(f"{z.nr} {merk}".strip())
                    b.setCursor(Qt.PointingHandCursor)
                    # Mängel: Warndreieck in Signalfarbe (gelb/orange/rot) + Rand in derselben Farbe,
                    # bei „nicht bewohnbar“ ganz rot umrandet
                    mb, _mf = mangel_farben(st)
                    if st:
                        b.setIcon(mangel_icon(st, 15))
                        b.setAccessibleDescription(f"Mangel: {mg.stufe_text(st)}")
                    rand = ("border:none;" if not st else f"border:none; border-left:6px solid {mb};" if st < 3
                            else f"border:3px solid {mb}; border-left:6px solid {mb};")
                    b.setStyleSheet(f"QPushButton {{ background:{bg}; color:{fg}; {rand} border-radius:6px; "
                                    f"padding:4px 7px; font-size:11.5px; {'font-weight:700;' if st >= 2 else ''} }} "
                                    f"QPushButton:hover {{ border:1px solid {theme.T.accent}; }}")
                    b.setToolTip(self._tooltip(r, tag))
                    b.clicked.connect(lambda _=False, zid=z.id: self._oeffnen(zid))
                    fl.addWidget(b)
                gitter.addWidget(feld, i, 1)
            gitter.setColumnStretch(1, 1)
            karte.inhalt.addLayout(gitter)
            self.l_uebersicht.addWidget(karte)

    # Karten: je Etage eine Spalte, je Zimmer eine Karte
    def _karten(self, tag: date) -> None:
        leeren(self.l_karten)
        t = theme.T
        haeuser = self._nach_haus()
        if not self._haus and len(self._zeilen) > KARTEN_MAX and len(haeuser) > 1:   # wie im Gebäudeplan: hausweise
            erstes = next(iter(haeuser))
            self.hinweis_haus.setText(f"Karten zeigen bei vielen Zimmern ein Haus auf einmal – hier Haus {erstes}. "
                                      "Oben ein Haus wählen oder die Auswahl mit Filtern eingrenzen.")
            self.hinweis_haus.setVisible(True)
            haeuser = {erstes: haeuser[erstes]}
        for haus, zeilen in haeuser.items():
            bel = sum(1 for r in zeilen if r.status in ("belegt", "geplant"))
            nutzbar = sum(1 for r in zeilen if r.status != "gesperrt")
            kopf = QHBoxLayout()
            ic = QLabel()
            ic.setPixmap(icons.pixmap("haus", t.accent, 18))
            kopf.addWidget(ic)
            kopf.addWidget(label(f"Haus {haus}", "abschnitt"))
            kopf.addSpacing(12)
            kopf.addWidget(label(f"{len(zeilen)} Zimmer · {bel} belegt · "
                                 + (f"{bel / nutzbar:.0%}".replace("%", " %") if nutzbar else "–") + " Auslastung",
                                 "muted"))
            kopf.addStretch()
            self.l_karten.addLayout(kopf)
            spalten = QWidget()
            fl = FlowLayout(spalten, abstand=14)
            for e in sorted({r.zimmer.etage for r in zeilen}, key=zp._etage_sort):
                etage = [r for r in zeilen if r.zimmer.etage == e]
                e_bel = sum(1 for r in etage if r.status in ("belegt", "geplant"))
                spalte = Karte(zp.etage_text(e), f"{len(etage)} Zimmer · {e_bel} belegt", abstand=12)
                spalte.setFixedWidth(272)
                for r in etage:
                    spalte.inhalt.addWidget(self._zimmerkarte(r, tag))
                fl.addWidget(spalte)
            self.l_karten.addWidget(spalten)

    def _zimmerkarte(self, r: zl.Zeile, tag: date) -> QWidget:
        t, z = theme.T, r.zimmer
        k = QFrame()
        k.setObjectName("zkarte")
        k.setCursor(Qt.PointingHandCursor)
        k.setStyleSheet(f"QFrame#zkarte {{ border:1px solid {theme.alpha(t.text_3, .30)}; border-radius:10px; }}"
                        f"QFrame#zkarte:hover {{ border-color:{t.accent}; }}")
        k.setToolTip(self._tooltip(r, tag))
        k.mousePressEvent = lambda _e, zid=z.id: self._oeffnen(zid)
        v = QVBoxLayout(k)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)
        oben = QHBoxLayout()
        oben.setSpacing(6)
        oben.addWidget(label(f"<b>{escape(z.kurz)}</b>", "fett"))
        oben.addWidget(label(f"{z.betten} Bett" + ("en" if z.betten > 1 else ""), "klein"))
        oben.addStretch()
        text, stufe = STATUS_PILLE.get(r.status, (r.status, "neutral"))
        oben.addWidget(Pille(text, stufe))
        v.addLayout(oben)
        merkmale = [x for x in (f"renoviert {zl.reno_text(z)}" if z.renoviert else "", r.boden,
                                "Tier" if z.tiere else "", "Bad über den Flur" if z.nur_maenner else "",
                                "Gäste" if z.gaeste else "") if x]
        if merkmale:
            v.addWidget(label(escape(" · ".join(merkmale)), "klein", umbruch=True))
        if r.maengel:
            st = mg.stufe(r.maengel)
            mang = label(mangel_html(st) + " " + escape(" · ".join(m.text for m in sorted(r.maengel, key=lambda m: -m.stufe))),
                         "klein", umbruch=True)
            mang.setTextFormat(Qt.RichText)
            mang.setStyleSheet(f"color: {mangel_farben(st)[0] if st >= 2 else t.text};")
            v.addWidget(mang)
        for b in r.belegungen:
            zeile = QHBoxLayout()
            zeile.setSpacing(8)
            ic = QLabel()
            ic.setPixmap(icons.pixmap("schloss" if b.art == "gesperrt" else "person",
                                      t.ueber if b.art == "gesperrt" else t.accent, 16))
            zeile.addWidget(ic, 0, Qt.AlignTop)
            text = QVBoxLayout()
            text.setSpacing(0)
            if b.art == "gesperrt":
                text.addWidget(label(escape(b.grund or "gesperrt"), "fett", umbruch=True))
            else:
                name = zp.anzeige_name(b.name) if b.name != zp.PIVOT_NAME else "gebucht (Zimmer-Pivot)"
                text.addWidget(label(f"<b>{escape(name)}</b>" + (f" ({escape(b.massnahme)})" if b.massnahme else ""),
                                     umbruch=True))
            text.addWidget(label(f"{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y}" + (" · geplant" if b.art == "geplant" else ""),
                                 "klein"))
            zeile.addLayout(text, 1)
            v.addLayout(zeile)
        for lbl in k.findChildren(QLabel):        # Klick auf den Text öffnet ebenfalls die Zimmerkarte
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        return k

    # Liste: Tabelle
    def _liste(self, _tag: date) -> None:
        self.tab.fuellen([[r.zimmer.kurz, zp.flur_text(r.zimmer).split(" · ", 1)[-1], zl.merkmal_kurz(r.zimmer),
                           zl.reno_text(r.zimmer) or "–", r.boden or "–", r.heute, r.zimmer.notiz] for r in self._zeilen])
        self.tab.hoehe_anpassen(18)

    def _ansicht_zeilen(self) -> list[zl.Zeile]:
        if self._ansicht != "liste":
            return list(self._zeilen)
        return [self._zeilen[self.tab.daten_zeile(r)] for r in range(self.tab.rowCount())
                if self.tab.daten_zeile(r) < len(self._zeilen)]

    def _liste_oeffnen(self, r: int, _c: int = 0) -> None:
        i = self.tab.daten_zeile(r)
        if 0 <= i < len(self._zeilen):
            self._oeffnen(self._zeilen[i].zimmer.id)

    # ---- Aktionen ----------------------------------------------------------------------------

    def _drucken(self, pdf: bool) -> None:
        self.seite._html_ausgeben(zl.liste_html(self._ansicht_zeilen(), self.filter(), self.a_namen.isChecked()), True,
                                  f"Zimmerliste_{date.today():%Y-%m-%d}.pdf" if pdf else None)

    def _maengel_offen(self) -> list:
        """Offene Mängel der angezeigten Zimmer (ohne Mängel-Filter: alle offenen)."""
        return [m for r in self._ansicht_zeilen() for m in r.maengel]

    def nur_maengel(self) -> None:
        """Von außen (Kennzahl „! N Zimmer mit Mängeln“): alle Häuser, nur Zimmer mit Mängeln."""
        self._zuruecksetzen()
        if hasattr(self, "_haus_setzen"):
            self._haus_setzen("")
        self.schnell["maengel"].setChecked(True)

    def _bericht_daten(self) -> tuple[list, dict, dict]:
        kurz = {z.id: z.kurz for z in self.seite.stand.zimmer}
        status = {r.zimmer.id: r.status for r in self._ansicht_zeilen()}
        return self._maengel_offen(), kurz, status

    def _maengel_drucken(self, pdf: bool) -> None:
        from .. import maengel as mg

        offen, kurz, status = self._bericht_daten()
        self.seite._html_ausgeben(mg.fm_html(offen, lambda zid: kurz.get(zid, zid), status), True,
                                  f"Maengelbericht_FM_{date.today():%Y-%m-%d}.pdf" if pdf else None)

    def _maengel_excel(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from .. import maengel as mg

        offen, kurz, status = self._bericht_daten()
        pfad, _ = QFileDialog.getSaveFileName(self, "Mängelbericht als Excel", f"Maengelbericht_FM_{date.today():%Y-%m-%d}.xlsx",
                                              "Excel (*.xlsx)")
        if not pfad:
            return
        try:
            n = mg.fm_excel(pfad, offen, lambda zid: kurz.get(zid, zid), status)
        except OSError as e:
            self.z.meldung.emit(f"Konnte nicht speichern (ist die Datei noch in Excel offen?): {e}", "fehler")
            return
        self.z.meldung.emit(f"{n} Mängel gespeichert. Das FM trägt „erledigt am“ ein – danach hier "
                            "„Erledigte aus der FM-Excel übernehmen“.", "ok")

    def _maengel_erledigt_einlesen(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from .. import maengel as mg

        pfad, _ = QFileDialog.getOpenFileName(self, "Ausgefüllte FM-Excel wählen", "", "Excel (*.xlsx)")
        if not pfad:
            return
        try:
            eintraege, fehler = mg.fm_erledigte_lesen(pfad)
        except Exception as e:          # noqa: BLE001 – kaputte/fremde Datei: Meldung statt Absturz
            self.z.meldung.emit(f"Datei konnte nicht gelesen werden: {e}", "fehler")
            return
        kurz = {z.id: z.kurz for z in self.seite.stand.zimmer}
        offen = {(m.zimmer, m.art) for m in mg.offen()}
        neu = [e for e in eintraege if (e[0], e[1]) in offen]
        if not neu:
            self.z.meldung.emit("Keine neuen erledigten Mängel in der Datei" + (f" ({len(fehler)} unlesbar)" if fehler else "")
                                + ".", "info")
            return
        liste = "<br>".join(f"{kurz.get(z, z)}: {mg.NAMEN.get(a, a)} – erledigt {d:%d.%m.%Y}" + (f" ({b})" if b else "")
                            for z, a, d, b in neu[:25]) + (f"<br>… und {len(neu) - 25} weitere" if len(neu) > 25 else "")
        if fehler:
            liste += "<br><br>Nicht lesbar (bitte von Hand): " + ", ".join(fehler[:10])
        if QMessageBox.question(self, "Erledigte übernehmen", f"{len(neu)} Mängel als behoben markieren?<br><br>{liste}") \
                != QMessageBox.Yes:
            return
        n = mg.erledigte_uebernehmen(neu)
        self.z.meldung.emit(f"{n} Mängel als behoben übernommen (Verlauf bleibt erhalten).", "ok")
        self.z.zimmer_geaendert.emit()
        self.zeigen()

    def _maengel_kopieren(self) -> None:
        from PySide6.QtGui import QGuiApplication

        from .. import maengel as mg

        offen = self._maengel_offen()
        kurz = {z.id: z.kurz for z in self.seite.stand.zimmer}
        QGuiApplication.clipboard().setText(mg.fm_text(offen, lambda zid: kurz.get(zid, zid)))
        self.z.meldung.emit(f"{len(offen)} Mängel kopiert – in die Mail an das FM einfügen (Strg+V).", "ok")

    def _kopieren(self) -> None:
        from PySide6.QtGui import QGuiApplication

        zeilen = ["Zimmer\tEtage\tMerkmale\tRenoviert\tBoden\tAm Tag\tNotiz"]
        for r in self._ansicht_zeilen():
            zeilen.append("\t".join([r.zimmer.kurz, zp.flur_text(r.zimmer), zl.merkmal_kurz(r.zimmer),
                                     zl.reno_text(r.zimmer), r.boden, r.heute, r.zimmer.notiz]))
        QGuiApplication.clipboard().setText("\n".join(zeilen))
        self.z.meldung.emit(f"{len(zeilen) - 1} Zimmer kopiert – in Excel einfügen (Strg+V).", "ok")

    def _excel(self) -> None:
        tag = self.tag.datum()
        pfad = self.seite._speicherort(f"Freie_Zimmer_{tag:%Y-%m-%d}.xlsx")
        if pfad:
            self.seite._excel_schreiben(pfad, f"Belegung am {tag:%d.%m.%Y}", [], tag)

    def _gewaehlt(self) -> list:
        sel = self.tab.selectionModel()
        reihen = sorted({self.tab.daten_zeile(i.row()) for i in sel.selectedRows()}) if sel else []
        return [self._zeilen[r].zimmer for r in reihen if r < len(self._zeilen)]

    def _eigenschaften_setzen(self) -> None:
        from .dialoge import ZimmerEigenschaftenDialog

        zimmer = self._gewaehlt()
        if not zimmer:
            QMessageBox.information(self, "Eigenschaften setzen", "Bitte zuerst in der Liste eine oder mehrere Zeilen "
                                    "markieren (Strg/Umschalt + Klick).")
            return
        if ZimmerEigenschaftenDialog(self.seite.stand, zimmer, self).exec():
            self.z.meldung.emit(f"Eigenschaften für {len(zimmer)} Zimmer gespeichert.", "ok")
            self.seite._nach_aenderung()

    def _renovierungen_einfuegen(self) -> None:
        from .dialoge import RenovierungenDialog

        if RenovierungenDialog(self.seite.stand, self).exec():
            self.seite._nach_aenderung()
