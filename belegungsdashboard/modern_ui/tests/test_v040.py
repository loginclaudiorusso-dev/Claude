"""0.40: Haus 6 – Bad über den Flur (x01, x02, x08, x09), schaltbare Aufteilung je Etage. Erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import regeln_kern, standort_kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)            # Haus-6-Korrektur ist aktiv, Aufteilung aus
    yield tmp_path
    regeln_kern.zuruecksetzen()
    aenderungen.verlauf_leeren()


def test_bad_ueber_flur_x05_korrigiert(goslar):
    from belegung import zimmerplan as zp

    st = zp.laden()
    etage = sorted((z for z in st.zimmer if z.haus == "6" and z.etage == "5"), key=lambda z: z.nummer)
    assert len(etage) == 9
    assert [z.nummer % 100 for z in etage if z.nur_maenner] == [1, 2, 8, 9]


def test_aufteilung_schaltbar_mit_rueckgaengig(goslar):
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import regeln_kern as rk

    st = zp.laden()
    eigen = next(z for z in st.zimmer if z.haus == "6" and z.nummer % 100 == 5)
    flurbad = next(z for z in st.zimmer if z.haus == "6" and z.nummer % 100 == 1)
    assert not zp.erlaubt(eigen, "Reha")                                  # aus: wie bisher
    rk.setzen(True)
    assert zp.erlaubt(eigen, "Reha") and not zp.erlaubt(flurbad, "Reha")    # nur Zimmer mit eigenem Bad
    assert zp.erlaubt(flurbad, "Mieter") and zp.erlaubt(flurbad, "UWT")
    ok, _t = kern.rueckgaengig()
    assert ok and not rk.an() and not zp.erlaubt(eigen, "Reha")


def test_vorrang_auf_renovierten_etagen(goslar):
    from types import SimpleNamespace

    from belegung import zimmerplan as zp
    from modern import regeln_kern as rk

    rk.setzen(True)
    st = zp.laden()
    etage = [z for z in st.zimmer if z.haus == "6" and z.etage == "4"]
    for z in etage:
        z.renoviert = "2030-01-01"
    assert ("6", "4") in rk.aktualisieren(st)
    mieter, uwt = SimpleNamespace(gruppe="Mieter", kurz=False, tier=False, dz="", geschlecht="m"), \
        SimpleNamespace(gruppe="UWT", kurz=True, tier=False, dz="", geschlecht="m")
    wert = {z.nummer % 100: z for z in etage}
    assert zp.zimmer_wert(wert[1], mieter) > zp.zimmer_wert(wert[8], mieter) > zp.zimmer_wert(wert[5], mieter)
    assert zp.zimmer_wert(wert[9], uwt) > zp.zimmer_wert(wert[2], uwt)
    nicht_reno = next(z for z in st.zimmer if z.haus == "6" and z.etage == "5" and z.nummer % 100 == 1)
    assert not any("renovierten Etage" in t for _p, t in zp.zimmer_wert_details(nicht_reno, mieter))


def test_vorschau_aendert_nichts(goslar):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import regeln_kern as rk

    h = date.today()
    an = h + timedelta(days=10)
    anreiseliste.speichern([anreiseliste.Person(f"Haupt, Hans{i}", "GS KBM 2611", an, True, tn_id=str(880 + i), geschlecht="m",
                                                abreise=an + timedelta(days=400)) for i in range(3)], {})
    st = zp.laden()
    vorher = rk.an()
    diff = rk.vorschau(st, h)
    assert rk.an() == vorher and isinstance(diff, list)
    assert not zp.laden().zuweisungen                                       # nichts gespeichert
