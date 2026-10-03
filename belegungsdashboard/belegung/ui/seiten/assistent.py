"""Chat mit dem Assistenten."""

from __future__ import annotations

import html
import re
from datetime import date

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ... import speicher
from ...assistent import Antwort, Assistent
from ...assistent.antworten import BEISPIELE
from ...assistent.llm import Einstellungen, backend_erstellen
from .. import icons, theme
from ..basis import Seite, Worker, Zustand
from ..widgets import FlowLayout, Pille, knopf, label, leeren


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def _tabelle_html(kopf: list[str], zeilen: list[list[str]]) -> str:
    th = theme.T
    rechts = [i > 0 and all(re.fullmatch(r"[\d.,%+−\-–± ()a-zA-ZäÄ]*", str(z[i]) or "") and re.search(r"\d", str(z[i]) or "")
                            for z in zeilen if i < len(z)) for i in range(len(kopf))]
    teile = ['<table cellspacing="0" cellpadding="0" style="margin-top:8px; border-collapse:collapse;">', "<tr>"]
    for i, k in enumerate(kopf):
        teile.append(f'<th nowrap align="{"right" if rechts[i] else "left"}" style="color:{th.text_3}; font-size:11.5px; '
                     f'font-weight:600; padding:6px 14px 6px 0; border-bottom:1px solid {th.border_strong};">{html.escape(k)}</th>')
    teile.append("</tr>")
    for z in zeilen:
        teile.append("<tr>")
        for i, wert in enumerate(z):
            teile.append(f'<td nowrap align="{"right" if i < len(rechts) and rechts[i] else "left"}" style="padding:6px 14px 6px 0; '
                         f'border-bottom:1px solid {th.border};">{_inline(str(wert))}</td>')
        teile.append("</tr>")
    teile.append("</table>")
    return "".join(teile)


_LISTE = re.compile(r"^\s*[-•*]\s+")


def markdown_html(text: str) -> str:
    """Kleiner Markdown-Umsetzer für Antworten (fett, kursiv, Listen, Tabellen, Absätze)."""
    zeilen = text.strip().splitlines()
    ausgabe, i = [], 0
    while i < len(zeilen):
        z = zeilen[i].rstrip()
        if z.startswith("|") and i + 1 < len(zeilen) and re.match(r"^\|?\s*:?-{2,}", zeilen[i + 1].strip()):
            kopf = [c.strip() for c in z.strip("|").split("|")]
            i += 2
            daten = []
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                daten.append([c.strip() for c in zeilen[i].strip().strip("|").split("|")])
                i += 1
            ausgabe.append(_tabelle_html(kopf, daten))
            continue
        if _LISTE.match(z):
            punkte = []
            while i < len(zeilen) and _LISTE.match(zeilen[i]):
                punkte.append("<li>" + _inline(_LISTE.sub("", zeilen[i])) + "</li>")
                i += 1
            ausgabe.append(f'<ul style="margin:4px 0 4px -18px;">{"".join(punkte)}</ul>')
            continue
        if re.match(r"^#{1,4}\s", z):
            ausgabe.append(f"<b>{_inline(z.lstrip('#').strip())}</b><br>")
        elif z.strip():
            ausgabe.append(_inline(z) + "<br>")
        else:
            ausgabe.append("<br>")
        i += 1
    html_text = "".join(ausgabe)
    return re.sub(r"(<br>)+$", "", html_text)


class Blase(QFrame):
    def __init__(self, art: str, inhalt_html: str, fuss: str | None = None, text_kopie: str | None = None):
        super().__init__()
        self.setProperty("blase", art)
        if art == "nutzer":
            self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 11, 15, 10)
        lay.setSpacing(6)
        self.text = QLabel(inhalt_html)
        self.text.setTextFormat(Qt.RichText)
        self.text.setWordWrap(art != "nutzer" or len(inhalt_html) > 70)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        lay.addWidget(self.text)
        if fuss or text_kopie:
            unten = QHBoxLayout()
            unten.setSpacing(6)
            if fuss:
                unten.addWidget(Pille(fuss, "akzent" if fuss.startswith("KI") else "neutral"))
            unten.addStretch()
            if text_kopie:
                kopie = knopf("", "icon", "kopieren", "Antwort kopieren")
                kopie.clicked.connect(lambda: QGuiApplication.clipboard().setText(text_kopie))
                unten.addWidget(kopie)
            lay.addLayout(unten)
        self.setMaximumWidth(760)


class Tippen(QFrame):
    def __init__(self, text: str):
        super().__init__()
        self.setProperty("blase", "hinweis")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 10, 15, 10)
        self._label = label("", "muted")
        lay.addWidget(self._label)
        self._basis, self._n = text, 0
        self._timer = QTimer(self, interval=380, timeout=self._tick)
        self._timer.start()
        self._tick()

    def _tick(self):
        self._n = (self._n + 1) % 4
        self._label.setText(self._basis + " " + "●" * self._n + "○" * (3 - self._n))


class AssistentSeite(Seite):
    titel = "Assistent"
    untertitel = "Fragen zur Belegung in normaler Sprache stellen"
    zeigt_filter = False
    zeigt_bezug = False
    scrollbar = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.assistent: Assistent | None = None
        self.verlauf: list[tuple[str, str]] = []
        self._worker: Worker | None = None
        self._tippen: Tippen | None = None
        self._historie: list[str] = []
        self._hist_pos = 0
        self.lay.setContentsMargins(28, 4, 28, 20)

        leiste = QHBoxLayout()
        self.modus = Pille("", "neutral")
        leiste.addWidget(self.modus)
        leiste.addStretch()
        neu = knopf("Neues Gespräch", "ghost", "neu")
        neu.clicked.connect(self.neues_gespraech)
        leiste.addWidget(neu)
        self.lay.addLayout(leiste)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        verlauf = QWidget()
        verlauf.setObjectName("seiteninhalt")
        self.scroll.setWidget(verlauf)
        self.chat = QVBoxLayout(verlauf)
        self.chat.setContentsMargins(0, 8, 8, 8)
        self.chat.setSpacing(12)
        self.chat.addStretch()
        self.lay.addWidget(self.scroll, 1)
        self.scroll.verticalScrollBar().rangeChanged.connect(lambda _a, b: self.scroll.verticalScrollBar().setValue(b))

        self.vorschlaege = QWidget()
        self.vorschlaege_lay = FlowLayout(self.vorschlaege)
        self.lay.addWidget(self.vorschlaege)

        eingabe = QHBoxLayout()
        eingabe.setSpacing(8)
        self.feld = QLineEdit()
        self.feld.setObjectName("chat_eingabe")
        self.feld.setPlaceholderText("z. B. „Wie viele Plätze sind im November in Goslar frei?“")
        self.feld.returnPressed.connect(self.senden)
        self.feld.installEventFilter(self)
        eingabe.addWidget(self.feld, 1)
        self.btn = knopf("Senden", "primary", "senden")
        self.btn.clicked.connect(self.senden)
        self.btn.setMinimumHeight(42)
        eingabe.addWidget(self.btn)
        self.lay.addLayout(eingabe)
        self.fusszeile = label("", "klein")
        self.lay.addWidget(self.fusszeile)
        zustand.daten_geaendert.connect(self._daten)
        self._willkommen()

    # ---- Zustand ----------------------------------------------------------------------------

    def _ki_einstellungen(self) -> Einstellungen:
        return Einstellungen.aus_dict(speicher.einstellungen().get("ki", {}))

    def _modus_anzeigen(self) -> None:
        e = self._ki_einstellungen()
        if e.backend == "claude":
            self.modus.setzen("akzent", "Datenantworten + KI (Claude)")
            self.fusszeile.setText("Zahlen stammen immer aus den geladenen Daten. Für freie Fragen wird Claude genutzt – "
                                   "übertragen werden nur Frage und die abgefragten Kennzahlen, keine Rohdaten.")
        elif e.backend == "lokal":
            self.modus.setzen("akzent", f"Datenantworten + lokale KI ({e.lokal_modell})")
            self.fusszeile.setText("Zahlen stammen immer aus den geladenen Daten. Freie Fragen beantwortet ein lokales Modell – nichts verlässt das Netzwerk.")
        else:
            self.modus.setzen("neutral", "Datenantworten (offline)")
            self.fusszeile.setText("Antworten werden direkt aus den Daten berechnet – offline. Für freie Fragen lässt sich "
                                   "unter Einstellungen → KI ein Sprachmodell zuschalten.")

    def _daten(self) -> None:
        if self.z.ds is None:
            return
        if self.assistent is None:
            self.assistent = Assistent(self.z.ds)
        else:
            self.assistent.daten_setzen(self.z.ds)

    def showEvent(self, e):
        super().showEvent(e)
        self._modus_anzeigen()
        self.feld.setFocus()

    def aktualisieren(self) -> None:
        if self.assistent:
            self.assistent.brutto_standard = self.z.brutto

    def eventFilter(self, obj, e):
        if obj is self.feld and e.type() == QEvent.KeyPress and self._historie:
            if e.key() == Qt.Key_Up:
                self._hist_pos = max(0, self._hist_pos - 1)
                self.feld.setText(self._historie[self._hist_pos])
                return True
            if e.key() == Qt.Key_Down:
                self._hist_pos = min(len(self._historie), self._hist_pos + 1)
                self.feld.setText(self._historie[self._hist_pos] if self._hist_pos < len(self._historie) else "")
                return True
        return super().eventFilter(obj, e)

    # ---- Chat -----------------------------------------------------------------------------

    def _einfuegen(self, widget: QWidget, rechts: bool = False) -> QHBoxLayout:
        zeile = QHBoxLayout()
        if rechts:
            zeile.addStretch(1)
            zeile.addWidget(widget)
        else:
            zeile.addWidget(widget, 4)
            zeile.addStretch(1)
        self.chat.insertLayout(self.chat.count(), zeile)
        return zeile

    def _willkommen(self) -> None:
        karte = QFrame()
        karte.setProperty("blase", "assistent")
        karte.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        v = QVBoxLayout(karte)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(8)
        kopf = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(icons.pixmap("funke", theme.T.accent, 20))
        kopf.addWidget(ic)
        kopf.addWidget(label("Hallo! Was möchtest du wissen?", "kartentitel"))
        kopf.addStretch()
        v.addLayout(kopf)
        v.addWidget(label("Ich rechne jede Antwort direkt aus den geladenen Daten: Belegung, freie Plätze, Auslastung, "
                          "Prognosen mit Spanne, Anreisen, Mieter und Häuser – für einen Tag, einen Monat oder einen "
                          "Zeitraum. Folgefragen wie „und Goslar?“ gehen auch.", "muted", umbruch=True))
        karte.setMaximumWidth(760)
        self._einfuegen(karte)
        self._vorschlaege_setzen(BEISPIELE)

    def _vorschlaege_setzen(self, texte: list[str]) -> None:
        leeren(self.vorschlaege_lay)
        for t in texte[:6]:
            chip = knopf(t, "chip")
            chip.clicked.connect(lambda _=False, t=t: self.senden(t))
            self.vorschlaege_lay.addWidget(chip)
        self.vorschlaege.setVisible(bool(texte))

    def neues_gespraech(self) -> None:
        leeren(self.chat)
        self.chat.addStretch()
        self.verlauf.clear()
        if self.assistent:
            self.assistent.zuruecksetzen()
        self._willkommen()

    def senden(self, text: str | None = None) -> None:
        frage = (text if isinstance(text, str) else self.feld.text()).strip()
        if not frage or (self._worker and self._worker.isRunning()):
            return
        if self.z.ds is None or self.assistent is None:
            self.z.meldung.emit("Es sind noch keine Daten geladen.", "warnung")
            return
        self.feld.clear()
        self._historie.append(frage)
        self._hist_pos = len(self._historie)
        self._einfuegen(Blase("nutzer", html.escape(frage)), rechts=True)
        self.assistent.brutto_standard = self.z.brutto

        try:
            antwort = self.assistent.beantworte(frage)
        except Exception as exc:  # Datenfehler sichtbar machen statt abzustürzen
            antwort = Antwort(f"Bei der Berechnung ist ein Fehler aufgetreten: {exc}", quelle="hinweis")
        if antwort is not None:
            self._antwort_zeigen(antwort, frage)
            return

        e = self._ki_einstellungen()
        try:
            backend = backend_erstellen(e)
        except Exception as exc:
            backend = None
            self.z.meldung.emit(f"KI nicht verfügbar: {exc}", "warnung")
        if backend is None:
            self._antwort_zeigen(Antwort(
                "Das habe ich nicht sicher verstanden. Ich kann Fragen zu **Belegung, freien Plätzen, Auslastung, "
                "Kapazität, Prognose, Anreisen, Mietern und Häusern** beantworten – am besten mit Standort und "
                "Zeitraum, z. B. „Belegung Goslar im Oktober“.", quelle="hinweis", vorschlaege=BEISPIELE[:4]), frage)
            return
        self._tippen = Tippen("denkt nach")
        self._tippen.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._tippen_zeile = self._einfuegen(self._tippen)
        self.btn.setEnabled(False)
        self._vorschlaege_setzen([])
        self._worker = Worker(backend.antworte, frage, list(self.verlauf), self.z.ds, date.today(), parent=self)
        self._worker.fertig.connect(lambda text: self._ki_fertig(text, frage, e.backend))
        self._worker.fehler.connect(self._ki_fehler)
        self._worker.start()

    def _tippen_weg(self) -> None:
        if self._tippen is not None:
            self.chat.removeItem(self._tippen_zeile)
            self._tippen.deleteLater()
            self._tippen_zeile.deleteLater()
            self._tippen = None
        self.btn.setEnabled(True)

    def _ki_fertig(self, text: str, frage: str, backend: str) -> None:
        self._tippen_weg()
        self._antwort_zeigen(Antwort(text, quelle="ki"), frage, "KI · Claude" if backend == "claude" else "KI · lokal")

    def _ki_fehler(self, text: str) -> None:
        self._tippen_weg()
        self._antwort_zeigen(Antwort(f"Die KI ist gerade nicht erreichbar: {text}", quelle="hinweis"), None)

    def _antwort_zeigen(self, a: Antwort, frage: str | None, fuss: str | None = None) -> None:
        inhalt = markdown_html(a.text)
        klartext = a.text
        if a.tabelle:
            kopf, zeilen = a.tabelle
            inhalt += _tabelle_html(kopf, zeilen)
            klartext += "\n" + "\t".join(kopf) + "\n" + "\n".join("\t".join(map(str, z)) for z in zeilen)
        if fuss is None:
            fuss = {"daten": "aus den Daten berechnet", "hinweis": None}.get(a.quelle)
            if a.hinweis == "Prognose" and fuss:
                fuss += " · enthält Prognose"
        art = "hinweis" if a.quelle == "hinweis" else "assistent"
        self._einfuegen(Blase(art, inhalt, fuss, klartext))
        if frage:
            self.verlauf += [("user", frage), ("assistant", klartext)]
        self._vorschlaege_setzen(a.vorschlaege)
