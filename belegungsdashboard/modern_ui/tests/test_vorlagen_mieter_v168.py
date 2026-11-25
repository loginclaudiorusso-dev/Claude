"""1.68: Vorlagen für Mietverträge einrichten (Ordner fehlte ganz) – nur der Vertragstext ist Pflicht."""

from datetime import date

import pytest

import modern.kern  # noqa: F401 – Einhängepunkte
from belegung import mieter as mt

from modern import vorlagen_mieter as vm


@pytest.fixture
def orte(monkeypatch, tmp_path):
    standort, gemeinsam, programm = tmp_path / "Standort", tmp_path / "Daten", tmp_path / "Programm"
    for p in (standort, gemeinsam, programm):
        p.mkdir()
    monkeypatch.setattr(vm, "_orte", lambda: [("Standort", standort), ("gemeinsam", gemeinsam), ("Programm", programm)])
    from belegung import protokoll

    monkeypatch.setattr(protokoll, "eintragen", lambda *a, **k: None)
    return standort, gemeinsam, programm


def test_ohne_ordner_fehlt_nur_der_vertrag(orte):
    assert vm.ordner_suchen() is None and vm.vertrag_fehlt()
    assert mt.fehlende_vorlagen() == [mt.VERTRAG]                       # eingehängt: nur Pflicht
    assert [s.datei for s in vm.status() if s.pflicht] == [mt.VERTRAG]


def test_muster_anlegen_im_gemeinsamen_ordner_und_nie_ueberschreiben(orte):
    _, gemeinsam, _ = orte
    vm.muster_anlegen()
    assert (gemeinsam / mt.VORLAGEN_ORDNER / mt.VERTRAG).is_file()
    assert not vm.vertrag_fehlt() and vm.ist_muster() and mt.fehlende_vorlagen() == []
    assert mt.vorlagen_ordner() == gemeinsam / mt.VORLAGEN_ORDNER
    with pytest.raises(ValueError):
        vm.muster_anlegen()


def test_muster_ergibt_vertrag_ohne_offene_platzhalter(orte):
    mv = mt.Mietvertrag("26-001", "Frau", "Erika", "Beispiel", "GS-6-301", date(2027, 1, 1), date(2027, 6, 30), 400.0,
                        11, 2, None, kaution=False)
    for kaution in (False, True):
        mv.kaution = kaution
        html = mt.vertrag_html(mv, vm.MUSTER)
        assert "{" not in html and "Beispiel" in html and "Mieterin" in html and "MUSTER" in html
        assert ("Mietsicherheit wird nicht vereinbart" in html) != kaution


def test_standort_vorrang_und_eigene_datei_ersetzt_mit_kopie(orte):
    standort, gemeinsam, _ = orte
    vm.einrichten(mt.VERTRAG, "=Mietvertrag {nr}\n1. Zimmer {zimmer_kurz}\n".encode("cp1252"))
    vm.einrichten(mt.VERTRAG, "=Vertrag {nr} – neu\n".encode())
    o = gemeinsam / mt.VORLAGEN_ORDNER
    assert (o / mt.VERTRAG).read_text(encoding="utf-8").startswith("=Vertrag")
    assert len(list(o.glob("Mietvertrag.vorlage.bis-*"))) == 1                # alte Fassung bleibt erhalten
    (standort / mt.VORLAGEN_ORDNER).mkdir(parents=True)
    (standort / mt.VORLAGEN_ORDNER / mt.VERTRAG).write_text("=Eigener Standort {nr}", encoding="utf-8")
    assert vm.ordner_suchen() == standort / mt.VORLAGEN_ORDNER


def test_falsche_dateien_abgelehnt(orte):
    with pytest.raises(ValueError):
        vm.einrichten(mt.VERTRAG, b"kein Platzhalter")
    with pytest.raises(ValueError):
        vm.einrichten(mt.SEPA, b"<html>")
    with pytest.raises(ValueError):
        vm.einrichten("boese.exe", b"MZ")
    vm.einrichten(mt.SEPA, b"%PDF-1.4 ...")
    assert vm.fehlende_optional() == ["Wohnungsgeberbestätigung", "Mietschuldenfreiheitsbescheinigung"]
