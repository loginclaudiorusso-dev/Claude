"""Hauptfenster: Seitenleiste, Kopfzeile mit globalen Filtern, Seiten, Laden im Hintergrund."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QMainWindow, QMenu, QProgressBar, QPushButton,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .. import laden, speicher
from .. import termine as tm
from ..konfig import GESAMT, STANDORT_LABEL, STANDORTE, programmordner, ressourcenordner
from . import icons, theme
from .basis import Seite, Worker, Zustand
from .widgets import DatumFeld, Karte, Pille, Segment, Toast, icon_setzen, knopf, label

log = logging.getLogger(__name__)

FILTER_STANDORTE = [GESAMT] + STANDORTE


def uwt_meldung(neu: list[str]) -> str:
    return "UWT übernommen: " + "; ".join(neu)


class HauptFenster(QMainWindow):
    def __init__(self, zustand: Zustand):
        super().__init__()
        self.z = zustand
        self._worker: Worker | None = None
        from .. import __version__

        self.setWindowTitle(f"Belegungsdashboard {__version__}")
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
        from .seiten.prognose import PrognoseSeite
        from .seiten.termine import TermineSeite
        from .seiten.uebersicht import UebersichtSeite
        from .seiten.zimmerplan import ZimmerplanSeite

        self.seiten: dict[str, Seite] = {
            "uebersicht": UebersichtSeite(zustand), "belegung": BelegungSeite(zustand),
            "prognose": PrognoseSeite(zustand), "assistent": AssistentSeite(zustand),
            "termine": TermineSeite(zustand), "zimmerplan": ZimmerplanSeite(zustand), "inventar": InventarSeite(zustand), "daten": DatenSeite(zustand), "einstellungen": EinstellungenSeite(zustand),
        }
        for s in self.seiten.values():
            self.stapel.addWidget(s)

        self.toast = Toast(wurzel)
        zustand.meldung.connect(self.toast.zeigen)
        zustand.navigieren.connect(self.zeigen)
        zustand.neu_laden.connect(self.laden)
        zustand.listen_geaendert.connect(self._listen_geaendert)
        zustand.filter_geaendert.connect(self._filter_anzeigen)
        zustand.theme_geaendert.connect(self._theme)
        for i, key in enumerate(self.seiten):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda k=key: self.zeigen(k))
        QShortcut(QKeySequence("F5"), self, activated=lambda: self.laden(False))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.suche.setFocus(), self.suche.selectAll()))
        self.zeigen("uebersicht")
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
        t1 = label("Belegung")
        t1.setObjectName("marke")
        from .. import __version__

        t2 = label(f"INN-tegrativ · Internat · v{__version__}")
        t2.setObjectName("marke_sub")
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
        eintraege = [("Analyse", None), ("uebersicht", "Übersicht"), ("belegung", "Belegung"), ("prognose", "Prognose"),
                     ("assistent", "Assistent"), ("Verwaltung", None), ("termine", "Termine"), ("zimmerplan", "Zimmerplan"),
                     ("inventar", "Inventar"),
                     ("daten", "Daten && Import"),
                     ("einstellungen", "Einstellungen")]
        icon_name = {"uebersicht": "uebersicht", "belegung": "belegung", "prognose": "prognose",
                     "assistent": "assistent", "termine": "kalender", "zimmerplan": "haus", "inventar": "inventar", "daten": "daten", "einstellungen": "einstellungen"}
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
            b.clicked.connect(lambda _=False, k=key: self.zeigen(k))
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
            b.setIcon(icons.icon(b.property("icon_key"), t.text_2, 18, farbe_aktiv=t.accent))

    def _kopf(self) -> QWidget:
        kopf = QFrame()
        kopf.setObjectName("kopf")
        h = QHBoxLayout(kopf)
        h.setContentsMargins(28, 22, 28, 12)
        h.setSpacing(12)
        texte = QVBoxLayout()
        texte.setSpacing(2)
        self.titel = label("", "seitentitel")
        self.untertitel = label("", "seitenuntertitel")
        texte.addWidget(self.titel)
        texte.addWidget(self.untertitel)
        h.addLayout(texte, 1)
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

    def zeigen(self, key: str) -> None:
        seite = self.seiten[key]
        self.stapel.setCurrentWidget(seite)
        self.nav_knoepfe[key].setChecked(True)
        self.titel.setText(seite.titel)
        self.untertitel.setText(seite.untertitel)
        self.standort_filter.setVisible(seite.zeigt_filter)
        self.bezug_filter.setVisible(seite.zeigt_bezug)

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
        self.tray.setToolTip("Belegungsdashboard")
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
        if self.tray is not None:
            self.tray.setToolTip(f"Belegungsdashboard – {len(offen)} Erinnerung(en) offen" if offen else "Belegungsdashboard")
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
