"""1.63: Exporte – belegte Datei → freier Name, gesperrter Export-Ordner → persönlicher Ordner, sonst klare Meldung."""

from pathlib import Path

import pytest

from modern import export_ziel as ez


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    gemeinsam, privat = tmp_path / "Export", tmp_path / "privat"
    monkeypatch.setattr(ez, "ordner", lambda unterordner="Export": gemeinsam)
    monkeypatch.setattr(ez, "privat", lambda: privat)
    return gemeinsam, privat


def test_normal(ordner):
    gemeinsam, _ = ordner
    p = ez.speichern("Liste.xlsx", lambda p: p.write_text("x"))
    assert p == gemeinsam / "Liste.xlsx" and p.read_text() == "x"
    assert ez.hinweis(p, "Liste.xlsx") == ""


def test_belegt_freier_name(ordner):
    gemeinsam, _ = ordner

    def schreiben(p: Path):
        if p.name == "Liste.xlsx":                      # bei einer Kollegin in Excel geöffnet
            raise PermissionError(13, "Zugriff verweigert", str(p))
        p.write_text("x")
    p = ez.speichern("Liste.xlsx", schreiben)
    assert p == gemeinsam / "Liste (2).xlsx"
    assert "neuem Namen" in ez.hinweis(p, "Liste.xlsx")


def test_kein_schreibrecht_persoenlicher_ordner(ordner, monkeypatch):
    gemeinsam, privat = ordner

    def schreiben(p: Path):
        if p.parent == gemeinsam:
            raise PermissionError(13, "Zugriff verweigert", str(p))
        p.write_text("x")
    monkeypatch.setattr(ez, "_ordner_beschreibbar", lambda b: b != gemeinsam)
    p = ez.speichern("Liste.xlsx", schreiben)
    assert p == privat / "Liste.xlsx"
    assert "persönlichen Ordner" in ez.hinweis(p, "Liste.xlsx")


def test_alles_gesperrt_klare_meldung(ordner, monkeypatch):
    def schreiben(p: Path):
        raise PermissionError(13, "Zugriff verweigert", str(p))
    monkeypatch.setattr(ez, "_ordner_beschreibbar", lambda b: False)
    with pytest.raises(ez.ExportGesperrt) as e:
        ez.speichern("Liste.xlsx", schreiben)
    assert "Schreibrecht" in str(e.value) and "geöffnet" not in str(e.value)
    assert ez.meldung(e.value) == str(e.value)
    assert "Schreibrecht" in ez.meldung(PermissionError(13, "x", "Z:/Export/a.xlsx"))


def test_kandidaten():
    assert [p.name for p in ez.kandidaten(Path("/x"), "A.xlsx", 3)] == ["A.xlsx", "A (2).xlsx", "A (3).xlsx"]
