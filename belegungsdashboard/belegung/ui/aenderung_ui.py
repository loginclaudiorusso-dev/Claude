"""Einheitlicher Ablauf für Änderungen an der Zimmerplanung: Vorschau → Speichern → Rückmeldung mit „Rückgängig“.

``ausfuehren`` merkt den Stand davor, speichert und meldet nur nach echtem Erfolg. Schlägt etwas fehl, wird der Stand
davor wiederhergestellt, damit keine halbe Änderung bleibt. ``VorschauDialog`` zeigt vor dem Speichern, was sich für
wen ändert, und sperrt das Speichern, solange es Konflikte gibt.
"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QVBoxLayout

from .. import aenderungen
from .widgets import Hinweis, Karte, knopf, label

log = logging.getLogger(__name__)

GRUPPEN = [("umgeplant", "Umgeplant – war schon gespeichert",
            "Diese Personen hatten schon ein gespeichertes Zimmer und bekommen ein anderes."),
           ("entfernt", "Planung wird entfernt", "Diese Personen stehen danach ohne Zimmer da."),
           ("neu", "Neu geplant", "Bisher ohne Zimmer.")]


class VorschauDialog(QDialog):
    """Zeigt eine ``aenderungen.Vorschau``: Konflikte (blockieren), dann je Art „vorher → nachher“ mit Folgen."""

    def __init__(self, vorschau: aenderungen.Vorschau, titel: str, knopf_text: str = "Änderungen speichern",
                 einleitung: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titel)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label(titel, "seitentitel"))
        if einleitung:
            v.addWidget(label(einleitung, "muted", umbruch=True))
        if vorschau.konflikte:
            v.addWidget(Hinweis("<b>Erst lösen – so wird nichts gespeichert:</b><br>" + "<br>".join(vorschau.konflikte),
                                "fehler"))
        for art, ueberschrift, erklaerung in GRUPPEN:
            liste = vorschau.nach_art(art)
            if not liste:
                continue
            karte = Karte(f"{ueberschrift} ({len(liste)})", erklaerung)
            for a in liste:
                zeile = f"<b>{a.name}</b>: {a.alt.removeprefix('GS-') or '–'} → <b>{a.neu.removeprefix('GS-') or '–'}</b>"
                if a.von and a.bis:
                    zeile += f" <span style='color:gray'>({a.von:%d.%m.} – {a.bis:%d.%m.%Y})</span>"
                if not a.angefordert:
                    zeile += " · <i>Vorschlag</i>"
                if a.folgen and art != "neu":
                    zeile += "<br><span style='color:gray'>" + " · ".join(a.folgen) + "</span>"
                karte.inhalt.addWidget(label(zeile, umbruch=True))
            v.addWidget(karte)
        if vorschau.leer:
            v.addWidget(label("Keine Änderung – alles ist schon so gespeichert.", "muted"))
        v.addStretch()
        unten = QHBoxLayout()
        unten.addStretch()
        ab = knopf("Abbrechen", "ghost")
        ab.clicked.connect(self.reject)
        n = len(vorschau.aenderungen)
        self.ok = knopf(f"{knopf_text} ({n})" if n else knopf_text, "primary", "haken")
        self.ok.setEnabled(not vorschau.konflikte and not vorschau.leer)
        self.ok.clicked.connect(self.accept)
        self.ok.setDefault(True)
        unten.addWidget(ab)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        from .dialoge import scrollbar_machen

        scrollbar_machen(self, 640, 620)


def bestaetigen(parent, vorschau: aenderungen.Vorschau, titel: str, knopf_text: str = "Änderungen speichern",
                einleitung: str = "", immer: bool = False) -> bool:
    """Einfache Fälle (nur neue Planungen, keine Konflikte) ohne Dialog – sonst Vorschau zeigen."""
    if vorschau.einfach and not immer:
        return True
    return VorschauDialog(vorschau, titel, knopf_text, einleitung, parent).exec() == QDialog.Accepted


def ausfuehren(parent, zustand, titel: str, aktion: Callable[[], object],
               meldung: str | Callable[[object], str], art: str = "ok", rueckgaengig: bool = True) -> bool:
    """``aktion`` speichern (alles oder nichts), danach Meldung – mit „Rückgängig“, wenn ``rueckgaengig``.
    Neu laden bzw. ``zimmer_geaendert`` macht der Aufrufer.

    Gibt True nur zurück, wenn wirklich gespeichert wurde. Bei einem Fehler bleibt bzw. wird der Stand davor.
    ValueError (fachlich abgelehnt, z. B. Zimmer inzwischen belegt) wird als Hinweis gezeigt, nicht als Absturz."""
    vorher = aenderungen.schnappschuss()
    try:
        ergebnis = aktion()
    except Exception as exc:              # noqa: BLE001 – jeder Fehler: nichts halb gespeichert lassen
        if isinstance(exc, ValueError):
            log.info("Abgelehnt: %s – %s", titel, exc)
        else:
            log.exception("Speichern fehlgeschlagen: %s", titel)
        try:
            if aenderungen.schnappschuss() != vorher:
                for name, inhalt in vorher.items():
                    aenderungen._roh_schreiben(name, inhalt)
            zurueck = "Die Planung ist unverändert."
        except Exception:                 # noqa: BLE001
            zurueck = "Der Stand davor konnte nicht vollständig wiederhergestellt werden – bitte die Planung prüfen."
        if isinstance(exc, ValueError):
            QMessageBox.warning(parent, "Nicht gespeichert", f"{exc}\n\n{zurueck}")
        else:
            QMessageBox.critical(parent, "Nicht gespeichert", f"„{titel}“ konnte nicht gespeichert werden:\n{exc}\n\n{zurueck}")
        zustand.meldung.emit(f"Nicht gespeichert: {titel}.", "fehler")
        return False
    schritt = aenderungen.merken(titel, vorher) if rueckgaengig else None
    text = meldung(ergebnis) if callable(meldung) else meldung
    if schritt is not None:
        zustand.aenderung_gespeichert.emit(text, art)
    else:
        zustand.meldung.emit(text, art)
    return True


def rueckgaengig(parent, zustand, fragen: bool = True) -> None:
    """Letzte Änderung zurück – auf Strg+Z mit Rückfrage, die sagt, was zurückgenommen wird."""
    s = aenderungen.letzter()
    if s is None:
        zustand.meldung.emit("Nichts zum Rückgängigmachen.", "info")
        return
    if fragen and QMessageBox.question(parent, "Rückgängig", f"„{s.titel}“ rückgängig machen?\n\nDie Planung (Zimmer, Umzüge) "
                            "wird auf den Stand davor zurückgesetzt.") != QMessageBox.Yes:
        return
    ok, text = aenderungen.rueckgaengig()
    zustand.meldung.emit(text, "ok" if ok else "warnung")
    if ok:
        zustand.zimmer_geaendert.emit()
    elif "nicht mehr" in text:
        QMessageBox.information(parent, "Rückgängig nicht möglich", text)


def zimmer_wechseln_geplant(parent, zustand, stand, person: str, nach: str, quelle: str = "Zimmer gewechselt") -> bool:
    """Der eine Ablauf für „Zimmer wechseln“ bei geplanten Personen (noch nicht eingezogen) – aus Zeitstrahl und
    Personenkarte. Prüft die Regeln, sagt „vorher → nachher“ samt Folgen („fest“ entfällt, Ausnahme), fragt beim
    DZ-Partner nach (optionale Folgeänderung – nie automatisch), prüft gegen den frischen Stand und speichert
    sicher mit Rückgängig. Wer schon eingezogen ist, zieht über den Umzug-Dialog um. True = gespeichert."""
    from .. import zimmerplan as zp

    fehler, hinweis, partner = zp.verschieben_pruefen(stand, person, nach)
    if fehler:
        QMessageBox.warning(parent, "Zimmerwechsel nicht möglich", fehler)
        return False
    b = next(x for x in stand.bedarf if x.schluessel == person)
    von = (stand.zugewiesen(person) or {}).get("zimmer", "")
    z_neu = stand.lage.zimmer[nach]
    alt = von.removeprefix("GS-") or "–"
    text = (f"{b.name} ({b.von:%d.%m.} – {b.bis:%d.%m.%Y})\n\nVorher: {alt}  →  nachher: {z_neu.kurz}. "
            f"{alt} wird dafür frei.")
    if (stand.zugewiesen(person) or {}).get("status") == "belegt":
        text += "\n\nDie Planung war „fest“ – im neuen Zimmer gilt sie wieder als geplant."
    if hinweis:
        text += f"\n\nAchtung – Ausnahme: {hinweis}"
    text += "\n\nDanach im Belegungssystem umbuchen (steht unter Aufgaben → Eintragen)."
    mit: list = []
    if partner:
        ohne = frozenset({person} | {x.schluessel for x in partner})
        passt_beide = stand.lage.freie_betten(nach, b.von, b.bis, ohne) >= 1 + len(partner)
        box = QMessageBox(QMessageBox.Question, "Zimmer wechseln",
                          text + f"\n\nDZ-Partner laut Liste: {', '.join(x.name for x in partner)}."
                          + ("" if passt_beide else " Für beide ist dort kein Platz."), parent=parent)
        beide = box.addButton("Beide wechseln", QMessageBox.AcceptRole) if passt_beide else None
        allein = box.addButton(f"Nur {b.name.split(',')[0]}", QMessageBox.AcceptRole)
        box.addButton("Abbrechen", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is None or box.clickedButton() not in (beide, allein):
            return False
        if box.clickedButton() is beide:
            mit = partner
    elif QMessageBox.question(parent, "Zimmer wechseln", text) != QMessageBox.Yes:
        return False
    zts = [zp.Zuteilung(x, z_neu) for x in [b] + mit]
    v = aenderungen.zuweisungen_vorschau(zp.laden(), zts, gesehen=stand.zuweisungen)
    if v.konflikte:                       # inzwischen woanders geändert oder belegt – nichts überschreiben
        QMessageBox.warning(parent, "Zimmerwechsel nicht möglich", "\n".join(v.konflikte))
        return False
    namen = ", ".join(x.name for x in [b] + mit)
    return ausfuehren(parent, zustand, f"{namen}: {alt} → {z_neu.kurz}",
                      lambda: zp.zuweisungen_speichern(zts, quelle),
                      f"{namen}: {alt} → {z_neu.kurz}.", "warnung" if hinweis else "ok")
