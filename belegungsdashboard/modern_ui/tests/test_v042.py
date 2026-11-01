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
