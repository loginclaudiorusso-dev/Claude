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
    zimmer: str        # Zimmer-ID (gespeichert bzw. laut Gebäudeplan bewohnt) oder ""
    auf_etage: bool    # auf der Etage – oder von Hand als „passt so“ bestätigt
    bestaetigt: bool = False


def allergie_faelle(stand, heute: date, tage: int = 21) -> list[AllergieFall]:
    """Allergiker mit Anreise in den nächsten ``tage`` Tagen (oder schon da und noch nicht abgereist) – mit dem
    gespeicherten Zimmer und ob es auf der Allergiker-Etage liegt."""
    from datetime import timedelta

    erg = []
    ok_liste = bestaetigt()
    for b in stand.bedarf:
        if not allergiker(b.bemerkung) or b.bis < heute or b.von > heute + timedelta(days=tage):
            continue
        zw = stand.zugewiesen(b.schluessel) or {}
        zid = zw.get("zimmer", "") or ""
        wohnt = wohnt_in(stand, b, heute)            # 1.36: tatsächliches Zimmer (Gebäudeplan/Zimmerbelegung) gilt
        if wohnt and (not zid or not auf_allergie_etage(stand.lage.zimmer.get(zid))):
            zid = wohnt
        etage = auf_allergie_etage(stand.lage.zimmer.get(zid))
        hand = not etage and b.schluessel in ok_liste
        erg.append(AllergieFall(b.schluessel, b.name, b.von, zid, etage or hand, hand))
    return sorted(erg, key=lambda f: (f.anreise, f.name))


def wohnt_in(stand, b, heute: date) -> str:
    """1.36: In welchem Zimmer ist die Person laut Gebäudeplan bzw. Zimmerbelegung wirklich (belegt) – ab heute bzw.
    ab der Anreise? Erst über die Kennung, sonst über den Namen (alle Namensteile gleich). "" = nicht gefunden.
    Damit meldet „Allergiker nicht auf der Etage“ niemanden, der längst im richtigen Zimmer wohnt, aber nur noch im
    Gebäudeplan steht (die Zuteilung entfällt, sobald der Gebäudeplan die Buchung kennt)."""
    from belegung.zimmerplan import _namenswoerter

    tag = max(b.von, heute)
    woerter = _namenswoerter(b.name or "")
    treffer = ""
    for zid, bs in stand.lage.belegungen.items():
        for x in bs:
            if x.art not in ("belegt", "geplant") or not (x.von <= tag <= x.bis or x.von <= b.bis and b.von <= x.bis):
                continue
            if x.person and x.person == b.schluessel:
                return zid
            if woerter and x.name and _namenswoerter(x.name) == woerter and x.art == "belegt":
                treffer = treffer or zid
    return treffer


# ---- 1.36: „Passt so“ – von Hand bestätigt (gilt für alle PCs am Standort) ------------------------------------------

BESTAETIGT = "importe/modern_allergie_ok.json"


def bestaetigt() -> set[str]:
    from belegung import speicher

    try:
        d = speicher.lesen(BESTAETIGT, {})
    except Exception:                                  # noqa: BLE001 – beschädigt: nichts bestätigt
        return set()
    return set((d or {}).get("personen", {})) if isinstance(d, dict) else set()


def bestaetigen(schluessel: str, name: str = "", an: bool = True) -> str:
    """Fall als geprüft markieren („passt so“) – oder zurücknehmen. Ein Schritt mit Rückgängig."""
    from datetime import datetime

    from belegung import speicher

    from .kern import _schritt
    from .netz_kern import wer

    def aktion():
        d = speicher.lesen(BESTAETIGT, {}) or {}
        p = dict(d.get("personen", {}))
        if an:
            p[schluessel] = {"name": name, "von": wer(), "am": datetime.now().isoformat(timespec="minutes")}
        else:
            p.pop(schluessel, None)
        speicher.schreiben(BESTAETIGT, {"personen": p})
    _schritt("Allergiker geprüft" if an else "Allergiker-Prüfung zurückgenommen", aktion, [BESTAETIGT])
    return (f"{name or 'Person'}: als geprüft markiert – die Meldung verschwindet für alle" if an
            else "Prüfung zurückgenommen")
