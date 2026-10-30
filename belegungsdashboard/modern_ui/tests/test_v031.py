"""0.31: Bestimmtes Zimmer prüfen – warum es nicht wählbar ist, und von Hand zuweisen, wenn es geht. Erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield date.today()
    aenderungen.verlauf_leeren()


def _person(h, name="Pruef, Paula", massnahme="GS iBTZ", tage=8, dauer=90, nr="970"):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp

    an = h + timedelta(days=tage)
    anreiseliste.person_speichern(anreiseliste.Person(name, massnahme, an, True, tn_id=nr, abreise=an + timedelta(days=dauer)))
    st = zp.laden()
    return st, next(b for b in st.bedarf if b.name == name)


def test_zimmer_pruefen_eingaben_und_passt(leer):
    from modern import kern

    st, b = _person(leer)
    for eingabe in ("3.2-111", "3.2 111", "GS-3.2-111", "3.2/111"):
        r = kern.zimmer_pruefen(st, b.schluessel, eingabe)
        assert r.zimmer == "GS-3.2-111" and r.art == "passt", (eingabe, r)
    assert kern.zimmer_pruefen(st, b.schluessel, "9-999").art == "nein"
    assert kern.zuweisen(b.schluessel, "GS-3.2-111")


def test_zimmer_pruefen_nennt_wer_im_weg_ist(leer):
    from belegung import zimmerplan as zp
    from modern import kern

    _st, erste = _person(leer, "Vorher, Volker", nr="971")
    kern.zuweisen(erste.schluessel, "GS-3.2-111")
    st, b = _person(leer, nr="972")
    r = kern.zimmer_pruefen(zp.laden(), b.schluessel, "3.2-111")
    assert r.art == "nein" and "belegt oder gesperrt" in r.text and any("Vorher, Volker" in g for g in r.gruende)


def test_zimmer_pruefen_doppelzimmer_und_ausnahme(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import kern

    st, b = _person(leer)
    r = kern.zimmer_pruefen(st, b.schluessel, "3.2-112")             # Doppelzimmer → feste Regel
    assert r.art == "nein" and "Doppelzimmer" in r.text and "Stammdaten" in r.text
    r = kern.zimmer_pruefen(st, b.schluessel, "2-115")               # 1. OG Haus 2: nur Kurzmaßnahmen → Ausnahme
    assert r.art == "ausnahme" and "Kurzmaßnahmen" in r.text
    assert kern.zuweisen(b.schluessel, r.zimmer)                      # von Hand geht es
    maengel.setzen("GS-3.2-110", "schimmel", True, leer)
    assert kern.zimmer_pruefen(zp.laden(), b.schluessel, "3.2-110").art == "nein"   # unbewohnbar: nie
