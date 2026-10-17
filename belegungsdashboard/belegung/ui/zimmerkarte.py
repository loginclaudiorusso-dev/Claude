"""Zimmer- und Personenkarte: alles Wichtige zu einem Zimmer und seinen Bewohnern an einer Stelle.

Öffnet sich beim Klick auf ein Zimmer (Häuser, Zeitstrahl), aus der Suche und aus Terminen. Eigenes Fenster,
nicht modal – mehrere Karten können gleichzeitig offen sein (z. B. zwei Zimmer vergleichen).

* Bewohner (heute und kommende): Zimmer ändern (wenn hier geplant und noch nicht angereist), Abreise, Notizen
  mit Wiedervorlage. Wer schon eingezogen ist (auch laut Gebäudeplan), bekommt einen Umzug ab einem Tag.
* Zum Zimmer: dauerhafter Hinweis (Stammdaten), Notizen mit Wiedervorlage (z. B. „Heizung defekt“),
  Ausstattung aus dem Inventar.
* Darunter Zeitstrahl und alle Belegungen.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QBoxLayout, QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from .. import anreiseliste, inventar
from .. import zimmerplan as zp
from .notizen import NotizenWidget
from .widgets import DatumFeld, FlowLayout, Hinweis, Karte, Pille, Tabelle, knopf, label, leeren
from .zeitstrahl import Zeitstrahl

STATUS_TEXT = {"frei": "frei", "teilweise": "teilweise frei", "belegt": "belegt", "geplant": "geplant",
               "gesperrt": "gesperrt"}

_offen: list["ZimmerKarte"] = []
SICHTBAR = 4          # so viele Bewohner-Knöpfe, der Rest hinter „+ n spätere“


def zeitraum(von: date, bis: date) -> str:
    """„24.06.–23.06.28“ – Jahr nur, wenn nötig (anderes Jahr als heute bzw. als die Anreise)."""
    jahr = date.today().year
    a = f"{von:%d.%m.}" + (f"{von:%y}" if von.year != jahr else "")
    e = f"{bis:%d.%m.}" + (f"{bis:%y}" if bis.year != jahr or bis.year != von.year else "")
    return f"{a}–{e}"


def karte_oeffnen(parent, zustand, zimmer: str | None = None, person: str | None = None) -> "ZimmerKarte | None":
    """Karte zu einem Zimmer und/oder einer Person öffnen (eine schon offene Karte kommt nach vorn)."""
    if person and person.startswith("zimmer:"):
        zimmer, person = person.removeprefix("zimmer:"), None
    stand = zp.laden()
    if zimmer is None and person:
        bw = zp.bewohner_finden(stand, person)
        if bw is not None:
            zimmer = bw.zimmer
        elif not any(b.schluessel == person for b in stand.bedarf):
            zustand.meldung.emit("Zu diesem Eintrag gibt es keine Person bzw. kein Zimmer mehr.", "warnung")
            return None
    if zimmer is not None and zimmer not in stand.lage.zimmer:
        zustand.meldung.emit(f"Zimmer {zimmer.removeprefix('GS-')} ist unbekannt.", "warnung")
        return None
    for k in list(_offen):
        if k.zid == zimmer and (zimmer is not None or k.person == person):
            if person:
                k.person_waehlen(person)
            k.showNormal()
            k.raise_()
            k.activateWindow()
            return k
    k = ZimmerKarte(stand, zustand, zimmer, person, parent.window() if parent is not None else None)
    _offen.append(k)
    k.destroyed.connect(lambda *_: _offen.remove(k) if k in _offen else None)
    k.show()
    return k


class ZimmerKarte(QDialog):
    def __init__(self, stand: zp.Planstand, zustand, zid: str | None, person: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window, True)                     # eigenes Fenster, nicht modal
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.stand, self.z, self.zid, self.person = stand, zustand, zid, person
        self._speichert = False
        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inhalt = QWidget()
        inhalt.setObjectName("seiteninhalt")
        self.v = QVBoxLayout(inhalt)
        self.v.setContentsMargins(24, 20, 24, 20)
        self.v.setSpacing(14)
        scroll.setWidget(inhalt)
        aussen.addWidget(scroll)
        self._neu_timer = QTimer(self, singleShot=True, interval=150, timeout=self._neu_laden)
        zustand.listen_geaendert.connect(self._von_aussen)
        zustand.zimmer_geaendert.connect(self._von_aussen)
        self._aufbauen()
        bildschirm = self.screen().availableGeometry() if self.screen() else None
        b, h = (1120, 840) if zid else (640, 640)
        if bildschirm is not None:
            b, h = min(b, int(bildschirm.width() * 0.94)), min(h, int(bildschirm.height() * 0.9))
        self.resize(b, h)

    # ------------------------------------------------------------------ Aufbau

    def _aufbauen(self) -> None:
        leeren(self.v)
        heute = date.today()
        z = self.stand.lage.zimmer.get(self.zid) if self.zid else None
        self.bewohner = zp.bewohner_im_zimmer(self.stand, self.zid, heute) if z else []
        if z is None:
            b = next((x for x in self.stand.bedarf if x.schluessel == self.person), None)
            self.setWindowTitle(b.name if b else "Person")
            self.v.addWidget(label(b.name if b else "Person", "seitentitel"))
            if b is not None:
                bw = zp.Bewohner(b.schluessel, b.name, b.massnahme, b.gruppe, b.von, b.bis, "", "geplant", b)
                self.v.addWidget(PersonBlock(self, bw))
            self.v.addStretch()
            return
        self.setWindowTitle(f"Zimmer {z.kurz}")
        kopf = QHBoxLayout()
        kopf.addWidget(label(f"Zimmer {z.kurz}", "seitentitel"))
        kopf.addStretch()
        self.v.addLayout(kopf)
        status, _ = self.stand.lage.status_am(z.id, heute)
        merk = QWidget()
        fl = FlowLayout(merk, abstand=6)
        fl.addWidget(Pille(STATUS_TEXT[status].capitalize() + " heute",
                           {"frei": "ok", "teilweise": "knapp", "gesperrt": "ueber"}.get(status, "neutral")))
        fl.addWidget(label(f"{zp.flur_text(z)} · {z.betten} Bett{'en' if z.betten > 1 else ''}", "muted"))
        from .. import zimmerliste as zl

        if z.renoviert or z.boden:
            fl.addWidget(label(" · ".join(t for t in (f"renoviert {zl.reno_text(z)}" if z.renoviert else "",
                                                      f"Boden {zl.boden_text(z)}" if z.boden else "") if t), "muted"))
        for text, an in (("Tiere erlaubt", z.tiere), ("nur Männer (Bad über den Flur)", z.nur_maenner),
                         ("Gästezimmer", z.gaeste), ("Doppelzimmer", z.betten > 1)):
            if an:
                fl.addWidget(Pille(text, "akzent"))
        from .. import maengel as mg

        if (offen := mg.offen(z.id)):
            p = Pille(f"{len(offen)} Mangel" if len(offen) == 1 else f"{len(offen)} Mängel", "ueber")
            p.setToolTip("<br>".join(f"{m.text} – seit {m.seit:%d.%m.%Y}" for m in offen))
            fl.addWidget(p)
        if status in ("frei", "teilweise"):
            bis = self.stand.lage.frei_bis(z.id, heute)
            fl.addWidget(label(f"frei bis {bis:%d.%m.%Y}" if bis else "frei ohne Folgebelegung", "fett"))
        self.v.addWidget(merk)

        # Bewohner | Zum Zimmer – nebeneinander, bei schmalem Fenster untereinander
        self.spalten = QBoxLayout(QBoxLayout.LeftToRight)
        self.spalten.setSpacing(14)
        links = Karte("Bewohner", "heute und kommende – Person wählen")
        links.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)      # wächst mit der gewählten Person
        self.wahl_zeile = QWidget()
        self._wahl = FlowLayout(self.wahl_zeile, abstand=6)
        self._gruppe = QButtonGroup(self)
        self._gruppe.setExclusive(True)
        links.inhalt.addWidget(self.wahl_zeile)
        self.person_platz = QVBoxLayout()
        links.inhalt.addLayout(self.person_platz)
        if not self.bewohner:
            links.inhalt.addWidget(label("Niemand wohnt im Zimmer oder kommt noch.", "muted"))
        start = next((i for i, bw in enumerate(self.bewohner) if bw.schluessel == self.person),
                     next((i for i, bw in enumerate(self.bewohner) if bw.von <= heute), 0))
        self._mehr = None
        for i, bw in enumerate(self.bewohner):
            b = knopf(f"{zp.anzeige_name(bw.name)} · {zeitraum(bw.von, bw.bis)}" + ("" if bw.von <= heute else " (kommt)"), "chip")
            b.setCheckable(True)
            b.setToolTip(f"{bw.massnahme or zp.GRUPPE_LABEL.get(bw.gruppe, '')} · {bw.quelle}")
            self._gruppe.addButton(b, i)
            self._wahl.addWidget(b)
            b.setVisible(i < SICHTBAR or i == start)
        verborgen = [b for b in self._gruppe.buttons() if not b.isVisibleTo(self.wahl_zeile)]
        if verborgen:
            self._mehr = knopf(f"+ {len(verborgen)} spätere", "ghost")
            self._mehr.clicked.connect(lambda: ([b.setVisible(True) for b in self._gruppe.buttons()],
                                                self._mehr.hide()))
            self._wahl.addWidget(self._mehr)
        self._gruppe.idClicked.connect(self._person_zeigen)
        zb = ZimmerBlock(self, z)
        zb.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.spalten.addWidget(links, 3, Qt.AlignTop)
        self.spalten.addWidget(zb, 2, Qt.AlignTop)
        self.v.addLayout(self.spalten)
        if self.bewohner:
            self._gruppe.button(start).setChecked(True)
            self._person_zeigen(start)

        # Zeitstrahl und Belegungen
        karte = Karte("Zeitstrahl", "letzte Woche bis in drei Monaten")
        zs = Zeitstrahl()
        zs.SPUR = 28
        von, bis = heute - timedelta(days=7), heute + timedelta(days=83)
        zs.setzen(zp.zeitstrahl(self.stand.lage, [z], von, bis), von, bis)
        karte.inhalt.addWidget(zs)
        self.v.addWidget(karte)
        liste = Karte("Belegungen", "letzte 60 Tage und kommende")
        tab = Tabelle(["Von", "Bis", "Tage", "Wer / Was", "Art"], ["l", "l", "r", "l", "l"], dehnen=3)
        zeilen = []
        for b in sorted(self.stand.lage.belegungen.get(z.id, []), key=lambda b: b.von):
            if b.bis < heute - timedelta(days=60):
                continue
            if b.art == "freigabe":
                text, art = f"Zimmerfreigabe ({b.grund})", "Freigabe"
            else:
                text, art = zp.balken_text(b)
                art = {"belegt": "belegt", "geplant": "geplant (übernommen)", "pivot": "laut Zimmer-Pivot",
                       "gesperrt": "gesperrt"}[art]
                if b.umzug and (u := self.stand.lage.umzuege.get(b.umzug)) is not None:
                    text += (f" · Umzug aus {u.von_zimmer.removeprefix('GS-')}" if b.zimmer == u.nach_zimmer
                             else f" · Umzug nach {u.nach_zimmer.removeprefix('GS-')}")
            zeilen.append([f"{b.von:%d.%m.%Y}", f"{b.bis:%d.%m.%Y}", (b.bis - b.von).days + 1, text, art])
        tab.fuellen(zeilen)
        tab.hoehe_anpassen(10)
        liste.inhalt.addWidget(tab if zeilen else label("Keine Belegungen in den letzten 60 Tagen und danach.", "muted"))
        self.v.addWidget(liste)
        self.v.addStretch()
        self._spalten_anpassen()

    def _person_zeigen(self, i: int) -> None:
        leeren(self.person_platz)
        if 0 <= i < len(self.bewohner):
            self.person = self.bewohner[i].schluessel
            self.person_platz.addWidget(PersonBlock(self, self.bewohner[i]))

    def person_waehlen(self, schluessel: str) -> None:
        i = next((i for i, bw in enumerate(self.bewohner) if bw.schluessel == schluessel), None)
        if i is not None:
            self._gruppe.button(i).setVisible(True)
            self._gruppe.button(i).setChecked(True)
            self._person_zeigen(i)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._spalten_anpassen()

    def _spalten_anpassen(self) -> None:
        if getattr(self, "spalten", None) is not None and self.zid:
            self.spalten.setDirection(QBoxLayout.LeftToRight if self.width() >= 1060 else QBoxLayout.TopToBottom)

    # ------------------------------------------------------------------ Aktualisieren

    def _von_aussen(self) -> None:
        if self._speichert:
            return
        if self.isMinimized():                 # beim Zurückholen nachladen
            self._nachladen = True
        else:
            self._neu_timer.start()

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        from PySide6.QtCore import QEvent

        if e.type() == QEvent.WindowStateChange and not self.isMinimized() and getattr(self, "_nachladen", False):
            self._nachladen = False
            self._neu_timer.start()

    def _neu_laden(self) -> None:
        try:
            self.stand = zp.laden()
        except Exception as e:            # noqa: BLE001 – Karte bleibt mit altem Stand offen, aber nicht still
            logging.getLogger(__name__).exception("Zimmerkarte neu laden")
            self.z.meldung.emit(f"Zimmerkarte konnte nicht neu laden: {e}", "fehler")
            return
        if self.zid and self.zid not in self.stand.lage.zimmer:
            self.close()
            return
        self._aufbauen()

    def gespeichert(self, meldung: str | None = None) -> None:
        """Nach einer Änderung: alle Seiten (und andere Karten) neu berechnen, diese Karte neu aufbauen."""
        self._speichert = True
        try:
            if meldung:
                self.z.meldung.emit(meldung, "ok")
            self.z.zimmer_geaendert.emit()
        finally:
            self._speichert = False
        self._neu_laden()


class PersonBlock(QWidget):
    """Wichtigste Felder zu einem Bewohner: Zimmer, Abreise, Notizen mit Wiedervorlage."""

    def __init__(self, karte: ZimmerKarte, bw: zp.Bewohner):
        super().__init__()
        self.karte, self.bw = karte, bw
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(10)
        v.addWidget(label(zp.anzeige_name(bw.name), "kartentitel"))
        if zp.name_fehlt(bw.name):              # ehrlich kennzeichnen, Rohwert zeigen – nichts erfinden
            v.addWidget(Hinweis(f"Im Gebäudeplan steht kein Name („{bw.name or 'leer'}“). Bitte im Belegungssystem "
                                "prüfen – Zimmer und Zeitraum stimmen, nur der Name fehlt im Export.", "warnung"))
        gruppe = bw.massnahme or zp.GRUPPE_LABEL.get(bw.gruppe, bw.gruppe)
        v.addWidget(label(f"{gruppe} · {bw.von:%d.%m.%Y} – {bw.bis:%d.%m.%Y} · "
                          f"{bw.quelle if bw.zimmer else 'noch kein Zimmer'}",
                          "muted", umbruch=True))
        personen, _ = anreiseliste.laden()
        self.anreise_person = next((p for p in personen if p.schluessel == bw.schluessel), None)
        self.zimmer = self.abreise = self.offen = None
        self._wahl = None
        heute = date.today()
        self.bel = next((b for b in karte.stand.lage.belegungen.get(bw.zimmer, []) if b.von == bw.von
                         and b.bis == bw.bis and b.name == bw.name and b.art == bw.art), None)
        # Eingezogen (oder schon ein Umzug): Zimmerwechsel nur als Umzug ab einem Tag, nicht rückwirkend
        nur_umzug = bw.art == "belegt" or bool(bw.umzug) or bw.von <= heute
        if bw.art == "belegt" and not bw.eigene_belegung:
            v.addWidget(label("Gebucht im Belegungssystem (Gebäudeplan) – die Abreise bitte dort ändern. Ein Umzug "
                              "in ein anderes Zimmer lässt sich hier planen. Notizen und Wiedervorlagen gehen hier.",
                              "klein", umbruch=True))
            self._umzug_zeile(v)
        else:
            self._wahl = zp.zimmer_wahl(karte.stand, bw.schluessel) if bw.bedarf and not nur_umzug else None
            if nur_umzug:
                self._umzug_zeile(v)
            if self._wahl is not None and not self._wahl.gebucht:
                self.zimmer = zimmer_auswahl(self._wahl, karte.stand)
                zeile = QHBoxLayout()
                zeile.addWidget(label("Zimmer", "fett"))
                zeile.addWidget(self.zimmer)
                zeile.addStretch()
                v.addLayout(zeile)
            if self.anreise_person is not None:
                p = self.anreise_person
                zeile = QHBoxLayout()
                zeile.addWidget(label("Abreise", "fett"))
                self.abreise = DatumFeld(p.abreise or bw.bis)
                self.offen = QCheckBox("noch offen")
                self.offen.setChecked(p.abreise is None)
                self.offen.toggled.connect(lambda an: self.abreise.setEnabled(not an))
                self.abreise.setEnabled(p.abreise is not None)
                zeile.addWidget(self.abreise)
                zeile.addWidget(self.offen)
                zeile.addStretch()
                v.addLayout(zeile)
            knoepfe = QHBoxLayout()
            if self.zimmer is not None or self.abreise is not None:
                ok = knopf("Übernehmen", "primary", "haken")
                ok.setToolTip("Zimmer und Abreise speichern")
                ok.clicked.connect(self._uebernehmen)
                knoepfe.addWidget(ok)
            if bw.bedarf is not None and not bw.umzug and karte.stand.zugewiesen(bw.schluessel):
                belegt = bw.art == "belegt"
                st_k = knopf("Wieder auf geplant" if belegt else "Planung abschließen (fest)", "ghost",
                             None if belegt else "haken")
                st_k.setToolTip("Eingezogen bzw. steht fest: gilt als belegt – auch ohne neuen Gebäudeplan; "
                                "fällt aus Aufgaben → Eintragen heraus" if not belegt else "Wieder als geplant führen")
                st_k.clicked.connect(lambda _c=False, an=not belegt: self._status(an))
                knoepfe.addWidget(st_k)
            if self.anreise_person is not None:
                alle = knopf("Alle Angaben …", "ghost")
                alle.setToolTip("Geschlecht, Tier, Gruppe, Bemerkung, Abreise-Erinnerung – oder Person entfernen")
                alle.clicked.connect(self._alle_angaben)
                knoepfe.addWidget(alle)
            knoepfe.addStretch()
            v.addLayout(knoepfe)
            self.info = label("", "klein", umbruch=True)
            v.addWidget(self.info)
        v.addWidget(label("Notizen zur Person", "abschnitt"))
        notizen = NotizenWidget(bw.schluessel, bw.name, platzhalter="z. B. „Kostenzusage nachfragen“")
        notizen.geaendert.connect(karte.z.termine_geaendert.emit)
        v.addWidget(notizen)

    def _umzug_status(self, u) -> None:
        from .. import umzug as um
        from .aenderung_ui import ausfuehren

        k = self.karte
        text = f"{u.name}: Umzug " + ("wieder geplant" if u.belegt else "abgeschlossen (fest)")
        if ausfuehren(k, k.z, text, lambda: um.status_setzen(u.id, not u.belegt, "Zimmerkarte"), text + "."):
            k.gespeichert()

    def _umzug_zeile(self, v: QVBoxLayout) -> None:
        """Umzug: bestehenden zeigen (ändern, zurücknehmen) oder neuen planen."""
        from .. import umzug as um
        from .umzug_dialog import umzug_oeffnen, zurueck_nehmen

        k, b = self.karte, self.bel
        if b is None:
            return
        zeile = QHBoxLayout()
        u = k.stand.lage.umzuege.get(b.umzug) if b.umzug else None
        if u is not None:
            text = label(f"<b>Umzug:</b> {u.von_zimmer.removeprefix('GS-')} → {u.nach_zimmer.removeprefix('GS-')} "
                         f"ab {u.ab:%d.%m.%Y}" + (f" · {u.grund}" if u.grund else "") + f"<br>{u.status_text}",
                         "klein", umbruch=True)
            v.addWidget(text)
            aendern = knopf("Umzug ändern …", "ghost", "kalender")
            aendern.clicked.connect(lambda: umzug_oeffnen(k, k.z, uid=u.id) and k._neu_laden())
            weg = knopf("Umzug zurücknehmen", "ghost")
            weg.clicked.connect(lambda: zurueck_nehmen(k, k.z, u.id) and k._neu_laden())
            zeile.addWidget(aendern)
            if u.status in ("aktiv", "konflikt"):
                st_k = knopf("Wieder auf geplant" if u.belegt else "Umzug abschließen (fest)", "ghost",
                             None if u.belegt else "haken")
                st_k.setToolTip("Umzug ist erfolgt: neues Zimmer gilt als belegt – auch ohne neuen Gebäudeplan"
                                if not u.belegt else "Umzug wieder als geplant führen")
                st_k.clicked.connect(lambda _c=False: self._umzug_status(u))
                zeile.addWidget(st_k)
            zeile.addWidget(weg)
        elif b.bis >= date.today():
            neu = knopf("Zimmer wechseln (Umzug ab …) …", "ghost", "haus")
            neu.setToolTip("Ab einem Tag in ein anderes Zimmer – das alte wird danach frei")
            neu.clicked.connect(lambda: umzug_oeffnen(k, k.z, zid=b.zimmer, schluessel=um.schluessel_zu(k.stand, b),
                                                      name=b.name) and k._neu_laden())
            zeile.addWidget(neu)
        zeile.addStretch()
        v.addLayout(zeile)

    def _status(self, belegt: bool) -> None:
        from .aenderung_ui import ausfuehren

        text = f"{self.bw.name}: {'Planung abgeschlossen (fest)' if belegt else 'wieder geplant'}"
        if ausfuehren(self.karte, self.karte.z, text, lambda: zp.status_setzen(self.bw.schluessel, belegt), text + "."):
            self.karte.gespeichert()

    def _zimmer_setzen(self, neu_zimmer: str) -> bool:
        """Zimmer ändern bzw. Planung entfernen – vorher sagen, was sich ändert (alt → neu, „fest“ entfällt)."""
        from .aenderung_ui import ausfuehren

        k, name = self.karte, self.bw.name
        zw = k.stand.zugewiesen(self.bw.schluessel) or {}
        alt = (zw.get("zimmer") or "").removeprefix("GS-") or "–"
        neu = neu_zimmer.removeprefix("GS-")
        fest = zw.get("status") == "belegt"
        if not neu_zimmer:
            if QMessageBox.question(k, "Planung entfernen", f"Die Planung von {name} entfernen?\n\nVorher: {alt}  →  "
                                    "nachher: ohne Zimmer. Das Zimmer wird frei, die Person steht unter Zuteilen."
                                    + ("\n\nDie Planung war „fest“." if fest else "")) != QMessageBox.Yes:
                return False
        elif zw.get("zimmer"):                 # Wechsel: derselbe Ablauf wie im Zeitstrahl (Regeln, DZ-Partner, Vorschau)
            from .aenderung_ui import zimmer_wechseln_geplant

            return zimmer_wechseln_geplant(k, k.z, k.stand, self.bw.schluessel, neu_zimmer, "Zimmerkarte")
        titel = f"{name}: {alt} → {neu or 'ohne Zimmer'}"
        return ausfuehren(k, k.z, titel, lambda: zp.zuweisung_setzen(k.stand, self.bw.schluessel, neu_zimmer, "Zimmerkarte"),
                          titel + ".")

    def _uebernehmen(self) -> None:
        from .dialoge import person_uebernehmen

        neu_zimmer = None
        if self.zimmer is not None:
            gewaehlt = self.zimmer.currentData() or ""
            if gewaehlt != self._wahl.geplant:
                neu_zimmer = gewaehlt
        p = self.anreise_person
        neu_p = None
        if p is not None and self.abreise is not None:
            abreise = None if self.offen.isChecked() else self.abreise.datum()
            if abreise is not None and abreise < p.anreise:
                self.info.setText("<b>Die Abreise liegt vor der Anreise.</b>")
                return
            if abreise != p.abreise:
                neu_p = replace(p, abreise=abreise, abreise_quelle="hand", erledigt=False)
                if abreise is None:
                    neu_p.erinnerung_tage, neu_p.erinnerung_kanal = None, ""
        if neu_zimmer is None and neu_p is None:
            self.info.setText("Nichts geändert.")
            return
        k = self.karte
        if neu_zimmer is not None and not self._zimmer_setzen(neu_zimmer):
            return
        k._speichert = True
        try:
            if neu_p is not None:
                person_uebernehmen(p, neu_p, k.z, neu_zimmer)
            else:
                k.z.zimmer_geaendert.emit()
        finally:
            k._speichert = False
        if neu_zimmer is not None and k.zid and neu_zimmer != k.zid:
            ziel, eltern, zustand = neu_zimmer or None, k.parent(), k.z   # umgezogen: Karte des neuen Zimmers
            k.close()
            if ziel:
                karte_oeffnen(eltern, zustand, ziel, self.bw.schluessel)
            return
        k._neu_laden()

    def _alle_angaben(self) -> None:
        from .dialoge import person_bearbeiten

        k = self.karte
        k._speichert = True
        try:
            ok = person_bearbeiten(k, k.z, self.anreise_person)
        finally:
            k._speichert = False
        if ok:
            k._neu_laden()


class ZimmerBlock(Karte):
    """Zum Zimmer selbst: dauerhafter Hinweis, Notizen mit Wiedervorlage, Ausstattung."""

    def __init__(self, karte: ZimmerKarte, z: zp.Zimmer):
        super().__init__("Zum Zimmer", "Zustand, Hinweise und Wiedervorlagen")
        self.karte, self.z = karte, z
        self._maengel_bauen()
        self.inhalt.addWidget(label("Dauerhafter Hinweis", "fett"))
        zeile = QHBoxLayout()
        self.hinweis = QLineEdit(z.notiz)
        self.hinweis.setPlaceholderText("z. B. „bodentiefe Dusche“, „Fenster klemmt“")
        self.hinweis.setToolTip("Steht in den Zimmer-Stammdaten (Reiter „Zimmer“) und bei Vorschlägen")
        self.hinweis.returnPressed.connect(self._hinweis_speichern)
        zeile.addWidget(self.hinweis, 1)
        sp = knopf("Speichern", "ghost")
        sp.clicked.connect(self._hinweis_speichern)
        zeile.addWidget(sp)
        self.inhalt.addLayout(zeile)
        self.inhalt.addWidget(label("Notizen zum Zimmer", "fett"))
        notizen = NotizenWidget(zp.zimmer_schluessel(z.id), f"Zimmer {z.kurz}", platzhalter="Neue Notiz zum Zimmer …")
        notizen.geaendert.connect(karte.z.termine_geaendert.emit)
        self.inhalt.addWidget(notizen)
        e = karte.stand.lage.zkl.get(z.id)
        if e is not None:                      # Zimmerkontrollliste (nur Anzeige)
            teile = [e.info, f"{e.name} (TN {e.tn_id})" if e.name and e.tn_id else e.name, e.anmerkung]
            self.inhalt.addWidget(label("<b>Laut ZKL:</b> " + (" · ".join(t for t in teile if t) or "keine Angaben"),
                                        "klein", umbruch=True))
        ausstattung = inventar.laden().kurztext(z.id)
        self.inhalt.addWidget(label(f"<b>Ausstattung:</b> {ausstattung}" if ausstattung
                                    else "Ausstattung: noch nichts erfasst", "klein", umbruch=True))
        inv = knopf("Inventar öffnen", "ghost")
        inv.clicked.connect(lambda: karte.z.navigieren.emit("inventar"))
        self.inhalt.addWidget(inv, 0, Qt.AlignLeft)

    def _maengel_bauen(self) -> None:
        """Mängel als Vorschläge: antippen = offen (seit heute), noch einmal = behoben. Filterbar unter Zimmerplan →
        Zimmer („Mängel“), druckbar als Mängelliste für das FM."""
        from .. import maengel as mg

        offen = {m.art: m for m in mg.offen(self.z.id)}
        kopf = QHBoxLayout()
        kopf.addWidget(label("Zustand", "fett"))
        kopf.addWidget(label("– antippen, was nicht in Ordnung ist; nochmal antippen, wenn behoben", "klein"), 1)
        self.inhalt.addLayout(kopf)
        feld = QWidget()
        fl = FlowLayout(feld, abstand=5)
        # offene zuerst, dann die übrigen Vorschläge
        for art, text in sorted(mg.KATALOG, key=lambda x: x[0] not in offen):
            b = knopf(text, "chip", "werkzeug" if art in offen else None)
            b.setCheckable(True)
            b.setChecked(art in offen)
            b.setToolTip(f"Offen seit {offen[art].seit:%d.%m.%Y} – antippen, wenn behoben" if art in offen
                         else "Als Mangel melden")
            b.toggled.connect(lambda an, a=art, t=text: self._mangel(a, t, an))
            fl.addWidget(b)
        self.inhalt.addWidget(feld)

    def _mangel(self, art: str, text: str, an: bool) -> None:
        from .. import maengel as mg

        k = self.karte
        if not mg.setzen(self.z.id, art, an):
            return
        k._speichert = True                    # diese Karte nicht neu aufbauen (Chips stimmen schon)
        try:
            k.z.meldung.emit(f"Zimmer {self.z.kurz}: {text} – " + ("gemeldet." if an else "behoben."), "ok")
            k.z.zimmer_geaendert.emit()
        finally:
            k._speichert = False

    def _hinweis_speichern(self) -> None:
        text = self.hinweis.text().strip()
        if text == self.z.notiz:
            return
        st = self.karte.stand
        for z in st.zimmer:
            if z.id == self.z.id:
                z.notiz = text
        zp.stammdaten_speichern(st.zimmer, st.plan)
        self.karte.gespeichert(f"Hinweis zu Zimmer {self.z.kurz} gespeichert.")


def zimmer_auswahl(w: zp.ZimmerWahl, stand: zp.Planstand) -> QComboBox:
    """Auswahlliste wie beim Zuteilen: zulässige Zimmer, unter dem Strich Ausnahmen mit kurzem Grund."""
    box = QComboBox()
    box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(22)
    box.addItem("– kein Zimmer –", "")
    ids = {z.id for z in w.alternativen} | {z.id for z, _g in w.ausnahmen}
    if w.geplant and w.geplant not in ids and w.geplant in stand.lage.zimmer:
        box.addItem(f"{stand.lage.zimmer[w.geplant].kurz} · bisher (Regel verletzt)", w.geplant)
    for z in w.alternativen:
        box.addItem(z.kurz + (" · DZ" if z.betten > 1 else ""), z.id)
        box.setItemData(box.count() - 1, zp.flur_text(z), Qt.ToolTipRole)
    if w.ausnahmen:
        box.insertSeparator(box.count())
        for z, grund in w.ausnahmen:
            box.addItem(f"{z.kurz} · {grund}", z.id)
            box.setItemData(box.count() - 1, f"Ausnahme: {grund}", Qt.ToolTipRole)
    box.setCurrentIndex(max(0, box.findData(w.geplant)))
    box.setToolTip("Oben die zulässigen Zimmer, unter dem Strich Ausnahmen (nur von Hand)")
    return box
