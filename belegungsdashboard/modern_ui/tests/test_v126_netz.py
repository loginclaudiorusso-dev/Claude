"""1.26 – Schreibsperre: lebende Sperre nie löschen, Fencing beim Speichern. Simulierte Sperrdateien."""

import json
import os

import pytest

from modern import netz_kern


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    monkeypatch.setattr(netz_kern, "basis", lambda: tmp_path)
    monkeypatch.setattr(netz_kern, "_puls_starten", lambda p: None)
    return tmp_path


def test_lebende_sperre_wird_nicht_geloescht_wenn_zuruecklegen_scheitert(ordner, monkeypatch):
    p = ordner / netz_kern.SPERRE
    p.write_text(json.dumps({"token": "fremd"}), encoding="utf-8")
    monkeypatch.setattr(netz_kern, "_alter", lambda q: 0.0)                 # frisch = lebend
    echt = os.rename
    monkeypatch.setattr(os, "rename", lambda a, b: (_ for _ in ()).throw(OSError("belegt")))
    assert netz_kern._uebernehmen(p, alt=60) is False
    monkeypatch.setattr(os, "rename", echt)
    reste = [q for q in ordner.iterdir() if q.name.startswith(netz_kern.SPERRE)]
    assert reste and json.loads(reste[0].read_text(encoding="utf-8"))["token"] == "fremd"


def test_verwaiste_sperre_wird_uebernommen(ordner, monkeypatch):
    p = ordner / netz_kern.SPERRE
    p.write_text(json.dumps({"token": "alt"}), encoding="utf-8")
    monkeypatch.setattr(netz_kern, "_alter", lambda q: 999.0)
    assert netz_kern._uebernehmen(p, alt=60) is True
    assert not any(q.name.startswith(netz_kern.SPERRE) for q in ordner.iterdir())


def test_fencing_rollt_zurueck_wenn_sperre_verloren(ordner, monkeypatch):
    from modern import kern

    datei = {"inhalt": "vorher"}
    monkeypatch.setattr(kern.aenderungen, "_dateien", lambda: ["x.json"])
    monkeypatch.setattr(kern.aenderungen, "schnappschuss", lambda namen: {n: datei["inhalt"] for n in namen})
    monkeypatch.setattr(kern.aenderungen, "_roh_schreiben", lambda n, inhalt: datei.update(inhalt=inhalt))
    monkeypatch.setattr(kern.aenderungen, "merken", lambda *a: pytest.fail("darf nicht gemerkt werden"))

    def aktion():
        datei["inhalt"] = "nachher"
        (ordner / netz_kern.SPERRE).write_text(json.dumps({"token": "anderer-pc"}), encoding="utf-8")   # übernommen
    with pytest.raises(netz_kern.Besetzt, match="anderer PC"):
        kern._schritt("Test", aktion)
    assert datei["inhalt"] == "vorher"
    assert json.loads((ordner / netz_kern.SPERRE).read_text(encoding="utf-8"))["token"] == "anderer-pc"   # fremde bleibt


def test_normaler_schritt_speichert(ordner, monkeypatch):
    from modern import kern

    gemerkt = []
    monkeypatch.setattr(kern.aenderungen, "_dateien", lambda: [])
    monkeypatch.setattr(kern.aenderungen, "schnappschuss", lambda namen: {})
    monkeypatch.setattr(kern.aenderungen, "merken", lambda titel, vorher: gemerkt.append(titel))
    assert kern._schritt("Test", lambda: 7) == 7
    assert gemerkt == ["Test"] and not (ordner / netz_kern.SPERRE).exists()
