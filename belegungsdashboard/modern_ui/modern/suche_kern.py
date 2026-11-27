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


def _wer(t) -> tuple:
    return tuple(sorted(_woerter(getattr(t, "name", ""))))


def nur_aktuell(treffer: list[tuple[object, str]], heute: date) -> list[tuple[object, str]]:
    """1.23: Nach einem Zimmerwechsel nur noch das neue Zimmer. Hat eine Person einen Aufenthalt heute oder in der
    Zukunft, fallen ihre schon beendeten Teile in ANDEREN Zimmern weg (z. B. Umzug nur im Gebäudeplan, ohne
    Umzugs-Eintrag) – das alte Zimmer steht dann als Hinweis „vorher in …“ am aktuellen Treffer."""
    aktuell: dict[tuple, int] = {}
    for i, (t, _h) in enumerate(treffer):
        if getattr(t, "zimmer_id", "") and not getattr(t, "frei", False) and not getattr(t, "gesperrt", False) \
                and (t.bis is None or t.bis >= heute):
            aktuell.setdefault(_wer(t), i)
    out: list[tuple[object, str]] = []
    vorher: dict[int, list[str]] = {}
    # 1.73: dieselbe Person „noch kein Zimmer“ neben einem Eintrag MIT Zimmer (zweiter Listeneintrag, z. B. alte
    # Anreise): weg, wenn er schon vorbei ist oder sich mit dem Aufenthalt mit Zimmer überschneidet
    mit_zimmer: dict[tuple, list] = {}
    for t, _h in treffer:
        if getattr(t, "zimmer_id", "") and not getattr(t, "frei", False) and not getattr(t, "gesperrt", False):
            mit_zimmer.setdefault(_wer(t), []).append(t)
    for i, (t, h) in enumerate(treffer):
        if not getattr(t, "zimmer_id", "") and _wer(t) in mit_zimmer and _ueberholt(t, mit_zimmer[_wer(t)], heute):
            continue
        j = aktuell.get(_wer(t))
        if (j is not None and j != i and getattr(t, "zimmer_id", "") and not getattr(t, "frei", False)
                and not getattr(t, "gesperrt", False) and t.bis is not None and t.bis < heute
                and t.zimmer_id != treffer[j][0].zimmer_id):
            vorher.setdefault(j, []).append(f"vorher in {_kurz(t.zimmer_id)} bis {t.bis:%d.%m.%Y}")
            continue
        out.append((t, h))
    if vorher:
        idx = {id(t): i for i, (t, _h) in enumerate(treffer)}
        out = [(t, h if h else " · ".join(vorher.get(idx[id(t)], []))) for t, h in out]
    return out


def _ueberholt(t, andere: list, heute: date) -> bool:
    """Eintrag ohne Zimmer, der neben Aufenthalten MIT Zimmer nichts Neues sagt: vorbei oder überschneidend."""
    von, bis = getattr(t, "von", None), getattr(t, "bis", None)
    if bis is not None and bis < heute:
        return True
    for u in andere:
        uv, ub = getattr(u, "von", None), getattr(u, "bis", None)
        if von is None or uv is None or ((ub is None or von <= ub) and (bis is None or uv <= bis)):
            return True
    return False


def aktuelle_namen(treffer: list[tuple[object, str]], heute: date) -> set[tuple]:
    """Personen mit Aufenthalt heute/zukünftig – deren frühere Zimmer gehören nicht als „früher in …“ in die Suche."""
    return {_wer(t) for t, _h in treffer if getattr(t, "zimmer_id", "") and not getattr(t, "frei", False)
            and (t.bis is None or t.bis >= heute)}


def ist_aktuell(name: str, namen: set[tuple]) -> bool:
    return tuple(sorted(_woerter(name))) in namen


def zimmer_heute(lage, person: str, name: str, zimmer: str, von: date | None, bis: date | None, heute: date) -> str:
    """Kurzform für Listen: Zimmer-Kennung heute (nach Umzügen) – ``lage``: ``stand.lage``."""
    if not zimmer:
        return zimmer
    return ort(zimmer, person, name, von, bis, (getattr(lage, "umzuege", None) or {}).values(), heute).zimmer
