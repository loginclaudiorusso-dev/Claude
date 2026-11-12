"""Suche nach Umzug richtig (0.97). Rein, ohne Oberfläche.

Die Personensuche des Hauptprogramms nennt das Zimmer aus der ursprünglichen Zuteilung bzw. aus jedem Teil der
Belegung. Nach einem Umzug stand darum noch das alte Zimmer da – wer suchte, wusste nicht, wo die Person wohnt.

Hier wird je Person das Zimmer **heute** bestimmt (bzw. das Zimmer der nächsten Ankunft): Umzüge mit dem Stand
„aktiv“ oder „erledigt“ ab dem Umzugstag. Ein Umzug in der Zukunft wird als Hinweis genannt („zieht am … nach …“),
ein vergangener ebenso („umgezogen am … aus …“). Doppelte Treffer derselben Person (alter und neuer Teil der
Belegung) werden zu EINEM Treffer zusammengefasst.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

GILT = ("aktiv", "erledigt")


def _woerter(name: str) -> frozenset:
    return frozenset(w for w in "".join(c.lower() if c.isalnum() else " " for c in str(name or "")).split() if w)


def _gleich(person: str, name: str, u) -> bool:
    if person and getattr(u, "schluessel", "") == person:
        return True
    w = _woerter(name)
    return bool(w) and w == _woerter(getattr(u, "name", ""))


def _kurz(zid: str) -> str:
    return str(zid or "").removeprefix("GS-")


@dataclass
class Ort:
    zimmer: str              # Zimmer heute (bzw. ab Anreise)
    hinweis: str = ""        # „umgezogen am … aus …“ / „zieht am … nach …“


def ort(zimmer: str, person: str, name: str, von: date | None, bis: date | None, umzuege, heute: date) -> Ort:
    """Zimmer der Person heute – ``umzuege``: alle Umzüge (z. B. ``lage.umzuege.values()``)."""
    eigene = sorted((u for u in umzuege if getattr(u, "status", "") in GILT and _gleich(person, name, u)
                     and (von is None or u.ab >= von) and (bis is None or u.ab <= bis)), key=lambda u: u.ab)
    if not eigene:
        return Ort(zimmer)
    stichtag = max(heute, von) if von else heute          # wer noch nicht da ist: Zimmer bei Ankunft
    vorbei = [u for u in eigene if u.ab <= stichtag]
    kommend = [u for u in eigene if u.ab > stichtag]
    jetzt = vorbei[-1].nach_zimmer if vorbei else (eigene[0].von_zimmer or zimmer)
    teile = []
    if vorbei:
        u = vorbei[-1]
        teile.append(f"umgezogen am {u.ab:%d.%m.%Y} aus {_kurz(u.von_zimmer)}")
    if kommend:
        u = kommend[0]
        teile.append(f"zieht am {u.ab:%d.%m.%Y} nach {_kurz(u.nach_zimmer)}")
    return Ort(jetzt, " · ".join(teile))


def korrigieren(treffer: list, umzuege, heute: date) -> list[tuple[object, str]]:
    """Treffer der Hauptprogramm-Suche → [(Treffer mit Zimmer heute, Hinweis)], je Person nur einmal."""
    umzuege = list(umzuege or [])
    out: list[tuple[object, str]] = []
    gesehen: dict[tuple, int] = {}
    for t in treffer:
        if not getattr(t, "zimmer_id", "") or getattr(t, "frei", False) or getattr(t, "gesperrt", False):
            out.append((t, ""))
            continue
        o = ort(t.zimmer_id, getattr(t, "person", ""), t.name, t.von, t.bis, umzuege, heute)
        neu = replace(t, zimmer_id=o.zimmer) if o.zimmer != t.zimmer_id else t
        # dieselbe Person mit demselben Aufenthalt (Teile vor/nach dem Umzug) nur einmal
        schl = (getattr(t, "person", "") or tuple(sorted(_woerter(t.name))), o.zimmer)
        if schl in gesehen:
            i = gesehen[schl]
            alt, hinweis = out[i]
            von = min(alt.von, t.von)
            bis = None if alt.bis is None or t.bis is None else max(alt.bis, t.bis)
            out[i] = (replace(alt, von=von, bis=bis), hinweis or o.hinweis)
            continue
        gesehen[schl] = len(out)
        out.append((neu, o.hinweis))
    return out


def zimmer_heute(lage, person: str, name: str, zimmer: str, von: date | None, bis: date | None, heute: date) -> str:
    """Kurzform für Listen: Zimmer-Kennung heute (nach Umzügen) – ``lage``: ``stand.lage``."""
    if not zimmer:
        return zimmer
    return ort(zimmer, person, name, von, bis, (getattr(lage, "umzuege", None) or {}).values(), heute).zimmer
