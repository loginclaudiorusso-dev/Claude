"""Einstellungen: Erscheinungsbild und KI-Anbindung."""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QSpinBox, QWidget

from ... import __version__, erinnerung, speicher
from ...assistent.llm import CLAUDE_STANDARDMODELL, Einstellungen, backend_erstellen, schluessel_laden, schluessel_speichern
from ...konfig import datenordner
from .. import theme
from ..basis import Seite, Worker, Zustand
from ..widgets import Hinweis, Karte, Segment, knopf, label

THEME_OPTIONEN = ["hell", "dunkel", "hochkontrast", "system"]
BACKENDS = ["aus", "claude", "lokal"]
CLAUDE_MODELLE = [("claude-opus-5", "Claude Opus 5 (beste Qualität)"), ("claude-sonnet-5", "Claude Sonnet 5 (schneller)"),
                  ("claude-haiku-4-5", "Claude Haiku 4.5 (am günstigsten)")]


class EinstellungenSeite(Seite):
    titel = "Einstellungen"
    untertitel = "Darstellung und Assistent"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        e = speicher.einstellungen()

        aussehen = Karte("Erscheinungsbild", "System folgt der Windows-Einstellung")
        self.theme_wahl = Segment(["Hell", "Dunkel", "Hochkontrast", "System"],
                                  THEME_OPTIONEN.index(e.get("theme", "system")) if e.get("theme", "system") in THEME_OPTIONEN else 3)
        self.theme_wahl.geaendert.connect(self._theme_waehlen)
        aussehen.inhalt.addWidget(self.theme_wahl)
        self.lay.addWidget(aussehen)

        ki = Karte("KI für freie Fragen",
                   "Präzise Datenfragen beantwortet der Assistent immer selbst und offline. Ein Sprachmodell hilft "
                   "zusätzlich bei offen formulierten Fragen – es bekommt keine Rohdaten, sondern ruft dieselben "
                   "Abfragen auf wie das Dashboard.")
        self.ki_e = Einstellungen.aus_dict(e.get("ki", {}))
        self.backend = Segment(["Aus", "Claude (Anthropic)", "Lokales Modell"], BACKENDS.index(self.ki_e.backend))
        self.backend.geaendert.connect(self._backend)
        ki.inhalt.addWidget(self.backend)

        self.claude = QWidget()
        f = QFormLayout(self.claude)
        f.setContentsMargins(0, 6, 0, 0)
        f.setHorizontalSpacing(14)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-ant-… (wird in der Windows-Anmeldeinformationsverwaltung gespeichert)")
        if schluessel_laden():
            self.key.setPlaceholderText("•••••••• gespeichert – zum Ändern neuen Schlüssel eingeben")
        f.addRow("API-Schlüssel", self.key)
        self.modell = QComboBox()
        for mid, name in CLAUDE_MODELLE:
            self.modell.addItem(name, mid)
        self.modell.setCurrentIndex(max(0, self.modell.findData(self.ki_e.claude_modell)))
        f.addRow("Modell", self.modell)
        self.effort = QComboBox()
        for wert, name in (("low", "Schnell"), ("medium", "Ausgewogen"), ("high", "Gründlich")):
            self.effort.addItem(name, wert)
        self.effort.setCurrentIndex(max(0, self.effort.findData(self.ki_e.claude_effort)))
        f.addRow("Denktiefe", self.effort)
        f.addRow("", Hinweis("An Anthropic gehen nur die Frage, der kurze Gesprächsverlauf und die Ergebnisse der "
                             "abgefragten Kennzahlen (z. B. Monatsmittel) – keine Namen aus Listen, sofern sie nicht "
                             "explizit abgefragt werden.", "info"))
        ki.inhalt.addWidget(self.claude)

        self.lokal = QWidget()
        f2 = QFormLayout(self.lokal)
        f2.setContentsMargins(0, 6, 0, 0)
        f2.setHorizontalSpacing(14)
        self.url = QLineEdit(self.ki_e.lokal_url)
        f2.addRow("Server-Adresse", self.url)
        self.lmodell = QLineEdit(self.ki_e.lokal_modell)
        f2.addRow("Modell", self.lmodell)
        f2.addRow("", label("Funktioniert mit Ollama, LM Studio oder einem llama.cpp-Server (OpenAI-kompatible "
                            "Schnittstelle). Empfohlen: ein Modell mit gutem Tool-Calling, z. B. qwen2.5:7b-instruct.",
                            "klein", umbruch=True))
        ki.inhalt.addWidget(self.lokal)

        knoepfe = QHBoxLayout()
        sp = knopf("Speichern", "primary", "haken")
        sp.clicked.connect(self._speichern)
        self.test = knopf("Verbindung testen", None, "funke")
        self.test.clicked.connect(self._testen)
        knoepfe.addWidget(sp)
        knoepfe.addWidget(self.test)
        knoepfe.addStretch()
        ki.inhalt.addLayout(knoepfe)
        self.lay.addWidget(ki)

        erin = Karte("Erinnerungen an Abreisen", "Vorgabe für neue Erinnerungen – je Person in Daten → Anreisen änderbar")
        fe = QFormLayout()
        fe.setHorizontalSpacing(14)
        fe.setVerticalSpacing(8)
        ee = e.get("erinnerung", {})
        self.e_kanal = QComboBox()
        for k, text in erinnerung.KANAELE.items():
            self.e_kanal.addItem(text, k)
            if k in ("outlook", "mail") and not erinnerung.outlook_moeglich():
                self.e_kanal.model().item(self.e_kanal.count() - 1).setEnabled(False)
        kanal = ee.get("kanal") or erinnerung.standard_kanal()
        self.e_kanal.setCurrentIndex(max(0, self.e_kanal.findData(kanal)))
        self.e_kanal.setMaximumWidth(360)
        fe.addRow("Weg", self.e_kanal)
        self.e_tage = QSpinBox()
        self.e_tage.setRange(0, 60)
        self.e_tage.setSuffix(" Tage vor der Abreise")
        self.e_tage.setSpecialValueText("am Abreisetag")
        self.e_tage.setValue(int(ee.get("tage", 2)))
        self.e_tage.setFixedWidth(200)
        fe.addRow("Zeitpunkt", self.e_tage)
        self.e_mail = QLineEdit(ee.get("empfaenger", ""))
        self.e_mail.setPlaceholderText("leer = eigene Outlook-Adresse")
        self.e_mail.setMaximumWidth(360)
        fe.addRow("E-Mail an", self.e_mail)
        erin.inhalt.addLayout(fe)
        self._e_form = fe
        if not erinnerung.outlook_moeglich():
            erin.inhalt.addWidget(Hinweis("Outlook ist hier nicht verfügbar (nur unter Windows mit installiertem Outlook). "
                                          "Erinnerungen erscheinen dann im Dashboard oder als Kalenderdatei.", "info"))
        for w in (self.e_kanal,):
            w.currentIndexChanged.connect(self._erinnerung_speichern)
        self.e_tage.valueChanged.connect(self._erinnerung_speichern)
        self.e_mail.editingFinished.connect(self._erinnerung_speichern)
        self._erinnerung_sichtbar()
        self.lay.addWidget(erin)

        info = Karte("Über")
        info.inhalt.addWidget(label(f"Belegungsdashboard {__version__}<br>Datenordner: {datenordner()}<br>"
                                    "Tastenkürzel: Strg+1…6 Seiten wechseln · F5 neu einlesen", "muted", umbruch=True))
        self.lay.addWidget(info)
        self.lay.addStretch()
        self._backend(BACKENDS.index(self.ki_e.backend), speichern=False)

    def _theme_waehlen(self, idx: int) -> None:
        modus = THEME_OPTIONEN[idx]
        speicher.einstellung_setzen("theme", modus)
        theme.setzen(modus)
        self.z.theme_geaendert.emit()

    def _erinnerung_sichtbar(self) -> None:
        mail = self.e_kanal.currentData() == "mail"
        self.e_mail.setVisible(mail)
        beschriftung = self._e_form.labelForField(self.e_mail)
        if beschriftung:
            beschriftung.setVisible(mail)

    def _erinnerung_speichern(self, *_) -> None:
        speicher.einstellung_setzen("erinnerung", {"kanal": self.e_kanal.currentData(), "tage": self.e_tage.value(),
                                                   "empfaenger": self.e_mail.text().strip()})
        self._erinnerung_sichtbar()

    def _backend(self, idx: int, speichern: bool = True) -> None:
        self.claude.setVisible(BACKENDS[idx] == "claude")
        self.lokal.setVisible(BACKENDS[idx] == "lokal")
        self.test.setVisible(BACKENDS[idx] != "aus")
        if speichern:
            self._speichern(still=True)

    def _einstellungen(self) -> Einstellungen:
        return Einstellungen(backend=BACKENDS[self.backend.index()], claude_modell=self.modell.currentData() or CLAUDE_STANDARDMODELL,
                             claude_effort=self.effort.currentData() or "medium", lokal_url=self.url.text().strip(),
                             lokal_modell=self.lmodell.text().strip())

    def _speichern(self, still: bool = False) -> None:
        e = self._einstellungen()
        speicher.einstellung_setzen("ki", e.__dict__)
        if self.key.text().strip():
            if schluessel_speichern(self.key.text().strip()):
                self.key.clear()
                self.key.setPlaceholderText("•••••••• gespeichert – zum Ändern neuen Schlüssel eingeben")
            else:
                self.z.meldung.emit("Schlüssel konnte nicht sicher gespeichert werden – alternativ Umgebungsvariable "
                                    "ANTHROPIC_API_KEY setzen.", "warnung")
                return
        if not still:
            self.z.meldung.emit("Einstellungen gespeichert.", "ok")

    def _testen(self) -> None:
        if self.z.ds is None:
            self.z.meldung.emit("Erst Daten laden.", "warnung")
            return
        self._speichern(still=True)
        try:
            backend = backend_erstellen(self._einstellungen())
        except Exception as exc:
            self.z.meldung.emit(f"Einrichtung fehlgeschlagen: {exc}", "fehler")
            return
        self.test.setEnabled(False)
        self.test.setText("Teste …")
        self._w = Worker(backend.antworte, "Wie hoch ist die Belegung insgesamt heute? Antworte in einem Satz.", [],
                         self.z.ds, date.today(), parent=self)
        self._w.fertig.connect(lambda t: self.z.meldung.emit(f"Verbindung klappt: {t[:160]}", "ok"))
        self._w.fehler.connect(lambda t: self.z.meldung.emit(f"Test fehlgeschlagen: {t}", "fehler"))
        self._w.finished.connect(lambda: (self.test.setEnabled(True), self.test.setText("Verbindung testen")))
        self._w.start()
