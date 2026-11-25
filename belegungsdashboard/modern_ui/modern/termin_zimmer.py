"""1.63: Welche Zimmer gehören zu einem An- oder Abreise-Termin („Abreise: 2 Personen (Hospitation)“)?

Die Sammeltermine kommen aus dem Hauptprogramm und nennen nur Namen. Hier werden die Personen aus dem Termin-Schlüssel
wiedergefunden (``anreise:<Tag>``, ``abreisetag:<Tag>:<emr|andere>``, ``abreise:<Person>``, ``notiz:<Person>:…``) und
ihr Zimmer aus dem Zimmerplan gesucht – zuerst die Belegung am Termin-Tag, sonst die zeitlich nächste.
Rein (ohne Oberfläche), damit testbar.
"""

from __future__ import annotations

from datetime import date

from belegung import anreiseliste


def _tag(teil: str) -> date | None:
    try:
        return date.fromisoformat(teil)
    except (TypeError, ValueError):
        return None


def personen(tid: str, alle: list) -> tuple[date | None, list]:
    """(Termin-Tag, Personen) zu einem Termin-Schlüssel; unbekannte Arten → (None, [])."""
    art, _, rest = (tid or "").partition(":")
    if art == "termin":                                   # Karte im Cockpit: „termin:<Termin-ID>“
        return personen(rest, alle)
    if art == "anreise":
        tag = _tag(rest)
        return tag, [p for p in alle if tag and anreiseliste.ankunft(p) == tag]
    if art == "abreisetag":
        teil, _, kat = rest.partition(":")
        tag = _tag(teil)
        return tag, [p for p in alle if tag and p.abreise == tag and p.internat and p.erinnerung_am is None
                     and (kat or ("emr" if anreiseliste.ist_emr(p) else "andere")) == ("emr" if anreiseliste.ist_emr(p) else "andere")]
    if art in ("abreise", "notiz"):
        schluessel = rest.split(":", 1)[0] if art == "notiz" else rest
        ps = [p for p in alle if p.schluessel == schluessel]
        return (ps[0].abreise if art == "abreise" and ps else (anreiseliste.ankunft(ps[0]) if ps else None)), ps
    return None, []


def zimmer_von(lage, schluessel: str, name: str, tag: date | None) -> str:
    """Zimmer-ID der Person: Belegung am Tag, sonst die zeitlich nächste; über den Schlüssel, notfalls über den Namen."""
    treffer = []
    for zid, bs in (getattr(lage, "belegungen", None) or {}).items():
        for b in bs:
            if b.art not in ("belegt", "geplant"):
                continue
            if (schluessel and b.person == schluessel) or (name and b.name and b.name.strip().lower() == name.strip().lower()):
                treffer.append((zid, b))
    if not treffer:
        return ""
    if tag is None:
        return treffer[0][0]

    def abstand(t) -> int:
        b = t[1]
        if b.von <= tag <= b.bis:
            return 0
        return min(abs((b.von - tag).days), abs((b.bis - tag).days))
    return min(treffer, key=abstand)[0]


def zeilen(tid: str, alle: list, lage, kurz=lambda z: z) -> list[tuple[str, str, str]]:
    """[(Name, Zimmer-Kurz oder „ohne Zimmer“, Zimmer-ID)] zu einem Termin – leer, wenn der Termin keine Personen hat."""
    tag, ps = personen(tid, alle)
    erg = []
    for p in ps:
        zid = zimmer_von(lage, p.schluessel, p.name, tag)
        erg.append((p.name, kurz(zid) if zid else "ohne Zimmer", zid))
    return erg


def tooltip(zs: list[tuple[str, str, str]], max_zeilen: int = 12) -> str:
    if not zs:
        return ""
    teile = [f"{n} – {z}" for n, z, _ in zs[:max_zeilen]]
    if len(zs) > max_zeilen:
        teile.append(f"… und {len(zs) - max_zeilen} weitere")
    return "Zimmer:\n" + "\n".join(teile)


def kurztext(zs: list[tuple[str, str, str]], max_zimmer: int = 4) -> str:
    """„Zimmer 2-101, 2-103“ (ohne doppelte) – für die Zeile selbst."""
    zim = list(dict.fromkeys(z for _n, z, zid in zs if zid))
    if not zim:
        return "noch ohne Zimmer" if zs else ""
    return "Zimmer " + ", ".join(zim[:max_zimmer]) + (f" +{len(zim) - max_zimmer}" if len(zim) > max_zimmer else "")
