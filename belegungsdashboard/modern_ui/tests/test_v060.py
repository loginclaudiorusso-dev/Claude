"""0.60: Erstellten Mietvertrag bearbeiten (z. B. falsches Zimmer). Erfundene Namen und Beträge."""

from datetime import date

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


def _werte(mv, **neu):
    w = {"anrede": mv.anrede, "vorname": mv.vorname, "nachname": mv.nachname, "zimmer": mv.zimmer, "von": mv.von,
         "bis": mv.bis, "miete": mv.miete, "flaeche": mv.flaeche, "schluessel": mv.schluessel, "kaution": mv.kaution,
         "kaution_bis": mv.kaution_bis, "email": mv.email}
    w.update(neu)
    return w


def _vertrag(goslar):
    from belegung import mieter as mt
    from modern import mieter_kern as mk

    zimmer = list(mk.zimmer_auswahl(date(2027, 3, 1), date(2027, 8, 31), "Frau"))
    assert len(zimmer) >= 3
    mv = mt.Mietvertrag("27-001", "Frau", "Erika", "Erfunden", zimmer[0], date(2027, 3, 1), date(2027, 8, 31), 400.0)
    mt.anlegen(mv)
    return mv, zimmer


def test_zimmer_korrigieren_zimmerplan_zieht_mit(goslar):
    from belegung import mieter as mt
    from belegung import protokoll
    from belegung import zimmerplan as zp
    from modern import mieter_kern as mk

    mv, zimmer = _vertrag(goslar)
    text, pfad = mk.vertrag_aendern("27-001", _werte(mv, zimmer=zimmer[1]), unterlagen=False)
    assert "Zimmer" in text and pfad is None
    neu = mt.nach_nummer("27-001")
    assert neu.zimmer == zimmer[1] and neu.nr == "27-001" and len(mt.laden()) == 1
    zw = [z for z in zp.zuweisungen_laden() if z["person"] == "mv:27-001"]
    assert len(zw) == 1 and zw[0]["zimmer"] == zimmer[1]
    eintraege = [e for e in protokoll.laden() if e.get("aktion") == "Mietvertrag geändert"]
    assert len(eintraege) == 1 and eintraege[0]["alt"] == zimmer[0].removeprefix("GS-")
    assert eintraege[0]["neu"] == zimmer[1].removeprefix("GS-") and "Zimmer" in eintraege[0]["quelle"]


def test_mehrere_angaben_und_rueckgaengig(goslar):
    from belegung import mieter as mt
    from modern import kern
    from modern import mieter_kern as mk

    mv, zimmer = _vertrag(goslar)
    text, _ = mk.vertrag_aendern("27-001", _werte(mv, nachname="Erfunden-Neu", miete=420, bis=date(2027, 9, 30)),
                                 unterlagen=False)
    assert "Nachname" in text and "Miete" in text and "Mietende" in text
    assert mt.nach_nummer("27-001").bis == date(2027, 9, 30)
    ok, _m = kern.rueckgaengig()
    assert ok and mt.nach_nummer("27-001").nachname == "Erfunden" and mt.nach_nummer("27-001").miete == 400


def test_belegtes_zimmer_wird_abgelehnt(goslar):
    from belegung import mieter as mt
    from modern import mieter_kern as mk

    mv, zimmer = _vertrag(goslar)
    mt.anlegen(mt.Mietvertrag("27-002", "Herr", "Max", "Erfunden", zimmer[2], date(2027, 3, 1), date(2027, 8, 31), 400.0))
    with pytest.raises(ValueError, match="Zimmer"):
        mk.vertrag_aendern("27-001", _werte(mv, zimmer=zimmer[2]), unterlagen=False)
    assert mt.nach_nummer("27-001").zimmer == zimmer[0]
    # das eigene Zimmer blockiert sich nicht selbst (nur Zeitraum geändert)
    mk.vertrag_aendern("27-001", _werte(mv, bis=date(2027, 7, 31)), unterlagen=False)
    assert mv.zimmer in mk.zimmer_auswahl(date(2027, 3, 1), date(2027, 7, 31), "Frau", person="mv:27-001")


def test_ohne_aenderung_und_fehler(goslar):
    from modern import mieter_kern as mk

    mv, _ = _vertrag(goslar)
    with pytest.raises(ValueError, match="nichts geändert"):
        mk.vertrag_aendern("27-001", _werte(mv), unterlagen=False)
    with pytest.raises(ValueError, match="Ende"):
        mk.vertrag_aendern("27-001", _werte(mv, bis=date(2027, 2, 1)), unterlagen=False)
    with pytest.raises(ValueError, match="gibt es nicht"):
        mk.vertrag_aendern("27-999", _werte(mv), unterlagen=False)
