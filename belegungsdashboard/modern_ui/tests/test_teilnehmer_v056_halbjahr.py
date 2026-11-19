"""0.56: Neuanmeldungen je Halbjahr (alle Teilnehmenden), Verfahren per Rückwärtstest, Kleinst-/eingestellte Maßnahmen
ausblenden. Nur erfundene Kurse und Zahlen."""

from __future__ import annotations

from datetime import date

import pytest

from modern import massnahmen_kern as mk


def _roh(kurse: dict, von=date(2021, 1, 1), bis=date(2027, 12, 31)) -> dict:
    return {"pivot": {"von": von.isoformat(), "bis": bis.isoformat(),
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}}}


def _zwei_jahre(n: int, nach: int = 0) -> list[int]:
    return [n + (nach if a >= 14 else 0) for a in range(730)]


def _vw(starts: dict[tuple[int, int], int]) -> dict:
    """Erfundene Hauptmaßnahme „GS VW“: je (Jahr, Monat) ein Kurs mit n Personen."""
    return {f"GS VW {j % 100}{m:02d}": (date(j, m, 2), _zwei_jahre(n)) for (j, m), n in starts.items()}


def test_januar_und_juni_getrennt():
    roh = _roh(_vw({(j, m): 10 + (m == 6) * 5 for j in (2022, 2023, 2024) for m in (1, 6)}))
    r = mk.neuanmeldungen(roh, date(2024, 9, 1), ["GS VW"], 6, 2)["GS VW"]
    zs = {z.hj: z.erwartet for z in r.zeilen}
    assert zs[(2024, 1)] == 10 and zs[(2024, 2)] == 15


def test_neu_im_kurs_zaehlt_nachruecker_nicht_bestand():
    k = mk.Kurs("GS VW 2501", "GS VW", date(2025, 1, 2), _zwei_jahre(10, 3))
    assert mk.neu_im_kurs(k) == 13                    # Nachrücker in den ersten 6 Wochen zählen
    # zwei Jahrgänge gleichzeitig im Bestand – aber je Halbjahr nur die Neuen
    roh = _roh(_vw({(2023, 1): 10, (2024, 1): 12}))
    r = mk.neuanmeldungen(roh, date(2024, 9, 1), ["GS VW"], 6, 2)["GS VW"]
    zs = {z.hj: z for z in r.zeilen}
    assert zs[(2024, 1)].erwartet == 12 and zs[(2023, 1)].erwartet == 10 and zs[(2023, 2)].erwartet == 0


def test_halbjahre():
    # Startwellen: Januar und Juni getrennt; November/Dezember zählen zum Winterstart des Folgejahres
    assert mk.halbjahr(date(2026, 1, 5)) == (2026, 1) and mk.halbjahr(date(2026, 6, 1)) == (2026, 2)
    assert mk.halbjahr(date(2026, 11, 20)) == (2027, 1) and mk.halbjahr(date(2026, 4, 30)) == (2026, 1)
    assert mk.hj_start((2027, 1)) == date(2026, 11, 1) and mk.hj_ende((2027, 1)) == date(2027, 4, 30)
    assert mk.hj_start((2027, 2)) == date(2027, 5, 1) and mk.hj_ende((2027, 2)) == date(2027, 10, 31)
    assert mk.hj_plus((2026, 2), 1) == (2027, 1) and mk.hj_plus((2026, 1), -1) == (2025, 2)
    assert mk.hj_text((2027, 1)) == "Winterstart 2027" and mk.hj_kurz((2027, 2)) == "S 27"
    assert mk._erstes_hj(date(2021, 1, 1)) == (2021, 2)       # Januar-Kurse am Datenbeginn: Start unbekannt


def test_verfahren():
    r = [10, 12, 14, 16]
    assert mk._schaetzen(r, "vorjahr") == 16
    assert mk._schaetzen(r, "mittel3") == 14
    assert 14 < mk._schaetzen(r, "glatt") < 16
    assert mk._schaetzen(r, "trend") > 16                     # Trend setzt sich (gedämpft) fort
    assert mk._schaetzen([10, 5, 0, 0], "trend") >= 0


def test_rueckwaertstest_waehlt_trend_bei_wachstum():
    starts = {(j, m): 6 + 3 * (j - 2021) for j in range(2021, 2027) for m in (1, 7)}
    roh = _roh(_vw(starts), bis=date(2026, 12, 31))
    tests = mk.verfahren_testen(roh)
    assert tests[0].wape <= tests[-1].wape
    assert mk.bestes_verfahren(tests) in ("trend", "vorjahr", "holtwinters", "anteil")   # nie das reine Mittel
    mittel = next(t for t in tests if t.verfahren == "mittel3")
    assert mittel.bias < 0                                    # bei Wachstum zu niedrig


def test_prognose_gebucht_plus_nachbuchung_und_geplant():
    starts = {(j, m): 12 for j in range(2021, 2026) for m in (1, 7)}
    kurse = _vw(starts)
    kurse["GS VW 2601"] = (date(2026, 1, 5), _zwei_jahre(5))          # erst 5 gebucht, Start in 2 Monaten
    roh = _roh(kurse)
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 4, 4, "mittel3")["GS VW"]
    z = next(z for z in r.zeilen if z.hj == (2026, 1))
    assert z.gebucht == 5 and 5 < z.erwartet <= 12 and z.klein >= 5
    z2 = next(z for z in r.zeilen if z.hj == (2026, 2))
    assert z2.erwartet == pytest.approx(12) and z2.gebucht == 0
    assert r.naechstes_jahr == pytest.approx(z.erwartet + z2.erwartet)
    roh["plaetze"] = [{"familie": "GS VW", "monat": "2026-07", "plaetze": 20}]
    r2 = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 4, 4, "mittel3")["GS VW"]
    z3 = next(z for z in r2.zeilen if z.hj == (2026, 2))
    assert z3.erwartet == 20 and z3.geplant


def test_eingestellt_und_kleinstmassnahme():
    kurse = _vw({(j, m): 12 for j in range(2021, 2026) for m in (1, 7)})
    kurse["GS ALT 2201"] = (date(2022, 1, 10), [8] * 300)                 # seit Jahren kein Start
    kurse["GS MINI 2503"] = (date(2025, 3, 10), [1] * 40)                 # winzig
    kurse["GS MINI 2509"] = (date(2025, 9, 10), [2] * 40)
    roh = _roh(kurse)
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), None, 4, 2)
    assert r["GS VW"].aktiv
    assert r["GS ALT"].eingestellt and not r["GS ALT"].aktiv
    assert r["GS MINI"].klein_massnahme and not r["GS MINI"].aktiv


def test_sichtbarkeit_von_hand(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from modern import standort_kern

    standort_kern.waehlen("GS", merken_=False)
    mk.sichtbar_schritt("GS MINI", True)
    mk.sichtbar_schritt("GS VW", False)
    assert mk.sichtbarkeit() == {"GS MINI": True, "GS VW": False}
    mk.sichtbar_schritt("GS VW", None)
    assert mk.sichtbarkeit() == {"GS MINI": True}


def test_trend_kennzahl():
    kurse = _vw({(2023, 1): 10, (2023, 7): 10, (2024, 1): 10, (2024, 7): 10, (2025, 1): 6, (2025, 7): 6})
    r = mk.neuanmeldungen(_roh(kurse), date(2025, 11, 5), ["GS VW"], 4, 2)["GS VW"]
    assert r.letzte12 == 12 and r.vorige12 == 20
    assert r.trend == pytest.approx(-.4)
