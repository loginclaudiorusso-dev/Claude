"""1.37 – Persönliche Einstellungen je Person (angemeldet) statt je PC; ohne Anmeldung wie bisher je PC."""

import json

import pytest

from modern import benutzer_kern as bk
from modern import netz_kern


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    monkeypatch.setenv(netz_kern.LOKAL_ENV, str(tmp_path / "lokal"))
    (tmp_path / "daten").mkdir()
    standort_kern.waehlen("GS", merken_=False)
    bk.abmelden()
    yield tmp_path
    bk.abmelden()


def test_ohne_anmeldung_je_pc(ordner):
    netz_kern.persoenlich_setzen("design", {"helligkeit": "dunkel"}, je_standort=False)
    assert netz_kern.lokal_lesen()["design"] == {"helligkeit": "dunkel"}
    assert not (ordner / "daten" / "importe" / "personen").exists()


def test_mit_anmeldung_reist_es_mit_und_faellt_auf_den_pc_zurueck(ordner):
    netz_kern.persoenlich_setzen("design", {"helligkeit": "dunkel"}, je_standort=False)     # alter PC-Wert
    bk.setzen(bk.Konto("m.muster", "Mia", "mitarbeiter", ["GS"]))
    assert netz_kern.persoenlich("design", None, je_standort=False) == {"helligkeit": "dunkel"}   # Übergang
    netz_kern.persoenlich_setzen("design", {"helligkeit": "hell"}, je_standort=False)
    datei = ordner / "daten" / "importe" / "personen" / "m.muster.json"
    assert json.loads(datei.read_text(encoding="utf-8"))["design"] == {"helligkeit": "hell"}
    assert netz_kern.lokal_lesen()["design"] == {"helligkeit": "dunkel"}                  # PC-Wert unberührt
    netz_kern.persoenlich_setzen("qr_gemeldet", ["x"])                                     # gehört zum PC
    assert "GS:qr_gemeldet" in netz_kern.lokal_lesen()
    bk.setzen(bk.Konto("b.beispiel", "Bo", "mitarbeiter", ["GS"]))
    assert netz_kern.persoenlich("design", None, je_standort=False) == {"helligkeit": "dunkel"}   # andere Person


def test_standort_je_person(ordner):
    from modern import standort_kern

    bk.setzen(bk.Konto("m.muster", "Mia", "mitarbeiter", ["GS", "BP"]))
    standort_kern.merken("BP")
    assert standort_kern.gemerkt() == "BP"
    bk.setzen(bk.Konto("b.beispiel", "Bo", "mitarbeiter", ["GS"]))
    assert standort_kern.gemerkt() == "GS"


def test_unsichere_kennung_wird_nicht_als_dateiname_benutzt():
    assert netz_kern.name_unsicher("a/b") and netz_kern.name_unsicher(".x") and not netz_kern.name_unsicher("m.muster")
