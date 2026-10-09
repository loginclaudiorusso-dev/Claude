"""Zimmer-Pivot (Rios-Cube): Belegung je Zimmer und Tag (1 = eine Person, 2 = zwei Personen).

Die Pivot kennt keine Namen, dafür jeden Tag – auch gebuchte Zukunft. UWT und Mieter fehlen
darin, die stehen im Gebäudeplan. Für die Zimmerplanung wird sie deshalb als Ergänzung genutzt:
Tage, an denen die Pivot ein Zimmer belegt zeigt, der Gebäudeplan aber nicht, gelten als
„belegt laut Zimmer-Pivot“. So wird z. B. kein Zimmer vorgeschlagen, das im System schon
gebucht ist, aber im (älteren) Gebäudeplan noch frei aussah.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import speicher
from .pivot import PivotProfil, lese_matrix_datei, zelle_zu_datum

DATEI = f"{speicher.IMPORT_ORDNER}/zimmerpivot.json"
_ZIMMER = re.compile(r"^GS-[\d.]+-[A-Z]?\d+$")


@dataclass
class ZimmerPivot:
    datei: str
    stand: date | None
    zeitraum: tuple[date, date]
    # Zimmer-ID -> Liste (von, bis, Personen) zusammenhängender Tage mit gleicher Belegung
    belegung: dict[str, list[tuple[date, date, int]]] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)

    @property
    def zimmer(self) -> int:
        return len(self.belegung)


def parse(matrix: list[list], datei: str = "", stand: date | None = None) -> ZimmerPivot:
    kopf_idx = None
    for i, zeile in enumerate(matrix[:20]):
        if sum(1 for v in zeile if isinstance(v, str) and _ZIMMER.match(v.strip())) >= 3:
            kopf_idx = i
            break
    if kopf_idx is None:
        raise ValueError("Keine Zimmer-Spalten (GS-…-…) gefunden – ist das die Zimmer-Pivot?")
    spalten = {j: v.strip() for j, v in enumerate(matrix[kopf_idx]) if isinstance(v, str) and _ZIMMER.match(v.strip())}
    tage: dict[str, dict[date, int]] = {z: {} for z in spalten.values()}
    erster = letzter = None
    for zeile in matrix[kopf_idx + 1:]:
        if not zeile:
            continue
        tag = zelle_zu_datum(zeile[0])
        if tag is None:
            continue
        erster = tag if erster is None else min(erster, tag)
        letzter = tag if letzter is None else max(letzter, tag)
        for j, zid in spalten.items():
            v = zeile[j] if j < len(zeile) else None
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                tage[zid][tag] = int(v)
    if erster is None:
        raise ValueError("Keine Tageszeilen in der Zimmer-Pivot gefunden.")
    belegung = {}
    for zid, werte in tage.items():
        laeufe = []
        for t in sorted(werte):
            n = werte[t]
            if laeufe and laeufe[-1][1] == t - timedelta(days=1) and laeufe[-1][2] == n:
                laeufe[-1] = (laeufe[-1][0], t, n)
            else:
                laeufe.append((t, t, n))
        if laeufe:
            belegung[zid] = laeufe
    return ZimmerPivot(datei, stand, (erster, letzter), belegung)


def lesen(pfad: Path) -> ZimmerPivot:
    matrix, stand = lese_matrix_datei(Path(pfad), PivotProfil())
    return parse(matrix, Path(pfad).name, stand)


def speichern(zp: ZimmerPivot) -> None:
    speicher.schreiben(DATEI, {
        "datei": zp.datei, "stand": zp.stand.isoformat() if zp.stand else None,
        "von": zp.zeitraum[0].isoformat(), "bis": zp.zeitraum[1].isoformat(),
        "importiert_am": datetime.now().isoformat(timespec="seconds"),
        "belegung": {z: [[a.isoformat(), b.isoformat(), n] for a, b, n in l] for z, l in zp.belegung.items()},
    })


def laden() -> ZimmerPivot | None:
    roh = speicher.lesen(DATEI, None)
    if not roh:
        return None
    return ZimmerPivot(
        roh.get("datei", ""), date.fromisoformat(roh["stand"]) if roh.get("stand") else None,
        (date.fromisoformat(roh["von"]), date.fromisoformat(roh["bis"])),
        {z: [(date.fromisoformat(a), date.fromisoformat(b), int(n)) for a, b, n in l] for z, l in roh["belegung"].items()},
    )


def ergaenzungen(zp: ZimmerPivot, plan_belegt: dict[str, list[tuple[date, date]]],
                 freigaben: dict[str, list[tuple[date, date]]] | None = None) -> dict[str, list[tuple[date, date, int]]]:
    """Belegung laut Pivot, die der Gebäudeplan nicht abdeckt: je Zimmer (von, bis, zusätzliche Personen).
    In Zeiträumen mit Zimmerfreigabe (Gebäudeplan) gilt das Zimmer als frei."""
    ergebnis: dict[str, list[tuple[date, date, int]]] = {}
    for zid, laeufe in zp.belegung.items():
        plan = plan_belegt.get(zid, [])
        frei = (freigaben or {}).get(zid, [])
        extra: dict[date, int] = {}
        for von, bis, n in laeufe:
            t = von
            while t <= bis:
                if any(a <= t <= b for a, b in frei):
                    t += timedelta(days=1)
                    continue
                im_plan = sum(1 for a, b in plan if a <= t <= b)
                if n > im_plan:
                    extra[t] = n - im_plan
                t += timedelta(days=1)
        laeufe_extra = []
        for t in sorted(extra):
            if laeufe_extra and laeufe_extra[-1][1] == t - timedelta(days=1) and laeufe_extra[-1][2] == extra[t]:
                laeufe_extra[-1] = (laeufe_extra[-1][0], t, extra[t])
            else:
                laeufe_extra.append((t, t, extra[t]))
        if laeufe_extra:
            ergebnis[zid] = laeufe_extra
    return ergebnis
