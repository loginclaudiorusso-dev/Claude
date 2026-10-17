"""Mängel je Zimmer: Was im Zimmer kaputt oder schmutzig ist – zum Filtern und für das Facility-Management (FM).

In der Zimmerkarte stehen Vorschläge (Teppich beschädigt, Schimmel, Heizung …) als Chips: antippen = Mangel offen
(seit heute), noch einmal = behoben. Behobene Mängel bleiben mit Datum in der Datei (Verlauf je Zimmer); gezeigt und
gefiltert werden nur offene. Rein, ohne Qt. Gespeichert in ``zimmer_maengel.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import escape

from . import protokoll, speicher

DATEI = "zimmer_maengel.json"

KATALOG: list[tuple[str, str]] = [
    ("boden_kaputt", "Teppich/Boden beschädigt"),
    ("boden_dreckig", "Teppich/Boden verschmutzt"),
    ("wand", "Wand/Tapete beschädigt"),
    ("schimmel", "Schimmel/Feuchtigkeit"),
    ("fenster", "Fenster/Rollo defekt"),
    ("heizung", "Heizung defekt"),
    ("bad", "Bad/Dusche/WC defekt"),
    ("abfluss", "Abfluss verstopft"),
    ("wasser", "Wasserhahn tropft/undicht"),
    ("elektrik", "Licht/Steckdose defekt"),
    ("moebel", "Möbel beschädigt"),
    ("matratze", "Matratze erneuern"),
    ("tuer", "Tür/Schloss/Schlüssel defekt"),
    ("rauchmelder", "Rauchmelder defekt/fehlt"),
    ("geruch", "Geruch (Rauch u. a.)"),
    ("ungeziefer", "Ungeziefer"),
    ("grundreinigung", "Grundreinigung nötig"),
    ("renovierung", "Renovierung nötig"),        # z. B. ZKL „-> Reno“, „Reno1/Reno2“
    ("sonstiges", "Sonstiges"),
]
NAMEN = dict(KATALOG)


@dataclass
class Mangel:
    zimmer: str
    art: str
    seit: date
    behoben: date | None = None
    notiz: str = ""

    @property
    def text(self) -> str:
        return NAMEN.get(self.art, self.art) + (f" ({self.notiz})" if self.notiz else "")

    def zu_dict(self) -> dict:
        return {"zimmer": self.zimmer, "art": self.art, "seit": self.seit.isoformat(),
                "behoben": self.behoben.isoformat() if self.behoben else None, "notiz": self.notiz}

    @staticmethod
    def aus_dict(d: dict) -> "Mangel":
        return Mangel(d["zimmer"], d["art"], date.fromisoformat(d["seit"]),
                      date.fromisoformat(d["behoben"]) if d.get("behoben") else None, d.get("notiz", ""))


def laden() -> list[Mangel]:
    erg = []
    for d in speicher.lesen(DATEI, {}).get("maengel", []):
        try:
            erg.append(Mangel.aus_dict(d))
        except (KeyError, ValueError, TypeError):
            continue
    return erg


def offen(zimmer: str | None = None) -> list[Mangel]:
    return [m for m in laden() if m.behoben is None and (zimmer is None or m.zimmer == zimmer)]


def offen_je_zimmer() -> dict[str, list[Mangel]]:
    erg: dict[str, list[Mangel]] = {}
    for m in offen():
        erg.setdefault(m.zimmer, []).append(m)
    return erg


def setzen(zimmer: str, art: str, an: bool, heute: date | None = None, notiz: str = "") -> bool:
    """Mangel öffnen (an) bzw. als behoben markieren (aus). True, wenn sich etwas geändert hat."""
    heute = heute or date.today()
    alle = laden()
    offene = [m for m in alle if m.zimmer == zimmer and m.art == art and m.behoben is None]
    if an and not offene:
        alle.append(Mangel(zimmer, art, heute, None, notiz.strip()))
    elif not an and offene:
        for m in offene:
            m.behoben = heute
    else:
        return False
    speicher.schreiben(DATEI, {"maengel": [m.zu_dict() for m in alle]})
    protokoll.eintragen([{"aktion": "Mangel gemeldet" if an else "Mangel behoben", "name": NAMEN.get(art, art),
                          "person": "", "alt": zimmer if not an else "", "neu": zimmer if an else "",
                          "von": heute.isoformat(), "quelle": "Zimmerkarte"}])
    return True


def fm_text(offene: list[Mangel], kurz=lambda zid: zid.removeprefix("GS-")) -> str:
    """Zum Einfügen in eine Mail an das Facility-Management – je Zimmer eine Zeile."""
    je: dict[str, list[Mangel]] = {}
    for m in offene:
        je.setdefault(m.zimmer, []).append(m)
    zeilen = [f"Offene Mängel – Internat Goslar, Stand {datetime.now():%d.%m.%Y}", ""]
    for zid in sorted(je, key=_sort):
        zeilen.append(f"Zimmer {kurz(zid)}: " + "; ".join(f"{m.text} (seit {m.seit:%d.%m.})" for m in je[zid]))
    return "\n".join(zeilen)


def fm_html(offene: list[Mangel], kurz=lambda zid: zid.removeprefix("GS-")) -> str:
    """Druckliste für das FM: nach Haus und Zimmer, mit „seit“ und Spalte zum Abhaken."""
    from .drucklisten import _STIL

    teile = [_STIL, "<h1>Mängelliste</h1>",
             f"<div class='klein'>Internat Goslar · {len(offene)} offene Mängel in "
             f"{len({m.zimmer for m in offene})} Zimmern · Stand {datetime.now():%d.%m.%Y %H:%M}</div><br>",
             "<table class='liste' width='100%' cellspacing='0'><tr><th width='12%'>Zimmer</th><th>Mangel</th>"
             "<th width='14%'>seit</th><th width='16%'>erledigt am</th></tr>"]
    for m in sorted(offene, key=lambda m: (_sort(m.zimmer), m.art)):
        teile.append(f"<tr><td><b>{escape(kurz(m.zimmer))}</b></td><td>{escape(m.text)}</td>"
                     f"<td>{m.seit:%d.%m.%Y}</td><td></td></tr>")
    teile.append("</table>")
    if not offene:
        teile.append("<p class='leer'>Keine offenen Mängel.</p>")
    return "".join(teile)


def _sort(zid: str) -> tuple:
    haus, _, nr = zid.removeprefix("GS-").partition("-")
    try:
        h = float(haus)
    except ValueError:
        h = 99.0
    ziffern = "".join(c for c in nr if c.isdigit())
    return h, nr[:1].isalpha(), int(ziffern or 0), nr
