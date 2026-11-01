"""0.42: Planen nach Budget (Bau und Möbel getrennt), Monate mit möglichst wenig Engpässen. Erfundene Daten."""

from datetime import date

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _p(rk, **mehr):
    return {**rk.parameter(), "preisstand": 2031, "preis_pct": 0, "puffer_pct": 0, "neben_pct": 0, "vorsteuer_pct": 100,
            "kosten": {"2": {"bau_etage": 90000, "moebel_zimmer": 1000, "aufbau_zimmer": 0, "dauer_tage": 30},
                       "6": {"bau_etage": 20000, "moebel_zimmer": 1000, "aufbau_zimmer": 0, "dauer_tage": 30}}, **mehr}


def test_budget_auswahl_beide_budgets_und_bedarf(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    p = _p(rk)
    fl = rk.flure(st, date(2030, 1, 1), p)
    h6 = [f for f in fl if f.haus == "6"]
    # Bau reicht für zwei Haus-6-Etagen, Möbel nur für eine → eine Etage
    eine = rk.budget_auswahl(fl, p, 2031, 45000, 1000 * len(h6[0].zimmer) + 10)
    assert eine and len(eine.flure) == 1 and eine.flure[0].haus == "6"
    assert eine.kosten.investition <= 1000 * len(h6[0].zimmer) + 10
    # Bedarf geht vor: eine Etage mit „Renovierung nötig“ wird gewählt
    ziel = h6[-1]
    for z in ziel.zimmer[:2]:
        maengel.setzen(z.id, "renovierung", True, date(2029, 1, 1))
    fl = rk.flure(zp.laden(), date(2030, 1, 1), p)
    aw = rk.budget_auswahl(fl, p, 2031, 25000, None)
    assert [f.schluessel for f in aw.flure] == [ziel.schluessel]
    # zu wenig Budget → nichts, die günstigste Etage wird genannt
    assert rk.budget_auswahl(fl, p, 2031, 1000, None) is None
    assert rk.guenstigste(fl, p, 2031)[0].haus == "6"
    # ohne Grenzen: alles
    assert len(rk.budget_auswahl(fl, p, 2031, None, None).flure) == len(fl)


def test_monat_mit_engpass_wird_gemieden():
    from modern import renovierung_kern as rk

    f = rk.Flur("6|3|", "6", "3", "", zimmer=[])
    f.zimmer = [type("Z", (), {"betten": 1})() for _ in range(9)]
    fs = []
    for m in range(1, 5):
        fe = rk.Fenster(date(2031, m, 1), date(2031, m, 28), date(2030, 12, 1))
        fe.prognose = (200, 190, 280 if m == 1 else 200)           # Januar: obere Prognose hoch
        fs.append(fe)
    rk.engpass_markieren(fs, f, 300)
    assert [fe.engpass for fe in fs] == [True, False, False, False]
    best = rk.bester_monat(fs, date(2030, 1, 1))
    assert best.start.month == 2 and not best.engpass


def test_vorschlaege_mit_kapazitaet_und_budgetmodus_gespeichert(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    p = _p(rk)
    rk.parameter_schritt({**p, "modus": "budget", "budget_bau": 50000, "budget_moebel": None})
    q = rk.parameter()
    assert q["modus"] == "budget" and q["budget_bau"] == 50000 and q["budget_moebel"] is None
    fl = rk.flure(st, date(2030, 1, 1), q)
    aw = rk.budget_auswahl(fl, q, 2031)
    prog = {(2031, m): (100.0, 90.0, 100.0 if m != 1 else 400.0) for m in range(1, 13)}
    vs = rk.vorschlaege(st, fl, 2031, date(2030, 1, 1), q, prog, aw, kap=300)
    assert vs and all(v.fenster and v.fenster.start.month != 1 for v in vs)      # Januar wäre ein Engpass
    zeilen = rk.jahresplan(st, 2031, vs, q)
    assert all(not z.engpass for z in zeilen)
