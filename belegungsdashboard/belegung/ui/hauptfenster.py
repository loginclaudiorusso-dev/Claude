"""Hauptfenster: Seitenleiste, Kopfzeile mit globalen Filtern, Seiten, Laden im Hintergrund."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QMainWindow, QMenu, QProgressBar, QPushButton,
    QStackedWidget, QSystemTrayIcon, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from .. import laden, speicher
from .. import termine as tm
from ..konfig import GESAMT, STANDORT_LABEL, STANDORTE, programmordner, ressourcenordner
from . import icons, theme
from .aenderung_ui import rueckgaengig
from .basis import Seite, Worker, Zustand, arbeitsspeicher_freigeben, sichtbar
from .widgets import DatumFeld, Karte, KurzLabel, Pille, Segment, Toast, icon_setzen, knopf, label

log = logging.getLogger(__name__)

FILTER_STANDORTE = [GESAMT] + STANDORTE


def uwt_meldung(neu: list[str]) -> str:
    return "UWT übernommen: " + "; ".join(neu)


class _TabLeiste(QTabBar):
    """Tab-Leiste, die bei vielen Tabs schrumpft (Blätter-Pfeile) statt das Fenster zu verbreitern."""

    def minimumSizeHint(self) -> QSize:
        s = super().minimumSizeHint()
        return QSize(min(s.width(), 180), s.height())


def _reiter_text(seite, ansicht: dict) -> str:
    """Unterreiter-Name aus einer gemerkten Ansicht (Tab im Hintergrund)."""
    import re

    r = seite._reiter_segment()
    i = ansicht.get("reiter")
    if r is None or not isinstance(i, int):
        return ""
    return re.sub(r"\s*\(\d+\)$", "", r.beschriftung(i))


class HauptFenster(QMainWindow):
    def __init__(self, zustand: Zustand):
        super().__init__()
        self.z = zustand
        self._worker: Worker | None = None
        from .. import __version__

        self.setWindowTitle(f"{speicher.anzeige_name()[0]} – v{__version__}")
        self.resize(1440, 920)
        self.setMinimumSize(900, 600)

        wurzel = QWidget()
        wurzel.setObjectName("wurzel")
        self.setCentralWidget(wurzel)
        h = QHBoxLayout(wurzel)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._sidebar())

        rechts = QVBoxLayout()
        rechts.setContentsMargins(0, 0, 0, 0)
        rechts.setSpacing(0)
        rechts.addWidget(self._tableiste())
        rechts.addWidget(self._kopf())
        self.fortschritt = QProgressBar()
        self.fortschritt.setRange(0, 0)
        self.fortschritt.setFixedHeight(3)
        self.fortschritt.setTextVisible(False)
        self.fortschritt.setVisible(False)
        rechts.addWidget(self.fortschritt)
        self.stapel = QStackedWidget()
        rechts.addWidget(self.stapel, 1)
        h.addLayout(rechts, 1)

        # neue UWT-Pläne aus dem Ordner „UWT“ übernehmen, bevor die Seiten laden
        from .. import uwt

        try:
            uwt_neu = uwt.automatisch_importieren()
        except Exception:
            uwt_neu = []
        from .. import einheitsliste

        try:
            listen_neu = einheitsliste.automatisch_importieren()   # Ordner „Listen“: Einheitslisten
        except Exception:
            listen_neu = []

        from .seiten.assistent import AssistentSeite
        from .seiten.belegung import BelegungSeite
        from .seiten.daten import DatenSeite
        from .seiten.einstellungen import EinstellungenSeite
        from .seiten.inventar import InventarSeite
        from .seiten.posteingang import PosteingangSeite
        from .seiten.prognose import PrognoseSeite
        from .seiten.start import StartSeite
        from .seiten.termine import TermineSeite
        from .seiten.uebersicht import UebersichtSeite
        from .seiten.zimmerplan import ZimmerplanSeite

        self.seiten: dict[str, Seite] = {
            "start": StartSeite(zustand),
            "uebersicht": UebersichtSeite(zustand), "belegung": BelegungSeite(zustand),
            "prognose": PrognoseSeite(zustand), "assistent": AssistentSeite(zustand),
            "termine": TermineSeite(zustand), "posteingang": PosteingangSeite(zustand),
            "zimmerplan": ZimmerplanSeite(zustand), "inventar": InventarSeite(zustand), "daten": DatenSeite(zustand), "einstellungen": EinstellungenSeite(zustand),
        }
        for s in self.seiten.values():
            self.stapel.addWidget(s)
            if (aktion := getattr(s, "kopf_aktion", None)) is not None:
                self._kopf_h.insertWidget(1, aktion, 0, Qt.AlignVCenter)
                aktion.hide()

        self.name_anzeigen()
        zustand.name_geaendert.connect(self.name_anzeigen)
        self.toast = Toast(wurzel)
        zustand.meldung.connect(self.toast.zeigen)
        zustand.aenderung_gespeichert.connect(
            lambda text, art: self.toast.zeigen(text, art, aktion=("Rückgängig", lambda: rueckgaengig(self, zustand, False))))
        zustand.navigieren.connect(self.zeigen)
        zustand.neu_laden.connect(self.laden)
        zustand.listen_geaendert.connect(self._listen_geaendert)
        zustand.filter_geaendert.connect(self._filter_anzeigen)
        zustand.theme_geaendert.connect(self._theme)
        for i, key in enumerate(self.seiten):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda k=key: self.zeigen(k))
        QShortcut(QKeySequence("F5"), self, activated=lambda: self.laden(False))
        QShortcut(QKeySequence.Undo, self, activated=lambda: rueckgaengig(self, zustand))    # Strg+Z: Planung
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.suche.setFocus(), self.suche.selectAll()))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._tab_duplizieren)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self._tab_schliessen(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Tab"), self, activated=lambda: self._tab_blaettern(1))
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, activated=lambda: self._tab_blaettern(-1))
        for s in self.seiten.values():            # Unterreiter gewechselt → Tab-Titel anpassen
            if (r := s._reiter_segment()) is not None:
                r.geaendert.connect(lambda _i: self._tab_titel())
        self._tabs_wiederherstellen()
        self._beenden = False
        self._tray_einrichten()
        zustand.termine_geaendert.connect(self.erinnerungen_pruefen)
        zustand.listen_geaendert.connect(lambda: zustand.termine_geaendert.emit())
        self._melde_timer = QTimer(self)
        self._melde_timer.setInterval(15 * 60 * 1000)
        self._melde_timer.timeout.connect(lambda: self.erinnerungen_pruefen(melden=True))
        self._melde_timer.start()
        QTimer.singleShot(1500, lambda: self.erinnerungen_pruefen(melden=True))
        if uwt_neu:
            QTimer.singleShot(800, lambda: zustand.meldung.emit(uwt_meldung(uwt_neu), "ok"))
        if listen_neu:
            QTimer.singleShot(1200, lambda: zustand.meldung.emit("Listen übernommen: " + "; ".join(listen_neu), "ok"))

    # ---- Aufbau ---------------------------------------------------------------------------

    def _sidebar(self) -> QWidget:
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(232)
        v = QVBoxLayout(sb)
        v.setContentsMargins(14, 18, 14, 14)
        v.setSpacing(2)

        marke = QHBoxLayout()
        marke.setSpacing(10)
        logo = QPixmap(str(ressourcenordner() / "assets" / "logo.png"))
        if logo.isNull():
            logo = QPixmap(str(programmordner() / "assets" / "logo.png"))
        self.logo = label()
        if not logo.isNull():
            self.logo.setPixmap(logo.scaledToHeight(34, Qt.SmoothTransformation))
            marke.addWidget(self.logo)
        texte = QVBoxLayout()
        texte.setSpacing(0)
        t1 = KurzLabel()                       # Name und Zusatz: Einstellungen → Name des Dashboards
        t1.setObjectName("marke")
        t2 = KurzLabel()
        t2.setObjectName("marke_sub")
        self.marke_name, self.marke_zusatz = t1, t2
        texte.addWidget(t1)
        texte.addWidget(t2)
        marke.addLayout(texte, 1)
        v.addLayout(marke)
        v.addSpacing(14)
        # Namenssuche – immer sichtbar (Strg+F)
        from PySide6.QtWidgets import QLineEdit

        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Name oder Zimmer …")
        self.suche.setClearButtonEnabled(True)
        self.suche.setToolTip("Person (Name) oder Zimmer (z. B. 322, 2-322, E01) finden – Enter drücken · Strg+F")
        self.suche.returnPressed.connect(self.suchen)
        v.addWidget(self.suche)
        v.addSpacing(10)

        self.nav = QButtonGroup(self)
        self.nav_knoepfe: dict[str, QPushButton] = {}
        eintraege = [("start", "Start"), ("Analyse", None), ("uebersicht", "Übersicht"), ("belegung", "Belegung"), ("prognose", "Prognose"),
                     ("assistent", "Assistent"), ("Verwaltung", None), ("termine", "Termine"), ("posteingang", "Posteingang"),
                     ("zimmerplan", "Zimmerplan"),
                     ("inventar", "Inventar"),
                     ("daten", "Daten && Import"),
                     ("einstellungen", "Einstellungen")]
        icon_name = {"start": "start", "uebersicht": "uebersicht", "belegung": "belegung", "prognose": "prognose",
                     "assistent": "assistent", "termine": "kalender", "posteingang": "mail", "zimmerplan": "haus", "inventar": "inventar", "daten": "daten", "einstellungen": "einstellungen"}
        for key, text in eintraege:
            if text is None:
                v.addWidget(label(key.upper(), "nav_gruppe"))
                continue
            b = QPushButton(f"  {text}")
            b.setProperty("nav", True)
            b.setProperty("icon_key", icon_name[key])
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(QSize(18, 18))
            b.clicked.connect(lambda _=False, k=key: self._nav_klick(k))
            b.installEventFilter(self)                 # mittlere Maustaste: neuer Tab
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, k=key, b=b: self._nav_menue(k, b))
            self.nav.addButton(b)
            self.nav_knoepfe[key] = b
            v.addWidget(b)
        self._nav_icons()
        v.addStretch()

        karte = Karte(abstand=12)
        karte.inhalt.setSpacing(6)
        kopf = QHBoxLayout()
        kopf.addWidget(label("Datenstand", "klein"))
        kopf.addStretch()
        self.stand_pille = Pille("–", "neutral")
        kopf.addWidget(self.stand_pille)
        karte.inhalt.addLayout(kopf)
        self.stand_datum = label("–", "kpi_wert_klein")
        karte.inhalt.addWidget(self.stand_datum)
        self.stand_quelle = label("", "klein", umbruch=True)
        karte.inhalt.addWidget(self.stand_quelle)
        self.btn_laden = knopf("Aktualisieren", "primary", "aktualisieren")
        menue = QMenu(self.btn_laden)
        menue.addAction("Datei neu einlesen (schnell)\tF5", lambda: self.laden(False))
        self.server_aktion = menue.addAction("Pivot vom Server abrufen (Excel)", lambda: self.laden(True))
        self.server_aktion.setEnabled(laden.refresh_moeglich())
        menue.addSeparator()
        menue.addAction("Andere Excel-Datei wählen …", self.datei_waehlen)
        self.btn_laden.setMenu(menue)
        karte.inhalt.addWidget(self.btn_laden)
        v.addWidget(karte)
        return sb

    def _nav_icons(self) -> None:
        t = theme.T
        for b in self.nav_knoepfe.values():
            b.setIcon(icons.icon(b.property("icon_key"), t.sb_text_2 or t.text_2, 18,
                                 farbe_aktiv=t.sb_aktiv_text or t.accent))
        if hasattr(self, "tab_plus"):
            self.tab_plus.setIcon(icons.icon("plus", t.text_2, 16))
            for i in range(self.tabs.count()):
                self._tab_titel(i)

    def _kopf(self) -> QWidget:
        kopf = QFrame()
        kopf.setObjectName("kopf")
        h = QHBoxLayout(kopf)
        h.setContentsMargins(28, 22, 28, 12)
        h.setSpacing(12)
        texte = QVBoxLayout()
        texte.setSpacing(2)
        self.titel = label("", "seitentitel")
        self.untertitel = KurzLabel()                # kürzt im schmalen Fenster mit „…“ statt zu verbreitern
        self.untertitel.setProperty("rolle", "seitenuntertitel")
        texte.addWidget(self.titel)
        texte.addWidget(self.untertitel)
        h.addLayout(texte, 1)
        self._kopf_h = h                      # Seiten können eine eigene Aktion in den Kopf legen (kopf_aktion)
        self.standort_filter = Segment([STANDORT_LABEL[s] for s in FILTER_STANDORTE], 0)
        self.standort_filter.setToolTip("Standort für alle Auswertungen")
        self.standort_filter.geaendert.connect(lambda i: self.z.standort_setzen(FILTER_STANDORTE[i]))
        h.addWidget(self.standort_filter, 0, Qt.AlignVCenter)
        self.bezug_filter = Segment(["Netto", "Brutto"], 0)
        self.bezug_filter.setToolTip("Netto: Reha und Verträge · Brutto: zusätzlich FRAI, Jugendhilfe, andere Bereiche")
        self.bezug_filter.geaendert.connect(lambda i: self.z.brutto_setzen(i == 1))
        h.addWidget(self.bezug_filter, 0, Qt.AlignVCenter)
        return kopf

    # ---- Navigation / Filter ------------------------------------------------------------

    # ---- Tabs: mehrere Ansichten (Seite + Unterreiter) wie im Browser ------------------------

    def _tableiste(self) -> QWidget:
        leiste = QFrame()
        leiste.setObjectName("tableiste")
        h = QHBoxLayout(leiste)
        h.setContentsMargins(20, 8, 20, 0)
        h.setSpacing(4)
        self.tabs = _TabLeiste()
        self.tabs.setObjectName("ansichten")
        self.tabs.setTabsClosable(False)          # eigene, ruhige Schließen-Knöpfe (siehe _tab_titel)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.setExpanding(False)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setDrawBase(False)
        self.tabs.currentChanged.connect(self._tab_gewechselt)
        self.tabs.tabCloseRequested.connect(self._tab_schliessen)
        self.tabs.tabMoved.connect(lambda *_: self._tabs_speichern())
        self.tabs.setToolTip("Mehrere Ansichten: Strg+T neuer Tab, Strg+W schließen, Strg+Tab wechseln – "
                             "Seite mit Strg+Klick oder mittlerer Maustaste in der Seitenleiste in neuem Tab öffnen")
        h.addWidget(self.tabs, 0, Qt.AlignBottom)   # „+“ direkt hinter dem letzten Tab
        self.tab_plus = QToolButton()
        self.tab_plus.setObjectName("tab_plus")
        self.tab_plus.setCursor(Qt.PointingHandCursor)
        self.tab_plus.setToolTip("Neuer Tab (Strg+T)")
        self.tab_plus.setPopupMode(QToolButton.InstantPopup)
        menue = QMenu(self.tab_plus)
        menue.aboutToShow.connect(lambda: self._plus_menue(menue))
        self.tab_plus.setMenu(menue)
        self.tab_plus.setIcon(icons.icon("plus", theme.T.text_2, 16))
        h.addWidget(self.tab_plus, 0, Qt.AlignVCenter)
        h.addStretch(1)
        self._tab_id = 0
        self._aktiv_id: int | None = None
        return leiste

    def _plus_menue(self, menue: QMenu) -> None:
        menue.clear()
        menue.addAction("Aktuelle Ansicht duplizieren\tStrg+T", self._tab_duplizieren)
        menue.addSeparator()
        for key, b in self.nav_knoepfe.items():
            menue.addAction(b.icon(), self.seiten[key].titel or key, lambda k=key: self.tab_oeffnen(k))

    def _tab_daten(self, i: int) -> dict:
        d = self.tabs.tabData(i)
        return d if isinstance(d, dict) else {}

    def _tab_index(self, tid: int | None) -> int:
        return next((i for i in range(self.tabs.count()) if self._tab_daten(i).get("id") == tid), -1)

    def _tab_merken(self) -> None:
        """Ansicht der gerade gezeigten Seite im aktiven Tab ablegen."""
        i = self._tab_index(self._aktiv_id)
        if i < 0:
            return
        d = dict(self._tab_daten(i))
        seite = self.seiten.get(d.get("seite"))
        if seite is not None:
            try:
                d["ansicht"] = seite.ansicht_lesen()
            except Exception:                      # noqa: BLE001 – Ansicht merken darf nie stören
                d["ansicht"] = {}
        self.tabs.setTabData(i, d)

    def tab_oeffnen(self, key: str, ansicht: dict | None = None, aktivieren: bool = True) -> None:
        if key not in self.seiten:
            return
        self._tab_merken()
        self._tab_id += 1
        i = self.tabs.addTab("")
        self.tabs.setTabData(i, {"id": self._tab_id, "seite": key, "ansicht": dict(ansicht or {})})
        self._tab_titel(i)
        if aktivieren:
            self.tabs.setCurrentIndex(i)
        self._tabs_speichern()

    def _tab_duplizieren(self) -> None:
        d = self._tab_daten(self.tabs.currentIndex())
        seite = self.seiten.get(d.get("seite"))
        self.tab_oeffnen(d.get("seite", "start"), seite.ansicht_lesen() if seite is not None else {})

    def _tab_gewechselt(self, i: int) -> None:
        if i < 0:
            return
        if self._aktiv_id is not None and self._tab_index(self._aktiv_id) >= 0:
            self._tab_merken()
        d = self._tab_daten(i)
        self._aktiv_id = d.get("id")
        key = d.get("seite") if d.get("seite") in self.seiten else "start"
        self._seite_zeigen(key)
        if d.get("ansicht"):
            try:
                self.seiten[key].ansicht_setzen(d["ansicht"])
            except Exception:                      # noqa: BLE001
                log.exception("Ansicht konnte nicht wiederhergestellt werden")
        self._tab_titel(i)
        self._tabs_speichern()

    def _tab_schliessen(self, i: int) -> None:
        if self.tabs.count() <= 1 or i < 0:
            return
        if self._tab_daten(i).get("id") == self._aktiv_id:
            self._aktiv_id = None                  # Ansicht des geschlossenen Tabs nicht mehr merken
        self.tabs.removeTab(i)
        self._tabs_speichern()

    def _tab_blaettern(self, d: int) -> None:
        if self.tabs.count() > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + d) % self.tabs.count())

    def _tab_titel(self, i: int | None = None) -> None:
        i = self.tabs.currentIndex() if i is None else i
        if i < 0:
            return
        d = self._tab_daten(i)
        seite = self.seiten.get(d.get("seite"))
        if seite is None:
            return
        zusatz = seite.ansicht_titel() if self.stapel.currentWidget() is seite or not d.get("ansicht") else \
            _reiter_text(seite, d["ansicht"])
        text = f"{seite.titel} · {zusatz}" if zusatz else seite.titel
        self.tabs.setTabText(i, text.replace("&", "&&"))          # „&“ sonst als Tastenkürzel gelesen
        self.tabs.setTabToolTip(i, f"{seite.titel}{' – ' + zusatz if zusatz else ''}")
        if hasattr(self, "nav_knoepfe") and d.get("seite") in self.nav_knoepfe:   # Farben der Tab-Leiste, nicht der Seitenleiste
            self.tabs.setTabIcon(i, icons.icon(self.nav_knoepfe[d["seite"]].property("icon_key"), theme.T.text_2, 16,
                                               farbe_aktiv=theme.T.accent))
        zu = self.tabs.tabButton(i, QTabBar.RightSide)
        if zu is None:
            zu = QToolButton()
            zu.setObjectName("tab_zu")
            zu.setCursor(Qt.PointingHandCursor)
            zu.setToolTip("Tab schließen (Strg+W)")
            zu.setFixedSize(18, 18)
            zu.clicked.connect(lambda _=False, b=zu: self._tab_schliessen(
                next((k for k in range(self.tabs.count()) if self.tabs.tabButton(k, QTabBar.RightSide) is b), -1)))
            self.tabs.setTabButton(i, QTabBar.RightSide, zu)
        zu.setIcon(icons.icon("schliessen", theme.T.text_3, 12))
        zu.setVisible(self.tabs.count() > 1)

    def _tabs_speichern(self) -> None:
        if getattr(self, "_tabs_laden", False):
            return
        self._tab_merken()
        for i in range(self.tabs.count()):         # Schließen-Knopf nur, wenn mehr als ein Tab offen ist
            if (b := self.tabs.tabButton(i, QTabBar.RightSide)) is not None:
                b.setVisible(self.tabs.count() > 1)
        liste = [{"seite": self._tab_daten(i).get("seite"), "ansicht": self._tab_daten(i).get("ansicht", {})}
                 for i in range(self.tabs.count())]
        try:
            speicher.einstellung_setzen("ansichten", {"tabs": liste, "aktiv": self.tabs.currentIndex()})
        except OSError:
            pass

    def _tabs_wiederherstellen(self) -> None:
        roh = speicher.einstellungen().get("ansichten") or {}
        tabs = [t for t in roh.get("tabs", []) if isinstance(t, dict) and t.get("seite") in self.seiten][:12]
        self._tabs_laden = True
        try:
            for t in tabs or [{"seite": "start", "ansicht": {}}]:
                self.tab_oeffnen(t["seite"], t.get("ansicht") if isinstance(t.get("ansicht"), dict) else {},
                                 aktivieren=False)
        finally:
            self._tabs_laden = False
        aktiv = roh.get("aktiv", 0) if isinstance(roh.get("aktiv"), int) else 0
        aktiv = aktiv if 0 <= aktiv < self.tabs.count() else 0
        if self.tabs.currentIndex() == aktiv:
            self._tab_gewechselt(aktiv)
        else:
            self.tabs.setCurrentIndex(aktiv)

    def _nav_klick(self, key: str) -> None:
        """Seitenleiste: Seite im aktuellen Tab – mit Strg in einem neuen Tab."""
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            self.tab_oeffnen(key)
        else:
            self.zeigen(key)

    def zeigen(self, key: str) -> None:
        """Seite im aktuellen Tab zeigen (Seitenleiste, Sprünge aus anderen Seiten)."""
        if key not in self.seiten:
            return
        i = self.tabs.currentIndex()
        if i >= 0:
            d = dict(self._tab_daten(i))
            if d.get("seite") != key:
                d.update(seite=key, ansicht={})
                self.tabs.setTabData(i, d)
        self._seite_zeigen(key)
        self._tab_titel()
        self._tabs_speichern()

    def _seite_zeigen(self, key: str) -> None:
        seite = self.seiten[key]
        self.stapel.setCurrentWidget(seite)
        self.nav_knoepfe[key].setChecked(True)
        self.titel.setText(seite.titel)
        self.untertitel.setText(seite.untertitel)
        self.standort_filter.setVisible(seite.zeigt_filter)
        self.bezug_filter.setVisible(seite.zeigt_bezug)
        for s in self.seiten.values():
            if (aktion := getattr(s, "kopf_aktion", None)) is not None:
                aktion.setVisible(s is seite)

    def name_anzeigen(self) -> None:
        from .. import __version__

        name, zusatz = speicher.anzeige_name()
        self.marke_name.setText(name)
        self.marke_zusatz.setText(" · ".join(x for x in (zusatz, f"v{__version__}") if x))
        self.setWindowTitle(f"{name} – v{__version__}")
        if hasattr(self, "nav_knoepfe") and "start" in self.seiten:   # Titel der Startseite in Leiste, Kopf, Tabs
            self.nav_knoepfe["start"].setText(f"  {self.seiten['start'].titel}".replace("&", "&&"))
            seite = self.stapel.currentWidget()
            self.titel.setText(seite.titel)
            self.untertitel.setText(seite.untertitel)
            for i in range(self.tabs.count()):
                self._tab_titel(i)
        if getattr(self, "tray", None) is not None:
            self.erinnerungen_pruefen()

    def _nav_menue(self, key: str, b: QPushButton) -> None:
        m = QMenu(self)
        m.addAction("In neuem Tab öffnen", lambda: self.tab_oeffnen(key))
        if key == "zimmerplan":
            m.addAction("In neuem Fenster öffnen", lambda: self.seiten["zimmerplan"]._neues_fenster())
        m.exec(b.mapToGlobal(b.rect().bottomLeft()))

    def eventFilter(self, obj, e) -> bool:
        if e.type() == QEvent.MouseButtonRelease and e.button() == Qt.MiddleButton:
            key = next((k for k, b in self.nav_knoepfe.items() if b is obj), None)
            if key is not None:
                self.tab_oeffnen(key)
                return True
        return super().eventFilter(obj, e)

    def _filter_anzeigen(self) -> None:
        self.standort_filter.setzen(FILTER_STANDORTE.index(self.z.standort))
        self.bezug_filter.setzen(1 if self.z.brutto else 0)

    def _theme(self) -> None:
        self._nav_icons()
        icon_setzen(self.btn_laden)
        for s in self.seiten.values():
            for w in s.findChildren(QPushButton):
                icon_setzen(w)
            for feld in s.findChildren(DatumFeld):
                feld.icon_aktualisieren()
        self._stand_anzeigen()

    # ---- Laden ----------------------------------------------------------------------------

    def datei_waehlen(self) -> None:
        start = str(self.z.quelle.parent if self.z.quelle else programmordner())
        pfad, _ = QFileDialog.getOpenFileName(self, "Pivot-Datei wählen", start, "Excel-Dateien (*.xlsx *.xlsm)")
        if pfad:
            self.z.quelle = Path(pfad)
            speicher.einstellung_setzen("quelle", pfad)
            self.laden(False)

    def laden(self, refresh: bool = False) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.z.meldung.emit("Es läuft bereits ein Ladevorgang.", "info")
            return
        if self.z.quelle is None or not self.z.quelle.exists():
            self.datei_waehlen()
            return
        self.z.laedt = True
        self.fortschritt.setVisible(True)
        self.btn_laden.setEnabled(False)
        self.stand_quelle.setText("Pivot wird vom Server abgerufen – das kann einige Minuten dauern …" if refresh
                                  else "Daten werden geladen …")
        self._worker = Worker(laden.lade, self.z.quelle, refresh, com=refresh, parent=self)
        self._worker.fertig.connect(lambda ds: self._geladen(ds, refresh))
        self._worker.fehler.connect(self._ladefehler)
        self._worker.finished.connect(self._lade_ende)
        self._worker.start()

    def _geladen(self, ds, refresh: bool) -> None:
        self.z.ds = ds
        self.z.daten_geaendert.emit()
        self._stand_anzeigen()
        if refresh and ds.pivot_aktualisiert:
            self.z.meldung.emit("Pivot vom Server aktualisiert.", "ok")
        elif refresh:
            self.z.meldung.emit("Server nicht erreichbar – gespeicherter Pivot-Stand wird angezeigt.", "warnung")
        elif ds.erinnerungen and not getattr(self, "_erinnert", False):
            self._erinnert = True
            n = len(ds.erinnerungen)
            self.z.meldung.emit(f"{n} Abreise-Erinnerung{'en' if n > 1 else ''} fällig – siehe Termine.", "info")

    def _ladefehler(self, text: str) -> None:
        self._stand_anzeigen()
        self.z.meldung.emit(f"Laden fehlgeschlagen: {text}", "fehler")

    def _lade_ende(self) -> None:
        self.z.laedt = False
        self.fortschritt.setVisible(False)
        self.btn_laden.setEnabled(True)

    def _listen_geaendert(self) -> None:
        if self.z.ds is None:
            return
        if not sichtbar(self):                 # minimiert/im Infobereich: Statistik erst beim Zurückholen
            self._neuberechnen_offen = True
            return
        self.fortschritt.setVisible(True)
        w = Worker(laden.neu_berechnen, self.z.ds, parent=self)
        w.fertig.connect(lambda ds: (setattr(self.z, "ds", ds), self.z.daten_geaendert.emit(), self._stand_anzeigen()))
        w.fehler.connect(lambda t: self.z.meldung.emit(f"Neuberechnung fehlgeschlagen: {t}", "fehler"))
        w.finished.connect(lambda: self.fortschritt.setVisible(False))
        w.start()
        self._neu_worker = w

    def _stand_anzeigen(self) -> None:
        ds = self.z.ds
        if ds is None:
            self.stand_datum.setText("–")
            self.stand_quelle.setText("Keine Daten geladen")
            return
        self.stand_datum.setText(ds.stichtag.strftime("%d.%m.%Y"))
        abruf = ds.pivot.abrufdatum
        if ds.pivot_aktualisiert is False:
            self.stand_pille.setzen("knapp", "Server-Abruf fehlgeschlagen")
        elif abruf and abruf >= date.today():
            self.stand_pille.setzen("ok", "aktuell")
        elif abruf:
            self.stand_pille.setzen("knapp", f"{(date.today() - abruf).days} Tage alt")
        else:
            self.stand_pille.setzen("neutral", "gespeichert")
        self.stand_quelle.setText(f"{ds.quelle.name} · geladen {ds.geladen_am:%H:%M} Uhr" if ds.quelle else "")

    # ---- Erinnerungen / Infobereich -------------------------------------------------------

    def _tray_einrichten(self) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        ic = QApplication.windowIcon()
        if ic.isNull():
            ic = icons.icon("kalender", theme.T.accent, 32)
        self.tray = QSystemTrayIcon(ic, self)
        self.tray.setToolTip(speicher.anzeige_name()[0])
        menue = QMenu()
        menue.addAction("Öffnen", self.vorholen)
        menue.addAction("Termine", lambda: self.vorholen("termine"))
        menue.addSeparator()
        menue.addAction("Beenden", self.beenden)
        self.tray.setContextMenu(menue)
        self._tray_menue = menue
        self.tray.activated.connect(lambda grund: self.vorholen() if grund in (
            QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        self.tray.messageClicked.connect(lambda: self.vorholen("termine"))
        self.tray.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def suchen(self) -> None:
        from .suche_dialog import SuchDialog

        SuchDialog(self, self.suche.text().strip()).exec()

    def benachrichtigen(self, titel: str, text: str) -> None:
        if self.tray is not None:
            self.tray.showMessage(titel, text, QSystemTrayIcon.Information, 20000)
        if self.isVisible():
            self.z.meldung.emit(f"{titel}: {text.splitlines()[0]}", "info")

    def erinnerungen_pruefen(self, melden: bool = False) -> None:
        """Zählt offene Erinnerungen in der Seitenleiste; meldet neue (einmal am Tag je Erinnerung)."""
        heute = date.today()
        try:
            alle = tm.alle()
        except Exception:
            log.exception("Termine konnten nicht gelesen werden")
            return
        offen = [t for t in alle if t.faellig(heute)]
        self.nav_knoepfe["termine"].setText(f"  Termine ({len(offen)})" if offen else "  Termine")
        try:
            from .. import mails

            n_post = mails.offen_anzahl()
        except Exception:                          # noqa: BLE001
            n_post = 0
        self.nav_knoepfe["posteingang"].setText(f"  Posteingang ({n_post})" if n_post else "  Posteingang")
        if self.tray is not None:
            name = speicher.anzeige_name()[0]
            self.tray.setToolTip(f"{name} – {len(offen)} Erinnerung(en) offen" if offen else name)
        self._reinigung_pruefen(heute, melden)
        if not melden:
            return
        neu = tm.zu_melden(alle, heute)
        if neu:
            self.benachrichtigen(*tm.meldetext(neu))
            tm.gemeldet_setzen(neu, heute)

    def _reinigung_pruefen(self, heute: date, melden: bool) -> None:
        """Offene Reinigungen, obwohl heute/morgen jemand ins Zimmer kommt → Zähler + Windows-Meldung."""
        from datetime import timedelta

        from .. import reinigungsliste as rl
        from .. import zimmerplan as zp

        try:
            st = zp.laden()
            zpv = st.zimmer_pivot
            rs = zp.reinigungen(st.lage, heute - timedelta(days=14), heute + timedelta(days=1),
                                zpv.zeitraum[1] if zpv else None, zpv.zeitraum[0] if zpv else None,
                                bool(speicher.einstellungen().get("reinigung_anreisetag", False)))
            kon = rl.konflikte(rs, heute, rl.erledigt())
            zimmer_kon = zp.konflikte(st.lage, heute)
        except Exception:
            log.exception("Reinigungen konnten nicht geprüft werden")
            return
        n = len(kon) + len(zimmer_kon)
        self.nav_knoepfe["zimmerplan"].setText(f"  Zimmerplan ({n})" if n else "  Zimmerplan")
        tipps = ([f"{len(kon)} Reinigung(en) offen, obwohl jemand einzieht"] if kon else []) + \
                ([f"{len(zimmer_kon)} geplante(s) Zimmer laut Gebäudeplan inzwischen belegt/gesperrt"] if zimmer_kon else [])
        self.nav_knoepfe["zimmerplan"].setToolTip("\n".join(tipps))
        if melden:
            neu = rl.zu_melden(rs, heute)
            if neu:
                titel = "Reinigung offen – Anreise steht an" if len(neu) == 1 else f"{len(neu)} Reinigungen offen – Anreisen stehen an"
                self.benachrichtigen(titel, "\n".join(rl.konflikt_text(r) for r in neu[:4]))
                rl.gemeldet_setzen(neu, heute)
            try:
                from .. import eintragen

                fac = eintragen.facility_zu_melden(st.lage, heute)
            except Exception:
                log.exception("Facility-Checks konnten nicht geprüft werden")
                fac = []
            if fac:
                self.benachrichtigen("Facility-Check nach langem Aufenthalt" if len(fac) == 1 else
                                     f"{len(fac)} Facility-Checks nach langem Aufenthalt",
                                     "\n".join(c.text for c in fac[:4]))
                eintragen.facility_gemeldet(fac)

    def vorholen(self, seite: str | None = None) -> None:
        if seite:
            self.zeigen(seite)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def beenden(self) -> None:
        self._beenden = True
        if self.tray is not None:
            self.tray.hide()
        self._threads_beenden()
        QApplication.instance().quit()

    def _threads_beenden(self) -> None:
        """Laufendes Laden abwarten – ein zerstörter, noch laufender QThread würde den Prozess abbrechen."""
        import os

        for w in (self._worker, getattr(self, "_neu_worker", None)):
            if w is not None and w.isRunning() and not w.wait(5000):
                os._exit(0)     # hängt z. B. am Server-Abruf; Daten werden atomar gespeichert

    # ---- minimiert / im Infobereich: nichts neu zeichnen, Speicher freigeben ------------------

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self._ruhen()
            else:
                QTimer.singleShot(0, self._aufwachen)

    def hideEvent(self, e) -> None:
        super().hideEvent(e)
        if not e.spontaneous():                # in den Infobereich geschlossen
            self._ruhen()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        QTimer.singleShot(0, self._aufwachen)

    def _ruhen(self) -> None:
        QTimer.singleShot(500, arbeitsspeicher_freigeben)   # nach dem Minimieren, nicht mittendrin

    def _aufwachen(self) -> None:
        """Was während des Minimierens liegen geblieben ist, jetzt nachholen – nur die sichtbare Seite."""
        if not sichtbar(self):
            return
        if getattr(self, "_neuberechnen_offen", False):
            self._neuberechnen_offen = False
            self._listen_geaendert()
        seite = self.stapel.currentWidget()
        if getattr(seite, "_veraltet", False):
            seite.anstossen()

    def closeEvent(self, e):
        if not self._beenden and self.tray is not None and tm.einstellungen()["hintergrund"]:
            e.ignore()
            self.hide()
            if not speicher.einstellungen().get("hintergrund_erklaert"):
                speicher.einstellung_setzen("hintergrund_erklaert", True)
                self.tray.showMessage("Läuft im Hintergrund weiter",
                                      "Erinnerungen kommen weiter. Beenden über das Symbol unten rechts (Rechtsklick).",
                                      QSystemTrayIcon.Information, 12000)
            return
        super().closeEvent(e)
        self._threads_beenden()
        QApplication.instance().quit()
