"""0.59: Mieter sind von der Männer-Regel (Haus 6, Bad über den Flur) ausgenommen. Erfundene Daten."""

from datetime import date

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, regeln_kern, standort_kern  # noqa: F401 – kern installiert die Ausnahme

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    regeln_kern.zuruecksetzen()
    aenderungen.verlauf_leeren()


def _bedarf(gruppe: str, geschlecht: str, massnahme: str):
    from belegung import zimmerplan as zp

    return zp.Bedarf(f"name:erfunden {gruppe}|2027-03-01", f"Erfunden, {gruppe}", massnahme, gruppe,
                     date(2027, 3, 1), date(2028, 2, 28), geschlecht)


def test_mieterin_darf_in_zimmer_mit_bad_ueber_den_flur(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    flurbad = next(z for z in st.zimmer if z.haus == "6" and z.nur_maenner and z.aktiv and z.betten == 1)
    mieterin = _bedarf("Mieter", "w", "Miete Goslar")
    assert zp.passt(st.lage, flurbad, mieterin) is None
    assert zp.passt(st.lage, flurbad, _bedarf("Mieter", "", "Miete Goslar")) is None      # Geschlecht unbekannt
    assert zp.passt(st.lage, flurbad, _bedarf("Mieter", "m", "Miete Goslar")) is None


def test_andere_gruppen_weiter_nur_maenner(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    flurbad = next(z for z in st.zimmer if z.haus == "6" and z.nur_maenner and z.aktiv and z.betten == 1)
    uwt_frau = _bedarf("UWT", "w", "GS UWT ERF27")
    assert zp.passt(st.lage, flurbad, uwt_frau) == "Bad über den Flur – nur Männer"


def test_uebrige_regeln_gelten_auch_fuer_mieter(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    ausser_haus6 = next(z for z in st.zimmer if z.haus == "3.2" and z.aktiv)
    assert zp.passt(st.lage, ausser_haus6, _bedarf("Mieter", "w", "Miete Goslar"))        # Mieter nur Haus 6


def test_vorschlag_findet_zimmer_fuer_mieterin(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    frei_flur = [z for z in st.zimmer if z.haus == "6" and z.aktiv and z.nur_maenner
                 and zp.passt(st.lage, z, _bedarf("Mieter", "w", "Miete Goslar")) is None]
    assert frei_flur                                                                      # sie werden angeboten


def test_keine_geschlechts_rueckfrage_bei_mietern(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    m = _bedarf("Mieter", "", "Miete Goslar")
    zt = zp.vorschlagen(st.lage, [m])[0]
    assert zt.zimmer is not None and zt.zimmer.haus == "6"
    assert not any("Geschlecht" in w for w in zt.warnungen)
