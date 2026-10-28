"""0.26: Flur-Raster (Abreisewellen je Flur und Woche) – erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def test_wellen_reinigungsfenster():
    from modern import flur_kern as fk

    fr, sa, mo, di = date(2030, 1, 4), date(2030, 1, 5), date(2030, 1, 7), date(2030, 1, 8)
    assert fk.reinigungstag(sa) == mo
    assert len(fk.wellen_bilden([(fr, "a"), (mo, "b")])) == 1                 # Fr + Mo = ein Reinigungsfenster
    assert len(fk.wellen_bilden([(fr, "a"), (sa, "b"), (mo, "c")])) == 1      # Wochenende zählt zum Montag
    assert len(fk.wellen_bilden([(di, "a"), (date(2030, 1, 11), "b")])) == 2  # Di + Fr = zwei
    w = fk.wellen_bilden([(mo, "a"), (di, "b"), (date(2030, 1, 9), "c"), (date(2030, 1, 10), "d")])
    assert [len(x.zimmer) for x in w] == [2, 2]                                # fest verankert, keine Kette Mo…Do
    assert w[0].text == "Mo 07.01. / Di 08.01."


def test_doppelzimmer_wird_erst_ganz_frei():
    from modern import flur_kern as fk

    assert fk._zusammen([(date(2030, 1, 1), date(2030, 3, 1)), (date(2030, 2, 1), date(2030, 3, 20))]) == \
        [(date(2030, 1, 1), date(2030, 3, 20))]


def _stand_mit(belegungen):
    """Erfundene Belegungen direkt in den Plan: (Name, Zimmer-Index auf einem Flur, von, bis, Maßnahme)."""
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp

    st = zp.laden()
    z0 = next(z for z in st.zimmer if z.aktiv and not z.gaeste and z.haus == "3.1")
    flur = sorted((z for z in st.zimmer if z.aktiv and not z.gaeste and z.flur_schluessel == z0.flur_schluessel),
                  key=lambda z: z.nummer)
    for name, i, von, bis, mn in belegungen:
        st.lage.belegungen.setdefault(flur[i].id, []).append(gebaeudeplan.Belegung(flur[i].id, von, bis, "belegt", name, mn))
    return st, flur


def test_raster_zaehlt_wellen_je_flur(leer):
    from modern import flur_kern as fk

    mo = date(2030, 1, 7)
    an = mo + timedelta(days=7)
    st, flur = _stand_mit([("Muster, Anna", 0, an, an + timedelta(days=116), "GS RVL"),
                           ("Muster, Bert", 1, an, an + timedelta(days=119), "GS RVL"),      # Fr/Mo: dieselbe Welle
                           ("Probe, Clara", 2, an, an + timedelta(days=150), "GS RVL"),
                           ("Kurz, Kai", 3, an, an + timedelta(days=10), "EMR Kurs"),
                           ("Miete, Mia", 4, mo - timedelta(days=300), mo + timedelta(days=300), "Mieter")])
    flure = fk.raster(st, mo, 8)
    f = next(x for x in flure if flur[0].id in x.zimmer)
    z = f.zellen[2]
    assert z.belegt == 3 and z.n == 2 and z.stufe == "warn"
    assert f.zellen[1].kurz == 1 and f.zellen[0].mieter == 1 and f.zellen[0].n == 0   # kurz/Mieter nicht gewertet
    d = fk.detail(f, z.woche)
    assert [len(leute) for _w, leute in d["wellen"]] == [2, 1] and len(d["mieter"]) == 1
    assert fk.zusammenfassung(flure, 2)["warn"] >= 1


def test_zeitstrahl_nur_ein_flur(leer):
    from belegung import zimmerplan as zp
    from modern import seiten_kern as sk

    st = zp.laden()
    z = next(z for z in st.zimmer if z.aktiv and z.haus == "3.1")
    flur = "|".join(z.flur_schluessel)
    zeilen = sk.zeitstrahl(st, "3.1", date.today(), 14, flur=flur)
    alle = sk.zeitstrahl(st, "3.1", date.today(), 14)
    assert zeilen and len(zeilen) < len(alle)
    assert all("|".join(st.lage.zimmer[x.zimmer].flur_schluessel) == flur for x in zeilen)
