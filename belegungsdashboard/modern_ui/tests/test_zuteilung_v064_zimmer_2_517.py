"""0.64: Zimmer 2-517 fest im Programm; Heute entschlackt. Erfundene Daten."""

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


def test_zimmer_2_517_ist_da(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    z = next((x for x in st.zimmer if x.id == "GS-2-517"), None)
    assert z is not None and z.haus == "2" and z.etage == "5" and z.betten == 1 and z.aktiv
    assert sum(1 for x in st.zimmer if x.id == "GS-2-517") == 1


def test_2_517_nicht_doppelt_mit_eigenem_eintrag(goslar):
    from belegung import speicher
    from belegung import zimmerplan as zp
    from modern import zimmer_zusatz_kern as zz

    speicher.schreiben(zz.DATEI, {"zimmer": [{"id": "GS-2-517", "haus": "2", "etage": "5", "nr": "517", "betten": 2}]})
    st = zp.laden()
    z = [x for x in st.zimmer if x.id == "GS-2-517"]
    assert len(z) == 1 and z[0].betten == 2                  # eigene Angabe geht vor


# ---- Heute entschlackt -------------------------------------------------------------------------------

class _K:
    def __init__(self, stufe):
        self.stufe = stufe


def test_heute_nur_noch_tageszentrale_und_postfach():
    from types import SimpleNamespace

    from modern import seite_heute as sh

    assert set(sh.ANSICHTEN) == {"zentrale", "postfach"}
    assert sh.ansicht(SimpleNamespace(heute_ansicht="uebersicht")) == "zentrale"      # gemerkte alte Ansicht
    assert sh.ansicht(SimpleNamespace()) == "zentrale"
    assert sh.postfach_an(SimpleNamespace(heute_ansicht="postfach"))
    assert not hasattr(sh, "_feed")


def test_ein_knopf_rot_nur_bei_dringendem():
    from modern.oberflaeche import knopf_zahlen

    z = knopf_zahlen([_K("bald"), _K("info")], 0)
    assert z["dringend"] == 0 and z["neu"] == 0 and "2 Aufgaben" in z["tipp"]
    z = knopf_zahlen([_K("dringend"), _K("bald")], 3)
    assert z["dringend"] == 1 and z["neu"] == 3
    assert "davon 1 dringend" in z["tipp"] and "3 neue Neuigkeiten" in z["tipp"]
