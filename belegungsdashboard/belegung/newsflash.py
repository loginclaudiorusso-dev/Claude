"""Newsflash: alles, was gerade ansteht, an einer Stelle – ohne Klick sichtbar (wechselnde Leiste oben, Popup bei
neuen dringenden Meldungen).

Quellen: die Vorgänge von „Heute“ (dringend und als Nächstes – Anreisen ohne Zimmer, Reinigung vor Einzug,
Doppelbelegungen, Fristen, Mails, Vertragsende …) und die Neuigkeiten der letzten ``NEU_STUNDEN`` (automatisch
übernommener Gebäudeplan, UWT zugeteilt …). Rein, ohne Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from . import speicher

NEU_STUNDEN = 24
GESEHEN = "newsflash_gesehen"        # Einstellung: {Tag: [Meldungs-IDs, die schon als Popup kamen]}
STUFE_TEXT = {"dringend": "Dringend", "bald": "Als Nächstes", "neu": "Neu"}


@dataclass
class Meldung:
    id: str
    stufe: str                       # dringend | bald | neu
    text: str
    detail: str = ""
    ziel: str = ""                   # Vorgang-Ziel (z. B. „anreise:2026-10-26“) oder Neuigkeit-Ziel
    vorgang: object = None           # der Vorgang selbst (zum Öffnen über die Startseite)

    @property
    def zeile(self) -> str:
        return f"{self.text} – {self.detail}" if self.detail else self.text


def meldungen(vorgaenge: list, neuigkeiten: list, jetzt: datetime | None = None) -> list[Meldung]:
    """Vorgänge (ohne „Zur Info“) und frische Neuigkeiten – dringende zuerst, je Stufe in der Reihenfolge der Quelle."""
    jetzt = jetzt or datetime.now()
    erg: list[Meldung] = []
    for v in vorgaenge:
        if v.stufe in ("dringend", "bald"):
            erg.append(Meldung(f"v:{v.id}", v.stufe, v.titel, v.detail, v.ziel, v))
    grenze = jetzt - timedelta(hours=NEU_STUNDEN)
    for n in neuigkeiten:
        if n.zeit >= grenze:
            stufe = "dringend" if n.art in ("warnung", "fehler") else "neu"
            erg.append(Meldung(f"n:{n.id}", stufe, n.text, "", n.ziel))
    reihe = {"dringend": 0, "bald": 1, "neu": 2}
    return sorted(erg, key=lambda m: reihe[m.stufe])


def neu_fuer_popup(liste: list[Meldung], heute: date | None = None) -> list[Meldung]:
    """Dringende Meldungen, die heute noch nicht als Popup kamen."""
    heute = heute or date.today()
    schon = set(speicher.einstellungen().get(GESEHEN, {}).get(heute.isoformat(), []))
    return [m for m in liste if m.stufe == "dringend" and m.id not in schon]


def als_gesehen(liste: list[Meldung], heute: date | None = None) -> None:
    heute = heute or date.today()
    gesehen = speicher.einstellungen().get(GESEHEN, {})
    tag = heute.isoformat()
    gesehen = {tag: sorted(set(gesehen.get(tag, [])) | {m.id for m in liste})}     # nur heute merken
    speicher.einstellung_setzen(GESEHEN, gesehen)
