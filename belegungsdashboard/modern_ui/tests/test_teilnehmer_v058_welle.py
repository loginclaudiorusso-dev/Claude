"""0.58: Rückwärtstest je Welle mit damaliger Spanne (Treffer im 80-/95-%-Band), UWT ausgeblendet. Erfundene Zahlen."""

from __future__ import annotations

import random
from datetime import date

from modern import massnahmen_kern as mk


def _roh(fams: dict[str, int], jahre=range(2015, 2026)) -> dict:
    random.seed(7)
    kurse = {}
    for fam, n in fams.items():
        for j in jahre:
            for m in (1, 6):
                kurse[f"{fam} {j % 100}{m:02d}"] = (date(j, m, 3), [max(1, n + random.randint(-4, 4))] * 700)
    return {"pivot": {"von": "2014-01-01", "bis": "2027-12-31",
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}}}


def test_rueckwaertstest_je_welle_und_treffer():
    roh = _roh({"GS VW": 15, "GS FISY": 12, "GS KBM": 18})
    tests = mk.verfahren_testen(roh)
    t = next(t for t in tests if t.verfahren == "mittel3")
    k80, n80 = t.treffer80
    k95, n95 = t.treffer95
    assert n80 == n95 > 20 and k95 >= k80
    assert .5 <= k80 / n80 <= 1 and k95 / n95 >= .8                    # Spannen sind nicht völlig falsch kalibriert
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 8, 2, "mittel3", tests=tests)["GS VW"]
    ist = [z for z in r.zeilen if z.art == "ist"]
    assert all(z.rueck is not None for z in ist)
    mit_band = [z for z in ist if z.rueck_band]
    assert mit_band and all(b[2] <= b[0] <= z.rueck <= b[1] <= b[3] for z in mit_band for b in [z.rueck_band])
    assert all(z.im80 in (True, False) and (z.im95 or not z.im80) for z in mit_band)
    assert all(z.rueck is None and z.rueck_band is None for z in r.zeilen if z.art != "ist")


def test_rueckwaertstest_ohne_vorwissen():
    roh = _roh({"GS VW": 15})
    r1 = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 8, 2, "vorjahr")["GS VW"]
    z = next(z for z in r1.zeilen if z.hj == (2024, 2))
    vorjahr = next(x for x in r1.zeilen if x.hj == (2023, 2))
    assert z.rueck == vorjahr.ist                                       # „wie Vorjahr“ – nur die Welle davor


def test_uwt_ausgeblendet():
    roh = _roh({"GS VW": 15, "GS UWT": 40}, range(2022, 2026))
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), None, 4, 2)
    assert r["GS UWT"].ausgeschlossen and not r["GS UWT"].aktiv and r["GS UWT"].grund.startswith("UWT")
    assert r["GS VW"].aktiv and r["GS VW"].grund == ""
