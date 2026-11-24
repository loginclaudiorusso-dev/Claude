"""1.59: Zusätzliche Belegungen im Management-Szenario – „was wäre, wenn …“ für Mieter, Events, Gruppen.

Jede Zeile: Bezeichnung, Plätze, von, bis (Tage). Für einen Monat zählt der Anteil der Tage, an denen die Belegung läuft
(die Prognose rechnet in durchschnittlich belegten Plätzen je Monat): 10 Plätze vom 16. bis 31. eines 31-Tage-Monats
ergeben dort 5,2. Mehrere Zeilen addieren sich. Rein, ohne NiceGUI; gespeichert wird nichts (Simulation).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

ARTEN = {"mieter": "Mieter", "event": "Event / Tagung", "gruppe": "Gruppe / Kurs", "sonst": "Sonstiges"}


@dataclass
class Zusatz:
    art: str
    name: str
    plaetze: int
    von: date
    bis: date

    @property
    def text(self) -> str:
        return (f"{self.plaetze} {ARTEN.get(self.art, self.art)}" + (f" „{self.name}“" if self.name else "") +
                f" · {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y}")


def im_monat(z: Zusatz, monat: date) -> float:
    """Durchschnittlich belegte Plätze dieser Zeile im Monat ``monat`` (1. des Monats)."""
    tage = calendar.monthrange(monat.year, monat.month)[1]
    anfang, ende = monat.replace(day=1), monat.replace(day=tage)
    von, bis = max(z.von, anfang), min(z.bis, ende)
    if bis < von or z.plaetze <= 0:
        return 0.0
    return z.plaetze * ((bis - von).days + 1) / tage


def je_monat(liste: list[Zusatz], monate: list[date]) -> list[float]:
    return [sum(im_monat(z, m) for z in liste) for m in monate]


def neu(art: str, name: str, plaetze, von: date, monate: int = 0, bis: date | None = None) -> Zusatz:
    """Zeile aus Eingaben – ``monate`` (z. B. Mietdauer) oder ``bis``; prüft die Werte."""
    try:
        n = int(plaetze)
    except (TypeError, ValueError):
        raise ValueError("Bitte die Zahl der Plätze eintragen.") from None
    if n <= 0 or n > 2000:
        raise ValueError("Plätze: bitte eine Zahl zwischen 1 und 2000.")
    if bis is None:
        if monate <= 0:
            raise ValueError("Bitte „bis“ oder die Dauer in Monaten angeben.")
        j, m = divmod(von.month - 1 + monate, 12)
        tag = min(von.day, calendar.monthrange(von.year + j, m + 1)[1])
        bis = date(von.year + j, m + 1, tag) - timedelta(days=1)
    if bis < von:
        raise ValueError("„bis“ liegt vor „von“.")
    return Zusatz(art if art in ARTEN else "sonst", (name or "").strip()[:60], n, von, bis)
