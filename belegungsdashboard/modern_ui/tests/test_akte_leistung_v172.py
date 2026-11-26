"""1.72: Mieter-Akte, Ladezeiten-Messung, Pivot-Zwischenspeicher, schnellere „Gleiche Person?“ (erfundene Daten)."""

from datetime import date, timedelta
from types import SimpleNamespace as NS

import pytest

import modern.kern  # noqa: F401 – Einhängepunkte

from modern import mieter_akte as ma


@pytest.fixture
def daten(monkeypatch, tmp_path):
    from belegung import protokoll, speicher

    monkeypatch.setattr(speicher, "pfad", lambda name: tmp_path / name)
    monkeypatch.setattr(protokoll, "eintragen", lambda *a, **k: None)
    return tmp_path


def test_akte_ablegen_umbenennen_papierkorb(daten):
    assert ma.ordner("26-001") is None and ma.dateien("26-001") == []
    ma.ablegen("26-001", "Beispiel", "Übergabe protokoll.pdf", b"%PDF-1")
    ma.ablegen("26-001", "Beispiel", "Übergabe protokoll.pdf", b"%PDF-2")          # gleicher Name → „ (2)“
    namen = sorted(d.name for d in ma.dateien("26-001"))
    assert namen == ["Übergabe protokoll (2).pdf", "Übergabe protokoll.pdf"]
    assert ma.ordner("26-001").name == "MV26-001_Beispiel"
    ma.entfernen("26-001", "Übergabe protokoll.pdf")
    assert [d.name for d in ma.dateien("26-001")] == ["Übergabe protokoll (2).pdf"]
    assert (ma.ordner("26-001") / ma.PAPIERKORB / "Übergabe protokoll.pdf").exists()    # nicht endgültig gelöscht


def test_akte_findet_ordner_ueber_nummer_und_sperrt_gefaehrliches(daten):
    (daten / ma.ORDNER / "MV26-002_Altname").mkdir(parents=True)
    assert ma.ordner("26-002", "Neuname").name == "MV26-002_Altname"
    with pytest.raises(ValueError):
        ma.ablegen("26-002", "Neuname", "boese.exe", b"MZ")
    with pytest.raises(ValueError):
        ma.ablegen("26-002", "Neuname", "../../ausbruch.pdf", b"x" * (ma.MAX_MB * 1_048_576 + 1))
    ma.ablegen("26-002", "Neuname", "../../ausbruch.pdf", b"%PDF")
    assert [d.name for d in ma.dateien("26-002")] == ["ausbruch.pdf"]                   # bleibt in der Akte


def test_kopie_ablegen_ohne_doppelte(daten):
    q = daten / "Mietunterlagen_MV26-003_Beispiel.pdf"
    q.write_bytes(b"%PDF-a")
    ma.kopie_ablegen("26-003", "Beispiel", q)
    ma.kopie_ablegen("26-003", "Beispiel", q)                                           # gleicher Inhalt: keine Kopie
    assert len(ma.dateien("26-003")) == 1
    q.write_bytes(b"%PDF-neu")
    ma.kopie_ablegen("26-003", "Beispiel", q)
    assert len(ma.dateien("26-003")) == 2
    assert ma.kopie_ablegen("26-003", "Beispiel", daten / "gibtsnicht.pdf") is None


def test_ladezeiten_bericht():
    from modern import leistung_messung as lm

    ms = [lm.Messung("01.01. 10:00:00", "Seitendaten", "auswertung", 6.0),
          lm.Messung("01.01. 10:00:01", "Aufbau", "auswertung", 1.0),
          lm.Messung("01.01. 10:00:02", "Daten laden", "heute", 0.2)]
    b = lm.bericht(ms)
    assert b["langsamste"][0].dauer == 6.0 and b["langsam"] == 1
    assert b["je_seite"][0] == ("auswertung", 2, 3.5, 6.0)
    t = lm.text(ms)
    assert "Ladezeiten" in t and "auswertung" in t


def test_ladezeiten_eingehaengt():
    from modern import auswertung_kern, oberflaeche

    assert getattr(oberflaeche.Ansicht._seite_laden, "_gemessen", False)
    assert getattr(auswertung_kern.datenstand, "_gemessen", False)


def test_pivot_zwischenspeicher(monkeypatch, tmp_path):
    from modern import auswertung_kern as ak
    from modern import netz_kern

    monkeypatch.setattr(netz_kern, "lokal_ordner", lambda: tmp_path)
    ak._platte_schreiben(("a", 1), {"wert": 42})
    assert ak._platte_lesen(("a", 1)) == {"wert": 42}
    assert ak._platte_lesen(("a", 2)) is None                                           # Pivot geändert → neu lesen
    (tmp_path / "zwischenspeicher" / "auswertung_datenstand.pkl").write_bytes(b"kaputt")
    assert ak._platte_lesen(("a", 1)) is None


def test_gleiche_person_einmal_je_stand(monkeypatch):
    from belegung.gebaeudeplan import Belegung

    from modern import gleiche_person as gp

    h = date(2026, 11, 26)
    plan = [Belegung("GS-2-105", h - timedelta(days=1), h + timedelta(days=20), "belegt", "Muehlhoff Erika Maria", "EMR")]
    b = NS(schluessel="id:1", name="Mühlhoff, Erika", von=h, bis=h + timedelta(days=4), gruppe="EMR", massnahme="EMR")
    st = NS(plan=NS(belegungen=plan), bedarf=[b], zuweisungen=[])
    monkeypatch.setattr(gp, "laden", lambda: {"verbunden": [], "nein": []})
    zaehler = {"n": 0}
    echt = gp._vorschlaege

    def gezaehlt(*a, **k):
        zaehler["n"] += 1
        return echt(*a, **k)
    monkeypatch.setattr(gp, "_vorschlaege", gezaehlt)
    assert len(gp.vorschlaege(st, h)) == 1 and len(gp.vorschlaege(st, h)) == 1
    assert zaehler["n"] == 1                                                              # zweiter Aufruf aus dem Speicher
