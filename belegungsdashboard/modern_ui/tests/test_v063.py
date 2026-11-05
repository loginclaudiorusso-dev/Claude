"""0.63: realistische Spannen (Wurzel-Einheiten), Obergrenze je Maßnahme, Holt-Winters und Anteil am Gesamttrend.
Nur erfundene Kurse und Zahlen."""

import random
from datetime import date

import pytest

from modern import massnahmen_kern as mk


def _roh(fams: dict[str, int], jahre=range(2017, 2026), streu=.25) -> dict:
    random.seed(5)
    kurse = {}
    for fam, n in fams.items():
        for j in jahre:
            for m in (1, 6):
                d = max(1, round(n * streu))
                kurse[f"{fam} {j % 100}{m:02d}"] = (date(j, m, 3), [max(1, n + random.randint(-d, d))] * 700)
    return {"pivot": {"von": "2016-01-01", "bis": "2025-12-31",
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}},
            "zuordnung": {f: "lang" for f in fams}}


def test_kleine_massnahmen_blaehen_die_spanne_der_grossen_nicht_auf():
    roh = _roh({"GS VW": 18, "GS KL": 4, "GS MI": 3})
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW", "GS KL"], 2, 4)
    vw = next(z for z in r["GS VW"].zeilen if z.hj == (2026, 2))
    assert vw.klein95 >= 8 and vw.gross95 <= 28              # vorher: 1–28 (Prozentfehler der kleinen)
    assert vw.klein95 <= vw.klein <= vw.erwartet <= vw.gross <= vw.gross95
    kl = next(z for z in r["GS KL"].zeilen if z.hj == (2026, 2))
    assert kl.gross95 - kl.erwartet < vw.gross95 - vw.erwartet   # kleine Maßnahme: kleinere Spanne in Personen


def test_obergrenze_automatisch_und_eigene_angabe(tmp_path, monkeypatch):
    roh = _roh({"GS VW": 18})
    r = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 2, 4)["GS VW"]
    assert r.kap_quelle == "automatisch" and 18 <= r.kapazitaet <= 30
    assert all(z.gross95 <= r.kapazitaet for z in r.zeilen if z.art != "ist")
    roh["kapazitaet"] = {"GS VW": 20}
    r2 = mk.neuanmeldungen(roh, date(2025, 11, 5), ["GS VW"], 2, 4)["GS VW"]
    assert r2.kapazitaet == 20 and r2.kap_quelle == "eigene Angabe"
    assert all(z.gross95 <= 20 and z.erwartet <= 20 for z in r2.zeilen if z.art != "ist")


def test_kapazitaet_schritt(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from modern import kern, standort_kern  # noqa: F401

    standort_kern.waehlen("GS", merken_=False)
    mk.kapazitaet_schritt("GS VW", 26)
    assert mk.kapazitaeten() == {"GS VW": 26}
    mk.kapazitaet_schritt("GS VW", None)
    assert mk.kapazitaeten() == {}


def test_holt_winters_nutzt_beide_wellen():
    # Winter 10, Sommer 20, beide wachsen um 2 je Jahr
    folge = []
    for j in range(2019, 2025):
        folge += [((j, 1), 10 + 2 * (j - 2019)), ((j, 2), 20 + 2 * (j - 2019))]
    w = mk._holt_winters(folge, (2025, 1))
    s = mk._holt_winters(folge, (2025, 2))
    assert 14 < w < 24 and s > w + 5                         # Saison bleibt getrennt, Trend wird fortgesetzt
    assert mk._holt_winters(folge[:3], (2025, 1)) is None


def test_anteil_am_gesamttrend():
    roh = _roh({"GS VW": 20, "GS KB": 10})
    ks = mk._starts(mk.kurse(roh), date(2016, 1, 1))
    eigene = [k for k in ks if k.familie == "GS KB"]
    w = mk.schaetzung(eigene, (2026, 1), date(2025, 11, 5), (2016, 2), "anteil", ks)
    assert 6 < w < 14


def test_rueckwaertstest_kalibriert():
    roh = _roh({"GS VW": 18, "GS KB": 12, "GS FI": 9})
    for t in mk.verfahren_testen(roh):
        k80, n = t.treffer80
        k95, _n = t.treffer95
        assert n > 20 and .6 <= k80 / n <= .97 and k95 / n >= .85, (t.verfahren, t.treffer80, t.treffer95)
