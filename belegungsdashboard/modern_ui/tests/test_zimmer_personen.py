"""0.7: Kartenansicht, Filter, Person direkt ins Zimmer, „neu“-Erkennung, Erinnerung, Wochenblatt – erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leute(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date.today()
    p = [anreiseliste.Person(n, "GS ASS", heute + timedelta(days=2), True, tn_id=str(i),
                             abreise=heute + timedelta(days=30))
         for i, n in enumerate(["Anders, Anna", "Berger, Bea"], 1)]
    anreiseliste.speichern(p, {})
    yield heute
    aenderungen.verlauf_leeren()


def _freies_zimmer(heute):
    from belegung import zimmerplan as zp
    from modern import zimmer_kern as zk

    st = zp.laden()
    karten, _h = zk.karten(st, zk.filter_bauen("2", "frei"), heute)
    return st, karten[0].etagen[0].karten[0]


def test_karten_je_haus_und_etage(leute):
    from belegung import zimmerplan as zp
    from modern import zimmer_kern as zk

    st = zp.laden()
    haeuser, hinweis = zk.karten(st, zk.filter_bauen(), leute)
    assert len(haeuser) == 1 and hinweis            # viele Zimmer → hausweise
    haeuser, hinweis = zk.karten(st, zk.filter_bauen("3.1"), leute)
    assert haeuser[0].haus == "3.1" and not hinweis and haeuser[0].etagen[0].karten


def test_seltene_filter(leute):
    from modern import zimmer_kern as zk

    f = zk.filter_bauen("", "", {"Vinyl"}, "", {"boeden": ["unbekannt"], "gruppen": ["EMR"], "modus": "darf"})
    assert f.boeden == {"Vinyl", "unbekannt"} and f.gruppen == {"EMR"} and f.gruppen_modus == "darf"
    assert zk.mehr_aktiv({"boeden": ["PVC"], "alle": True}) == 2


def test_person_ins_zimmer_und_rueckgaengig(leute):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import zimmer_kern as zk

    st, k = _freies_zimmer(leute)
    assert {c.name for c in zk.kandidaten(st, k.zimmer, leute)} >= {"Anders, Anna"}
    zk.person_ins_zimmer(k.zimmer, "Neumann, Nora", "GS RVL", "RVL", leute + timedelta(days=1),
                         leute + timedelta(days=20), "w")
    st = zp.laden()
    p = next(x for x in anreiseliste.laden()[0] if x.name == "Neumann, Nora")
    assert (st.zugewiesen(p.schluessel) or {}).get("zimmer") == k.zimmer
    kern.rueckgaengig()
    assert not any(x.name == "Neumann, Nora" for x in anreiseliste.laden()[0])
    with pytest.raises(ValueError):
        zk.person_ins_zimmer(k.zimmer, "ohne Komma", "GS RVL", "RVL", leute, leute + timedelta(days=3))


def test_neue_personen_sieben_tage(leute):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern

    st = zp.laden()
    assert kern.neue_personen(st, leute) == {}          # erster Start: alte Personen gelten nicht als neu
    anreiseliste.person_speichern(anreiseliste.Person("Zander, Zoe", "GS RVL", leute + timedelta(days=5), True,
                                                      abreise=leute + timedelta(days=40)))
    st = zp.laden()
    neu = kern.neue_personen(st, leute)
    assert len(neu) == 1 and list(neu.values()) == [leute]
    assert kern.neue_personen(st, leute + timedelta(days=7)) == {}


def test_erinnerung_im_dashboard(leute):
    from belegung import anreiseliste
    from modern import anreisen_kern as ank

    p = anreiseliste.laden()[0][0]
    assert "unter Termine" in ank.erinnerung_setzen(p.schluessel, True, 3, "app")
    p2 = next(x for x in anreiseliste.laden()[0] if x.schluessel == p.schluessel)
    assert (p2.erinnerung_tage, p2.erinnerung_kanal) == (3, "app")
    ank.erinnerung_setzen(p.schluessel, False, 0, "app")
    assert next(x for x in anreiseliste.laden()[0] if x.schluessel == p.schluessel).erinnerung_tage is None


def test_wochenblatt_und_exporte(leute):
    from belegung import zimmerplan as zp
    from modern import seiten_kern as sk
    from modern import zimmer_kern as zk

    montag = leute - timedelta(days=leute.weekday())
    assert "Wochenblatt" in sk.wochenblatt(montag, True)
    assert len(sk.wochen(leute)) == 4
    st = zp.laden()
    text, n = zk.liste_tsv(st, zk.filter_bauen("6"), leute)
    assert n > 0 and text.startswith("Zimmer\tEtage")
    _t, pfad = zk.belegung_excel(st, leute)
    assert pfad.exists()
