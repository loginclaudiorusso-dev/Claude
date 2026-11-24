"""1.56: Freie Zimmer in den nächsten Monaten (Belegungsplan → „Frei“).

Je Zimmer und Woche: wie viele Bett-Nächte sind frei? Daraus eine Heatmap wie bei den Fluren:

* **frei** – die ganze Woche alle Betten frei
* **teil** – teilweise frei (einige Tage oder ein Bett im Doppelzimmer)
* **voll** – kein Bett frei
* **sperr** – gesperrt (Renovierung, Mangel „nicht bewohnbar“ …); EMR-Reservierungen zählen als belegt, nicht gesperrt

Dazu je Zimmer: ab wann es frei wird und wie lange am Stück („frei ab 03.02., 9 Wochen“) – zum schnellen Finden eines
Zimmers für eine lange Maßnahme. Rein, ohne NiceGUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import zimmerplan as zp

MONATE = {3: 13, 6: 26, 12: 52}         # Monate → Wochen
MINDEST = 7                              # Tage am Stück, ab denen ein Zimmer als „frei“ zählt
STUFE = {"frei": "ganz frei", "teil": "teilweise frei", "voll": "belegt", "sperr": "gesperrt"}


@dataclass
class FZelle:
    woche: date            # Montag
    frei: int              # freie Bett-Nächte
    moeglich: int          # Betten × 7
    stufe: str             # frei | teil | voll | sperr

    @property
    def anteil(self) -> float:
        return self.frei / self.moeglich if self.moeglich else 0.0


@dataclass
class FZeile:
    zimmer: str
    kurz: str
    haus: str
    flur: str              # „1. OG West“
    betten: int
    zellen: list[FZelle] = field(default_factory=list)
    frei_ab: date | None = None        # erster Tag, an dem mindestens ein Bett frei ist
    frei_tage: int = 0                 # so viele Tage am Stück ab ``frei_ab`` (mindestens ein Bett frei)
    ganz_frei_ab: date | None = None   # erster Tag, an dem das ganze Zimmer frei ist
    ganz_frei_tage: int = 0
    strecken: list = field(default_factory=list)   # alle Strecken, in denen das ganze Zimmer frei ist (Beginn, Tage)

    @property
    def frei_anteil(self) -> float:
        m = sum(z.moeglich for z in self.zellen)
        return sum(z.frei for z in self.zellen) / m if m else 0.0

    @property
    def text(self) -> str:
        if self.ganz_frei_ab is None and self.frei_ab is None:
            return "im Zeitraum nicht frei"
        if self.ganz_frei_ab is not None:
            return f"ganz frei ab {self.ganz_frei_ab:%d.%m.}, {dauer(self.ganz_frei_tage)}"
        return f"1 Bett frei ab {self.frei_ab:%d.%m.}, {dauer(self.frei_tage)}"


def dauer(tage: int) -> str:
    if tage >= 14:
        return f"{tage // 7} Wochen"
    return f"{tage} Tag{'e' if tage != 1 else ''}"


def _tag(lage, zid: str, tag: date, betten: int) -> tuple[int, bool]:
    """(freie Betten, gesperrt?) an einem Tag."""
    from .zimmer_kern import status_anzeige

    st, bs, _emr = status_anzeige(lage, zid, tag)
    if st == "gesperrt":
        return 0, True
    personen = sum(1 for b in bs if b.art in ("belegt", "geplant"))
    return max(0, betten - personen), False


def _strecken(tage: list[tuple[date, bool]]) -> list[tuple[date, int]]:
    """Zusammenhängende Strecken (Beginn, Länge in Tagen), an denen die Bedingung gilt."""
    erg: list[tuple[date, int]] = []
    for tag, ja in tage:
        if not ja:
            continue
        if erg and erg[-1][0] + timedelta(days=erg[-1][1]) == tag:
            erg[-1] = (erg[-1][0], erg[-1][1] + 1)
        else:
            erg.append((tag, 1))
    return erg


def _erste(strecken: list[tuple[date, int]], mindest: int) -> tuple[date | None, int]:
    """Erste Strecke mit mindestens ``mindest`` Tagen (bis zum Ende des Zeitraums gilt auch kürzer, wenn sie dort
    erst beginnt – sie geht vermutlich weiter)."""
    for von, n in strecken:
        if n >= mindest:
            return von, n
    return None, 0


def raster(stand, start: date, wochen: int = 26, haus: str = "", unbewohnbar: set[str] | None = None,
           ab: date | None = None, mindest: int = MINDEST) -> list[FZeile]:
    """Je aktivem Zimmer (ohne Gästezimmer) die Wochen ab ``start`` (auf Montag gerundet). „frei ab“ zählt ab ``ab``
    (Standard: ``start``, sinnvoll: heute) und nur Strecken ab ``mindest`` Tagen – kurze Lücken sind kein freies Zimmer."""
    start -= timedelta(days=start.weekday())
    ab = max(ab or start, start)
    unbew = unbewohnbar or set()
    erg = []
    for z in stand.zimmer:
        if not z.aktiv or getattr(z, "gaeste", False) or (haus and z.haus != haus):
            continue
        zeile = FZeile(z.id, z.kurz, z.haus, zp.flur_text(z).split(" · ", 1)[-1] + (f" {z.flur}" if z.flur else ""),
                       z.betten)
        bett, ganz = [], []
        for w in range(wochen):
            mo = start + timedelta(days=7 * w)
            frei = gesperrt = 0
            for d in range(7):
                tag = mo + timedelta(days=d)
                n, sp = (0, True) if z.id in unbew else _tag(stand.lage, z.id, tag, z.betten)
                frei += n
                gesperrt += sp
                if tag >= ab:
                    bett.append((tag, n > 0))
                    ganz.append((tag, n >= z.betten))
            moeglich = 7 * z.betten
            stufe = "sperr" if gesperrt == 7 else "frei" if frei == moeglich else "teil" if frei else "voll"
            zeile.zellen.append(FZelle(mo, frei, moeglich, stufe))
        zeile.strecken = _strecken(ganz)
        zeile.ganz_frei_ab, zeile.ganz_frei_tage = _erste(zeile.strecken, mindest)
        zeile.frei_ab, zeile.frei_tage = _erste(_strecken(bett), mindest)
        erg.append(zeile)
    erg.sort(key=lambda r: (zp._haus_sort(r.haus), r.kurz))
    return erg


SORTIERUNG = {"zimmer": "nach Zimmer", "frueh": "früh frei zuerst", "lang": "lange frei zuerst"}


def sortieren(zeilen: list[FZeile], art: str) -> list[FZeile]:
    if art == "frueh":
        return sorted(zeilen, key=lambda r: (r.ganz_frei_ab or r.frei_ab or date.max, -r.ganz_frei_tage, r.kurz))
    if art == "lang":
        return sorted(zeilen, key=lambda r: (-r.ganz_frei_tage, -r.frei_tage, r.kurz))
    return zeilen


def filtern(zeilen: list[FZeile], nur_frei: bool, mindestens_wochen: int = 0) -> list[FZeile]:
    """``nur_frei``: Zimmer ohne freie Zeit weglassen; ``mindestens_wochen``: nur Zimmer, die so lange am Stück ganz
    frei sind (z. B. 8 Wochen für eine Maßnahme)."""
    erg = [r for r in zeilen if not nur_frei or r.frei_ab is not None]
    if mindestens_wochen:
        erg = [r for r in erg if any(n >= 7 * mindestens_wochen for _v, n in r.strecken)]
    return erg


def zusammenfassung(zeilen: list[FZeile]) -> dict[str, int]:
    """Wie viele Zimmer sind diese Woche ganz frei, im Zeitraum irgendwann frei, gar nicht frei?"""
    return {"jetzt": sum(1 for r in zeilen if r.zellen and r.zellen[0].stufe == "frei"),
            "spaeter": sum(1 for r in zeilen if r.frei_ab is not None),
            "nie": sum(1 for r in zeilen if r.frei_ab is None)}
