"""1.06 – Zu- und Abgänge in der Teilnehmer-Prognose, veraltete Maßnahmen entfernen, Kurznamen. Erfundene Daten."""

from datetime import date

import numpy as np

from modern import bestand_kern as bk
from modern import bestand_prognose as bp
from modern import massnahmen_kern as mk

from test_v079 import L, T, _daten


def _sim():
    fs = bp.faelle(_daten(), T, {}, L)
    md = bp.modell(fs, L, T)
    return fs, md, bp.simulieren(md, 0, 200, roh=True)


def test_bestand_plus_zugaenge_minus_abgaenge():
    _fs, _md, e = _sim()
    z = e.zeile("Alle")
    roh = e.roh[z]                                           # (R, T)
    diff = roh[:, -1] - roh[:, 0]
    assert np.allclose(diff, e.zu[z].sum(axis=1) - e.ab[z].sum(axis=1))
    assert np.all(e.zu[:, :, 0] == 0) and np.all(e.ab[:, :, 0] == 0)
    for art in e.arten:                                      # je Art ebenso
        i = e.zeile(art)
        assert np.allclose(e.roh[i][:, -1] - e.roh[i][:, 0], e.zu[i].sum(axis=1) - e.ab[i].sum(axis=1))


def test_fluss_und_summe():
    _fs, _md, e = _sim()
    f = bp.fluss(e, "Alle", "zu")
    assert len(f.median) == len(e.monate) and f.median[0] == 0 and np.all(f.p10 <= f.p90)
    med, lo, hi, bek = bp.fluss_summe(e, "Alle", "zu", 1, 6)
    assert lo <= med <= hi and bek >= 0
    assert bp.fluss(e, "Alle", "ab").bekannt is None


def test_ist_fluss_zaehlt_eintritte_und_enden():
    fs, _md, _e = _sim()
    zu = bp.ist_fluss(fs, L, "Alle", "zu", 12)
    ab = bp.ist_fluss(fs, L, "Alle", "ab", 12)
    assert len(zu) == len(ab) == 12 and zu[-1][0] == L
    assert sum(n for _d, n in zu if n) > 0 and sum(n for _d, n in ab if n) > 0


def test_veraltete_massnahmen_entfernen():
    roh = {"pivot": {"von": "2021-01-01", "bis": "2027-12-31",
                     "kurse": {"GS ALT 1901": {"von": "2019-01-02", "werte": mk._rle([5] * 400)},
                               "GS VW 2601": {"von": "2026-01-05", "werte": mk._rle([8] * 400)}}},
           "bestand": {"aufenthalte": [], "meta": {}}}
    ue = mk.familien_uebersicht(roh)
    assert [x.familie for x in ue] == ["GS ALT", "GS VW"] and ue[0].letzter == date(2019, 1, 2)
    roh["entfernt"] = ["GS ALT"]
    assert {k.familie for k in mk.kurse(roh)} == {"GS VW"} and len(mk.alle_kurse(roh)) == 2
    assert mk.familien_uebersicht(roh)[0].entfernt
    a = bk.Aufenthalt(1, "GS ALT 1901", date(2019, 1, 2), date(2019, 6, 1), 150, 0, 0)
    b = bk.Aufenthalt(2, "GS VW 2601", date(2026, 1, 5), date(2026, 6, 1), 150, 0, 0)
    roh["bestand"]["aufenthalte"] = [x.als_liste() for x in (a, b)]
    assert [x.kurs for x in bk.laden(roh)[0]] == ["GS VW 2601"]


def test_v107_overlay_symbol_und_ansicht_knoepfe():
    from modern import seite_massnahmen as sm
    from modern import symbole

    h = symbole.html("building", "", overlay="arrow_right", ofarbe=symbole.BLAU)
    assert "m-sym-ov" in h and "#0284c7" in h
    assert "m-sym-ov" not in symbole.html("building", "")
    assert [k[0] for k in sm.ANSICHT_KNOEPFE] == ["neu", "prognose", "bestand"]
    assert all(symbole.vorhanden(k[2]) and (not k[4] or symbole.vorhanden(k[4])) for k in sm.ANSICHT_KNOEPFE)
    for n in ("seat", "tag", "broom", "task_list_square_ltr", "people_team", "filter", "arrow_trending"):
        assert symbole.vorhanden(n), n
