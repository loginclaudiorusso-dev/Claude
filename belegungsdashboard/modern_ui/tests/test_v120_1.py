"""1.20.1 – Austauschdatei landet im Export-Ordner (im Programmfenster sind Browser-Downloads gesperrt)."""

import inspect
import json

from modern import austausch_dienst as ad


def test_speichern_schreibt_in_exportordner(tmp_path, monkeypatch):
    from belegung import speicher

    monkeypatch.setattr(speicher, "einstellungen", lambda: {"export_ordner": str(tmp_path / "Ex")})
    roh = json.dumps({"a": 1}).encode()
    p = ad.speichern(roh, "INNternat-Austausch_neu_test.json")
    assert p == tmp_path / "Ex" / "INNternat-Austausch_neu_test.json" and p.read_bytes() == roh


def test_oberflaeche_zeigt_pfad_und_ordner():
    from modern import seite_daten

    q = inspect.getsource(seite_daten._austausch_export)
    assert "ad.speichern" in q and "_im_ordner_zeigen" in q and "gespeichert unter" in q
    assert "/select," in inspect.getsource(seite_daten._im_ordner_zeigen)
