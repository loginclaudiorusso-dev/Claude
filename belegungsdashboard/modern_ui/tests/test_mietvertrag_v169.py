"""1.69: Mietverträge – Nummer automatisch (unter Sperre), Anschrift vor Einzug, Vordrucke auswählbar (erfundene Daten)."""

from datetime import date
from types import SimpleNamespace as NS

import pytest

import modern.kern  # noqa: F401 – Einhängepunkte
from belegung import mieter as mt

from modern import mieter_kern as mk

MV = NS(vorname="Erika", nachname="Beispiel")


def test_name_und_anschrift():
    t = "{name_anschrift} | {anschrift} | {nr}"
    assert mk.text_vorbereiten(t, MV, "Musterweg 1, 12345 Probehausen") == \
        "Erika Beispiel, Musterweg 1, 12345 Probehausen | Musterweg 1, 12345 Probehausen | {nr}"
    assert mk.text_vorbereiten(t, MV, "") == "Erika Beispiel |  | {nr}"          # ohne Anschrift kein Komma


def test_nur_ausgewaehlte_vordrucke(monkeypatch, tmp_path):
    for d in mk.DOKUMENTE:
        (tmp_path / d).write_bytes(b"%PDF")
    gesehen = {}
    monkeypatch.setattr(mt, "paket_erstellen",
                        lambda mv, pdf, ziel, ordner: gesehen.setdefault("d", sorted(p.name for p in ordner.iterdir())))
    mk._paket(None, None, tmp_path / "x.pdf", tmp_path, [mt.WOHNUNGSGEBER, mt.SEPA])
    assert gesehen["d"] == sorted([mt.WOHNUNGSGEBER, mt.SEPA])                 # Mietschuldenfreiheit nicht dabei


def test_standardauswahl_ohne_mietschulden(monkeypatch):
    from belegung import speicher

    monkeypatch.setattr(speicher, "einstellungen", lambda: {})
    assert mt.MIETSCHULDEN not in mk.dokumente_standard()
    monkeypatch.setattr(speicher, "einstellungen", lambda: {mk.DOKU_EINSTELLUNG: [mt.MIETSCHULDEN, "boese.pdf"]})
    assert mk.dokumente_standard() == [mt.MIETSCHULDEN]


def test_nummer_automatisch_trotz_eingabe(monkeypatch):
    monkeypatch.setattr(mk, "nummer_vorschlag", lambda von, heute=None: ("26-042", ""))
    gesehen = {}

    def pruefen(mv):
        gesehen["nr"] = mv.nr
        return ["Halt (Test)"]
    monkeypatch.setattr(mt, "pruefen", pruefen)
    werte = {"nr": "26-001", "nr_auto": True, "anrede": "Frau", "vorname": "Erika", "nachname": "Beispiel",
             "zimmer": "", "von": date(2026, 12, 1), "bis": date(2027, 5, 31), "miete": 400, "flaeche": 11,
             "schluessel": 1, "kaution": False, "kaution_bis": None}
    with pytest.raises(ValueError):
        mk._neuer_vertrag(werte)
    assert gesehen["nr"] == "26-042"
    with pytest.raises(ValueError):
        mk._neuer_vertrag({**werte, "nr_auto": False})                     # von Hand: die eingegebene Nummer
    assert gesehen["nr"] == "26-001"


def test_neuer_vertrag_unter_sperre(monkeypatch):
    from modern import netz_kern

    import contextlib
    aufrufe = []

    @contextlib.contextmanager
    def sperre(*a, **k):
        aufrufe.append("sperre")
        yield
    monkeypatch.setattr(netz_kern, "sperre", sperre)
    monkeypatch.setattr(mk, "_neuer_vertrag", lambda w: ("ok", None))
    assert mk.neuer_vertrag({}) == ("ok", None) and aufrufe == ["sperre"]
