"""Hinweise aus den Anreiselisten (Spalte „Internatsdienst“ bzw. Bemerkung) und die Allergiker-Etage.

Die Bemerkung ist Freitext („ev. Anr. 11.10. benötigt Duschhocker“, „Allergiker“ …). Erkannt werden wenige, klar
umrissene Arten – alles andere bleibt als Text sichtbar, wird aber nicht gedeutet. Allergiker gehören auf die
Allergiker-Etage (Haus 2, 1. OG) und werden dort bevorzugt untergebracht – auch mit langer Maßnahme und auch in den
EMR-Zimmern 101–110 (die Etagen-Regeln des Hauptprogramms gelten für sie nicht); alle anderen Prüfungen bleiben. Ohne Qt/NiceGUI, damit es testbar bleibt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

ALLERGIE_HAUS, ALLERGIE_ETAGE = "2", "1"
ALLERGIE_TEXT = "Allergiker-Etage (Haus 2, 1. OG)"


@dataclass(frozen=True)
class Hinweis:
    art: str          # allergie | hilfsmittel | begleitung | vortag
    text: str         # kurz für die Marke, z. B. „Duschhocker“
    symbol: str       # Material-Icon


# (Art, Muster, Symbol, Kurztext – None = Fundstelle als Text). Bewusst eng: lieber nichts deuten als falsch deuten.
_MUSTER = [
    ("allergie", r"allerg\w*|hausstaub\w*|milben\w*|pollen\w*|tierhaar\w*", "spa", "Allergiker"),
    ("hilfsmittel", r"duschhocker|duschstuhl|rollator|rollstuhl|gehhilfe|unterarmgehst\w*|krücken|toilettensitzerh\w*|"
                    r"pflegebett|barrierefrei\w*|ebenerdig", "accessible", None),
    ("begleitung", r"(ehe)?(mann|frau|partner\w*)\b[^.;]{0,40}mitbring\w*|mitbring\w*[^.;]{0,40}(ehe)?(mann|frau|partner\w*)|"
                   r"begleitperson|begleitung", "group", "Begleitung"),
    ("vortag", r"\b(ev|evtl|eventuell)\.?\s*anr(eise)?\b\.?|anreise am vortag|vorabend", "event", "evtl. Vortag"),
]


def erkennen(bemerkung: str) -> list[Hinweis]:
    """Hinweise in einer Bemerkung – je Art höchstens einer, in fester Reihenfolge."""
    text = (bemerkung or "").strip()
    if not text:
        return []
    erg = []
    for art, muster, symbol, kurz in _MUSTER:
        m = re.search(muster, text, re.IGNORECASE)
        if m:
            erg.append(Hinweis(art, kurz or m.group(0).strip().capitalize(), symbol))
    return erg


def rest(bemerkung: str) -> str:
    """Was nach dem Standard „ev. Anr. 11.10.“ (EMR) an eigenem Text übrig bleibt – leer = nichts Besonderes."""
    t = re.sub(r"\b(ev|evtl|eventuell)\.?\s*anr(eise)?\b\.?\s*(am\s*)?(\d{1,2}\.\d{1,2}\.(\d{2,4})?)?", " ",
               bemerkung or "", flags=re.IGNORECASE)
    t = re.sub(r"^[\s;,.:–-]+|[\s;,.:–-]+$", "", t)
    return t if len(t) >= 3 else ""


def allergiker(bemerkung: str) -> bool:
    return any(h.art == "allergie" for h in erkennen(bemerkung))


def auf_allergie_etage(zimmer) -> bool:
    return zimmer is not None and zimmer.haus == ALLERGIE_HAUS and zimmer.etage == ALLERGIE_ETAGE


# Mängel, die für Allergiker ein Zimmer ausschließen (auch wenn es sonst bewohnbar ist)
ALLERGIE_MEIDEN = {"schimmel", "ungeziefer", "geruch", "boden_dreckig"}


def meiden(offene_maengel: dict) -> set[str]:
    """Zimmer-IDs mit offenen Mängeln, die für Allergiker nicht in Frage kommen."""
    return {zid for zid, ms in offene_maengel.items() if any(m.art in ALLERGIE_MEIDEN for m in ms)}


# Diese Regeln des Hauptprogramms gelten für Allergiker auf der Allergiker-Etage nicht: Die Etage ist für sie da,
# Allergiker kommen selten – wer kommt, wird dort bevorzugt untergebracht (auch mit langer Maßnahme, auch in 101–110).
ETAGEN_REGEL = "Haus 2, 1. OG nur für Kurzmaßnahmen"


def _etagenregel(grund: str | None, zimmer) -> bool:
    from belegung import zimmerplan as zp

    return grund == ETAGEN_REGEL or bool(grund and grund.endswith(f" nicht in {zp.flur_text(zimmer)}"))


def allergie_zimmer(lage, b, vergeben: set[str] = frozenset(), nicht: set[str] = frozenset()) -> list:
    """Freie Zimmer auf der Allergiker-Etage für den Bedarf ``b`` – alle Prüfungen des Hauptprogramms (belegt,
    gesperrt, unbewohnbar, Doppelzimmer, Geschlecht, Tier …) gelten, nur die Etagen-Regeln (Kurzmaßnahmen, EMR-Zimmer)
    nicht. Reihenfolge: ohne Ausnahme zulässig zuerst, die EMR-Zimmer 101–110 zuletzt."""
    from belegung import zimmerplan as zp

    erg = []
    for z in lage.zimmer.values():
        if not auf_allergie_etage(z) or z.id in vergeben or z.id in nicht:
            continue
        grund = zp.passt(lage, z, b, frozenset({b.schluessel}))
        if grund is None or _etagenregel(grund, z):
            erg.append((grund is not None, zp.nur_emr(z), z.nummer, z))
    return [z for *_r, z in sorted(erg, key=lambda x: x[:3])]


def allergie_vorschlag(zt, vergeben: set[str], nicht: set[str] = frozenset(), lage=None):
    """Zimmer auf der Allergiker-Etage aus den zulässigen Alternativen des Hauptprogramms (nicht schon an andere
    derselben Anreise vorgeschlagen, ohne Schimmel/Ungeziefer/Geruch/Schmutz). None, wenn der Vorschlag schon dort
    liegt (und unbedenklich ist) oder dort nichts Passendes frei ist."""
    if auf_allergie_etage(zt.zimmer) and zt.zimmer.id not in nicht:
        return None
    if lage is not None:
        return next(iter(allergie_zimmer(lage, zt.bedarf, vergeben, nicht)), None)
    return next((z for z in zt.alternativen if auf_allergie_etage(z) and z.id not in vergeben and z.id not in nicht), None)


@dataclass
class AllergieFall:
    schluessel: str
    name: str
    anreise: date
    zimmer: str        # Zimmer-ID (gespeichert) oder ""
    auf_etage: bool


def allergie_faelle(stand, heute: date, tage: int = 21) -> list[AllergieFall]:
    """Allergiker mit Anreise in den nächsten ``tage`` Tagen (oder schon da und noch nicht abgereist) – mit dem
    gespeicherten Zimmer und ob es auf der Allergiker-Etage liegt."""
    from datetime import timedelta

    erg = []
    for b in stand.bedarf:
        if not allergiker(b.bemerkung) or b.bis < heute or b.von > heute + timedelta(days=tage):
            continue
        zw = stand.zugewiesen(b.schluessel) or {}
        zid = zw.get("zimmer", "") or ""
        erg.append(AllergieFall(b.schluessel, b.name, b.von, zid, auf_allergie_etage(stand.lage.zimmer.get(zid))))
    return sorted(erg, key=lambda f: (f.anreise, f.name))
