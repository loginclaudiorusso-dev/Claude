"""Hauptfenster: Seitenleiste, Kopfzeile mit globalen Filtern, Seiten, Laden im Hintergrund."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QMainWindow, QMenu, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from .. import laden, speicher
from ..konfig import GESAMT, STANDORT_LABEL, STANDORTE, programmordner, ressourcenordner
from . import icons, theme
from .basis import Seite, Worker, Zustand
from .widgets import DatumFeld, Karte, Pille, Segment, Toast, icon_setzen, knopf, label

log = logging.getLogger(__name__)

FILTER_STANDORTE = [GESAMT] + STANDORTE


class HauptFenster(QMainWindow):
    def __init__(self, zustand: Zustand):
        super().__init__()
        self.z = zustand
        self._worker: Worker | None = None
        self.setWindowTitle("Belegungsdashboard")
        self.resize(1440, 920)
        self.setMinimumSize(1100, 700)

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

        from .seiten.assistent import AssistentSeite
        from .seiten.belegung import BelegungSeite
        from .seiten.daten import DatenSeite
        from .seiten.einstellungen import EinstellungenSeite
        from .seiten.prognose import PrognoseSeite
        from .seiten.uebersicht import UebersichtSeite

        self.seiten: dict[str, Seite] = {
            "uebersicht": UebersichtSeite(zustand), "belegung": BelegungSeite(zustand),
            "prognose": PrognoseSeite(zustand), "assistent": AssistentSeite(zustand),
            "daten": DatenSeite(zustand), "einstellungen": EinstellungenSeite(zustand),
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
        self.zeigen("uebersicht")

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
        t2 = label("INN-tegrativ · Internat")
        t2.setObjectName("marke_sub")
        texte.addWidget(t1)
        texte.addWidget(t2)
        marke.addLayout(texte, 1)
        v.addLayout(marke)
        v.addSpacing(18)

        self.nav = QButtonGroup(self)
        self.nav_knoepfe: dict[str, QPushButton] = {}
        eintraege = [("Analyse", None), ("uebersicht", "Übersicht"), ("belegung", "Belegung"), ("prognose", "Prognose"),
                     ("assistent", "Assistent"), ("Verwaltung", None), ("daten", "Daten && Import"),
                     ("einstellungen", "Einstellungen")]
        icon_name = {"uebersicht": "uebersicht", "belegung": "belegung", "prognose": "prognose",
                     "assistent": "assistent", "daten": "daten", "einstellungen": "einstellungen"}
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
            self.z.meldung.emit(f"{n} Abreise-Erinnerung{'en' if n > 1 else ''} fällig – siehe Übersicht.", "info")

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
