"""1.24 – RVL und RVT getrennt; künftige Zahlen zeigen „angemeldet + erwartet = gesamt“. Erfundene Kurse."""

import inspect
from types import SimpleNamespace as NS

from modern import massnahmen_kern as mk


def test_rvl_und_rvt_eigene_gruppen():
    assert mk.standard_gruppe("GS RVL", 91) == "rvl" and mk.standard_gruppe("GS RVT", 91) == "rvt"
    assert mk.GRUPPEN["rvl"] == "RVL" and mk.GRUPPEN["rvt"] == "RVT" and "vorbereitung" not in mk.GRUPPEN


def test_alte_zuordnung_wird_uebernommen():
    roh = {"gruppen": {"GS RVT": "vorbereitung", "GS RVL": "vorbereitung", "GS XY": "vorbereitung"},
           "pivot": {"kurse": {"GS RVT 2601": {"dauer": 91}, "GS RVL 2601": {"dauer": 91}, "GS XY 2601": {"dauer": 91}}}}
    gr = mk.gruppen(roh)
    assert gr["GS RVT"] == "rvt" and gr["GS RVL"] == "rvl" and gr["GS XY"] == "rvl"


def test_neuanmeldungen_angemeldet_plus_erwartet():
    from modern import seite_massnahmen as sm

    z = NS(art="laufend", ist=3.0, gebucht=5.0)
    assert sm._angemeldet(z) == 8.0
    assert sm._angemeldet(NS(art="prognose", ist=0.0, gebucht=8.0)) == 8.0
    q = inspect.getsource(sm._tooltip) + inspect.getsource(sm._raster)
    assert "angemeldet + erwartet" in q and '"davon angemeldet"' in q


def test_teilnehmer_prognose_tooltip():
    from modern import bestand_prognose_ui as bu

    js = bu._fluss_tooltip(["Okt", "Dez"], [5, None], [None, 20.0], [None, 8.0], [None, 15.0], [None, 10.0], "Zugänge", True)
    assert '"an": 8.0' in js and '"rest": 12.0' in js and "fest angemeldet + " in js
    assert '"davon fest angemeldet"' in inspect.getsource(bu._fluss_ansicht)
