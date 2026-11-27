"""1.76: Berechnung für Laien – jeder Schritt mit Überschrift und Erklärung in Alltagssprache (echte Zahlen), Formeln
als Gleichung gesetzt. Erfundener Pivot (wie test_prognose_v123_rechenweg)."""

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

HIER = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ds():
    spec = importlib.util.spec_from_file_location("conftest_alt", HIER / "tests" / "conftest.py")
    alt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(alt)
    from belegung import laden, pivot

    h = date(2026, 11, 13)
    d = pivot.parse_matrix(alt.pivot_matrix(date(2022, 1, 1), h + timedelta(days=420), h), pivot.PivotProfil())
    d.abrufdatum = h
    vorher = pivot.lese_datei, pivot.lese_excel
    pivot.lese_datei = lambda *a, **k: d
    pivot.lese_excel = lambda *a, **k: (d, False)
    try:
        yield laden.lade(Path("erfunden.xlsx"))
    finally:
        pivot.lese_datei, pivot.lese_excel = vorher


def test_jeder_schritt_hat_alltagssprache(ds):
    from belegung import konfig
    from modern import rechenweg_kern as rk

    for st in (konfig.STANDORTE[0], konfig.GESAMT):
        w = [x for x in ds.prognose.werte[st] if x.art == "prognose"][2]
        sch = rk.rechenweg(ds, st, w.monat)
        assert sch and all(s.kurz and len(s.einfach) > 40 for s in sch), [s.titel for s in sch if not s.einfach]
        erg = sch[-1]
        assert erg.kurz == "Ergebnis" and "8 von 10" in erg.einfach and "rund" in erg.einfach
        fach = ("MAE", "Quantil", "k80", "σ", "Kovarianz")
        assert not any(f in s.einfach for s in sch for f in fach)          # keine Fachbegriffe in der Erklärung


def test_formel_gesetzt():
    from modern.prognose_berechnung_ui import _mathe, _zeilen

    assert _mathe("(φ + φ^H)·b") == '(φ <span class="op">+</span> φ<sup>H</sup>)·b'
    assert "−3,2" in _mathe("x = (−3,2)") and '<span class="op">−</span>' in _mathe("a − b")
    assert _zeilen("a = 1 · b = 2 → 3", pfeil=True) == ["a = 1", "b = 2", "→ 3"]
    assert "<script>" not in _mathe("<script>")
