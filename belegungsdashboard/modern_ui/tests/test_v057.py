"""0.57: 80-%- und 95-%-Spanne der Neuanmeldungen (aus dem Rückwärtstest). Nur erfundene Zahlen."""

from __future__ import annotations

from datetime import date

import pytest

from modern import massnahmen_kern as mk


def test_spanne_80_und_95():
    rel = [i / 10 for i in range(-20, 21)]                   # 41 Abweichungen von −2 bis +2 (Wurzel-Einheiten)
    lo, hi, lo95, hi95 = mk._spanne(rel)
    k = 1 + 2 / 41                                            # leichte Weitung für die Stichprobengröße
    assert lo == pytest.approx(-1.6 * k) and hi == pytest.approx(1.6 * k)
    assert lo95 == pytest.approx(-1.9 * k) and hi95 == pytest.approx(1.9 * k)
    assert lo95 <= lo < 0 < hi <= hi95


def test_spanne_wenige_fehler_hochgerechnet():
    lo, hi, lo95, hi95 = mk._spanne([-1, -.5, 0, .5, 1, .8])
    assert lo95 == pytest.approx(lo * 1.96 / 1.2816) and hi95 == pytest.approx(hi * 1.96 / 1.2816)
    lo, hi, lo95, hi95 = mk._spanne([])                       # ohne Test: wie Zufallsschwankung (Poisson)
    assert hi == pytest.approx(1.2816 * 1.4) and hi95 > hi


def test_band_waechst_mit_der_wurzel():
    # gleiche Abweichung in Wurzel-Einheiten: bei 16 sind es ±4, bei 4 nur ±2 – nicht dieselben Prozent
    assert mk.band(16, 1) - 16 == pytest.approx(4) and mk.band(4, 1) - 4 == pytest.approx(2)
    assert mk.band(3, -5) == 0                                # nie unter 0


def test_summenspanne_schmaler_als_summe_der_spannen():
    zs = [mk.HZeile((2027, 1), "prognose", 0, 0, 10, 8, 12, False, 6, 14),
          mk.HZeile((2027, 2), "prognose", 0, 0, 10, 8, 12, False, 6, 14)]
    u, o = mk.summen_spanne(zs, 80)
    assert 16 < u < 20 and 20 < o < 24                       # nicht 16–24
    u95, o95 = mk.summen_spanne(zs, 95)
    assert u95 < u and o95 > o
    zs[0].ist = 9                                            # schon Begonnene sind die Untergrenze
    assert mk.summen_spanne([zs[0]], 95)[0] >= 9


def _roh(starts: dict) -> dict:
    kurse = {f"GS VW {j % 100}{m:02d}": (date(j, m, 2), [n] * 730) for (j, m), n in starts.items()}
    return {"pivot": {"von": "2019-01-01", "bis": "2027-12-31",
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}}}


def test_neuanmeldungen_mit_beiden_spannen():
    import random

    random.seed(3)
    roh = _roh({(j, m): 12 + random.randint(-3, 3) for j in range(2019, 2026) for m in (1, 6)})
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 4, 4)["GS VW"]
    for z in r.zeilen:
        if z.art == "ist":
            assert z.klein == z.gross == z.klein95 == z.gross95 == z.erwartet
        else:
            assert z.klein95 <= z.klein <= z.erwartet <= z.gross <= z.gross95
            assert z.klein95 >= 0
    u, o = r.jahr_spanne(2026, 95)
    assert u < r.naechstes_jahr < o
