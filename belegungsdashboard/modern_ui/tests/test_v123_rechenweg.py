"""1.23 – Rechenweg der Prognose: dieselben Zahlen wie das Hauptprogramm, mit Statistik. Erfundener Pivot."""

import importlib.util
import inspect
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


def _zahl(t: str) -> float:
    return float(t.replace(".", "").replace(",", ".").replace("−", "-"))


def test_standort_schritte_und_werte(ds):
    from belegung import konfig
    from modern import rechenweg_kern as rk

    st = konfig.STANDORTE[0]
    w = [x for x in ds.prognose.werte[st] if x.art == "prognose"][2]
    sch = rk.rechenweg(ds, st, w.monat)
    titel = [s.titel for s in sch]
    assert titel[:2] == ["Datenbasis", "Modellwahl im Rückwärtstest"]
    assert "Unsicherheit (Band) aus den eigenen Fehlern" in titel and titel[-1] == "Ergebnis"
    band = next(s for s in sch if s.titel.startswith("Unsicherheit"))
    assert "Standardabweichung" in " ".join(band.details) and "k80" in band.rechnung
    halb = _zahl(band.rechnung.split("= ±")[1].split(" ")[0])
    assert abs(halb - (w.hi80 - w.erwartet)) < 0.06                  # gleiche Halbbreite wie im Hauptprogramm
    unter = next(s for s in sch if s.titel.startswith("Gebuchter"))
    assert unter.rechnung.endswith(rk._z(w.erwartet))


def test_gesamt_mit_korrelation(ds):
    from belegung import konfig
    from modern import rechenweg_kern as rk

    w = [x for x in ds.prognose.werte[konfig.GESAMT] if x.art == "prognose"][1]
    sch = rk.rechenweg(ds, konfig.GESAMT, w.monat)
    text = " ".join(s.rechnung + " ".join(s.details) for s in sch)
    assert "Kovarianz" in text and "Korrelation r" in text and "unabhängig" in text
    assert sch[0].rechnung.endswith(rk._z(w.erwartet))


def test_ist_monat_hat_keinen_rechenweg(ds):
    from belegung import konfig
    from modern import rechenweg_kern as rk

    w = next(x for x in ds.prognose.werte[konfig.STANDORTE[0]] if x.art == "ist")
    assert rk.rechenweg(ds, konfig.STANDORTE[0], w.monat) == []


def test_eingebunden():
    from modern import diagramm_karte, diagramm_ui, seite_prognose

    assert '"rechenweg"' in inspect.getsource(seite_prognose._berechnung_monat)
    assert "rechenweg_block" in inspect.getsource(diagramm_ui.fx_kasten)
    assert "rechenweg_block" in inspect.getsource(diagramm_karte.Karte._stelle)
