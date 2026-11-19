"""1.21 – Doppelzimmer einzeln vergeben (je Anreise per Knopfdruck), wenn die DZ-Liste nicht stimmt. Erfundene Daten."""

import inspect
from datetime import date

import pytest

TAG = date(2027, 3, 1)


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, regeln_kern, standort_kern  # noqa: F401 – kern installiert die Anpassungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    regeln_kern.zuruecksetzen()
    aenderungen.verlauf_leeren()


def _uwt(nr: int, dz: str = ""):
    from belegung import zimmerplan as zp

    return zp.Bedarf(f"uwt:K1:{TAG.isoformat()}:{nr}", f"Erfunden {nr}", "UWT K1", "UWT", TAG, date(2027, 8, 31), "m",
                     dz=dz)


def _partner_im_dz(st, dz: str = ""):
    """Ein Doppelzimmer, in dem schon eine UWT-Person derselben Klasse geplant ist."""
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp

    z = next(z for z in st.zimmer if z.betten > 1 and z.aktiv and not z.gaeste and not z.nur_maenner
             and zp.passt(st.lage, z, _uwt(1)) is None)
    st.lage.belegungen.setdefault(z.id, []).append(
        gebaeudeplan.Belegung(z.id, TAG, date(2027, 8, 31), "geplant", "Erfunden 1", "UWT K1", "m", _uwt(1).schluessel))
    if dz:
        st.lage.dz[_uwt(1).schluessel] = dz
    return z


def test_anwenden_nur_uwt_am_tag():
    from belegung import zimmerplan as zp
    from modern import dz_einzeln_kern as dze

    reha = zp.Bedarf("r", "Erfunden R", "Reha", "Reha", TAG, date(2027, 9, 1))
    spaeter = zp.Bedarf("u2", "Erfunden U", "UWT K2", "UWT", date(2027, 4, 1), date(2027, 9, 1), dz="K2:1")
    b = dze.anwenden([_uwt(1, "K1:1"), reha, spaeter], {TAG.isoformat()})
    assert [x.dz for x in b] == ["allein", "", "K2:1"]


def test_schalter_trennt_paare_und_rueckgaengig(goslar):
    from belegung import aenderungen
    from belegung import zimmerplan as zp
    from modern import dz_einzeln_kern as dze

    st = zp.laden()
    z = _partner_im_dz(st)
    assert zp.passt(st.lage, z, _uwt(2)) is None                    # ohne Schalter: gleiche Klasse teilt das DZ
    assert not dze.an(TAG.isoformat())
    text = dze.setzen(TAG.isoformat(), True)
    assert dze.an(TAG.isoformat()) and "allein" in text
    b = zp.angaben_anwenden([_uwt(2)], {})[0]                       # zp.laden nutzt genau diese Funktion
    assert b.dz == "allein" and zp.passt(st.lage, z, b) is not None
    aenderungen.rueckgaengig()
    assert not dze.an(TAG.isoformat())
    assert zp.angaben_anwenden([_uwt(2)], {})[0].dz == ""


def test_menueband_und_doku():
    from modern import seite_anreisen

    q = inspect.getsource(seite_anreisen.zuteilen_band)
    assert '"Doppelzimmer einzeln"' in q and "dze.betroffen" in q


def test_gespeicherte_paare_werden_aufgeloest(goslar):
    from belegung import aenderungen, uwt
    from belegung import speicher
    from belegung import zimmerplan as zp
    from modern import dz_einzeln_kern as dze
    from modern import kern

    pers = [{"tn_id": str(900 + i), "name": f"Muster{i}, Erfunden", "geschlecht": "m"} for i in range(1, 5)]
    speicher.schreiben(uwt.DATEI, {"bloecke": [{"klasse": "K9", "anreise": TAG.isoformat(), "abreise": "2027-08-31",
                                                "anzahl": 4, "personen": pers}]})
    speicher.schreiben(uwt.KLASSEN_DATEI, {"klassen": {"K9": [dict(p, dz=f"K9:{i // 2 + 1}") for i, p in enumerate(pers)]}})
    k = TAG.isoformat()
    kern.vorschlaege_uebernehmen(k, "alle")
    vorher = [z["zimmer"] for z in zp.laden().zuweisungen if z["person"].startswith("uwt:K9")]
    assert len(set(vorher)) == 2                                     # laut DZ-Liste: zwei Paare
    assert "2 Person(en)" in dze.setzen(k, True)
    zs = kern.zeilen(zp.laden(), k)
    assert sum(z.status == "ohne" and z.vorschlag is not None for z in zs) == 2
    kern.vorschlaege_uebernehmen(k, "alle")
    nachher = [z["zimmer"] for z in zp.laden().zuweisungen if z["person"].startswith("uwt:K9")]
    assert len(set(nachher)) == 4 and {z.status for z in kern.zeilen(zp.laden(), k)} == {"ok"}
    aenderungen.rueckgaengig()
    aenderungen.rueckgaengig()
    assert sorted(z["zimmer"] for z in zp.laden().zuweisungen if z["person"].startswith("uwt:K9")) == sorted(vorher)
    assert not dze.an(k)
