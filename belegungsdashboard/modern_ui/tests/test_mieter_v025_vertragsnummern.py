"""0.25: Vertragsnummern der Mieter mit bisherigen Verträgen abgleichen – erfundene Daten."""

from datetime import date

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


HEUTE = date(2026, 10, 28)


def test_ohne_bisherige_vertraege_ab_001(leer):
    from modern import mieter_kern as mk

    assert mk.nummern_abgleich(HEUTE)[0] == "26-001"


def test_ordner_mit_bisherigen_vertraegen(leer):
    from modern import mieter_kern as mk

    alt = leer / "Mietverträge"
    (alt / "2026").mkdir(parents=True)
    for name in ("MV 26.003 Muster.pdf", "Mietvertrag_26-017_Beispiel.docx", "2026/MV26-041 Probe.pdf",
                 "MV 25-099 Vorjahr.pdf", "Liste 15.10.2026.xlsx"):
        (alt / name).write_bytes(b"x")
    mk.abgleich_einstellen(str(alt), "")
    nr, woher = mk.nummern_abgleich(HEUTE)
    assert nr == "26-042" and "MV26-041 Probe.pdf" in woher                      # Vorjahr und Datum zählen nicht
    assert mk.vergeben("26-017", HEUTE) and mk.vergeben("26.003", HEUTE) and not mk.vergeben("26-042", HEUTE)


def test_letzte_nummer_von_hand(leer):
    from modern import mieter_kern as mk

    assert mk.abgleich_einstellen("", "26.047").startswith("Nächste Vertragsnummer")
    assert mk.nummern_abgleich(HEUTE) == ("26-048", "zuletzt 26-047 (von Hand festgelegt)")
    assert mk.vergeben("26-012", HEUTE) and not mk.vergeben("26-048", HEUTE)
    with pytest.raises(ValueError):
        mk.abgleich_einstellen("", "47")
    with pytest.raises(ValueError):
        mk.abgleich_einstellen(str(leer / "gibt_es_nicht"), "")


def test_doppelte_nummer_wird_nicht_erstellt(leer):
    from modern import mieter_kern as mk

    mk.abgleich_einstellen("", "26-047")
    werte = {"nr": "26-030", "anrede": "Frau", "vorname": "Erna", "nachname": "Erfunden", "zimmer": "GS-6-1005",
             "von": HEUTE, "bis": date(2027, 4, 27), "miete": 450, "flaeche": 11, "schluessel": 1, "kaution": False,
             "kaution_bis": HEUTE}
    with pytest.raises(ValueError, match="26-030 ist schon vergeben.*nächste freie: 26-048"):
        mk.neuer_vertrag(werte)
