"""1.58: Belegungsprognose (Leitungsansicht „Einfach“) für Laien – feste Diagrammfarben (nie aus dem Farbschema),
80-%-Band als Fläche (95 % auf Wunsch), höchstens fünf ganzzahlige Beschriftungen, runde Achse, 12 + 12 Monate,
laufender Monat als Nahtstelle; die Prognose zählt standardmäßig alle Bewohner (UWT und Mieter)."""

import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from modern import blick_kern as bk
from modern import diagramm_stil as ds
from modern import prognose_diagramm as pd_
from modern import themes

STICHTAG = date(2026, 11, 24)


def _zeilen():
    """30 Monate: Mai 2025 … Okt 2027; Nov 2026 läuft, danach Prognose."""
    zs, werte, ist = [], [], []
    for k in range(30):
        j, m = divmod(4 + k, 12)
        mon = date(2025 + j, m + 1, 1)
        art = "ist" if mon < date(2026, 11, 1) else ("laufend" if mon == date(2026, 11, 1) else "prognose")
        w = 200 + 25 * ((k % 12) in (0, 1, 2)) - 15 * ((k % 12) in (6, 7))
        zs.append(SimpleNamespace(monat=mon, art=art, erwartet=w, ist=w if art != "prognose" else None,
                                  lo80=None if art == "ist" else w - 6, hi80=None if art == "ist" else w + 6,
                                  lo95=None if art == "ist" else w - 12, hi95=None if art == "ist" else w + 12))
        werte.append(float(w) + .4)
        ist.append(art == "ist")
    return zs, werte, ist


def _opt(b95=False, hell=True):
    zs, werte, ist = _zeilen()
    g = bk.gf([z.monat for z in zs], werte, ist, STICHTAG, 250, [z.lo80 for z in zs], [z.hi80 for z in zs], None, 3.0)
    return pd_._gf_option(zs, werte, ist, g, 250, STICHTAG, None, b95, hell), g


def _texte(o) -> list[str]:
    t = []
    for se in o["series"]:
        for m in (se.get("markPoint") or {}).get("data", []):
            t.append(str(m.get("value", "")))
    return [x for x in t if x]


def test_farben_fest_und_unabhaengig_vom_farbschema(monkeypatch):
    a, _ = _opt(hell=True)
    monkeypatch.setattr(themes, "AKTIV", {**(themes.AKTIV if isinstance(themes.AKTIV, dict) else {}),
                                          "farbe": "eigen", "farbe_eigen": "#B45309"})
    b, _ = _opt(hell=True)
    assert a == b                                              # Farbschema wechselt – Diagramm bleibt gleich
    f = ds.DIAGRAMM_FARBEN["hell"]
    reihe = {se["name"]: se for se in a["series"]}
    assert reihe["Ist"]["lineStyle"]["color"] == f["ist"] and reihe["Prognose"]["lineStyle"]["color"] == f["prognose"]
    assert reihe["Prognose"]["lineStyle"]["type"] == "dashed"
    assert reihe[pd_.GF_LEGENDE["band80"]]["areaStyle"] == {"color": f["band80"], "opacity": 1}
    assert reihe[pd_.GF_LEGENDE["vorjahr"]]["lineStyle"]["type"] == "dotted"
    assert a["backgroundColor"] == "#FFFFFF" and _opt(hell=False)[0]["backgroundColor"] == "#1E2328"
    assert a["m_eigen"] is True                                 # globale Darstellung (Werte an jedem Punkt) greift nicht
    # jede Farbe genau eine Bedeutung
    werte = [v for k, v in f.items() if k in ("ist", "prognose", "band80", "band95", "vorjahr", "eng")]
    assert len(werte) == len(set(werte))


def test_95_band_nur_auf_wunsch_und_zeichenreihenfolge():
    o, _ = _opt(b95=False)
    namen = [se["name"] for se in o["series"]]
    assert pd_.GF_LEGENDE["band95"] not in namen
    o95, _ = _opt(b95=True)
    n = [se["name"] for se in o95["series"] if not se["name"].startswith("_")]
    assert n[:5] == [pd_.GF_LEGENDE[k] for k in ("band95", "band80", "vorjahr", "ist", "prognose")]


def test_hoechstens_fuenf_ganzzahlige_beschriftungen_wie_ueberschrift():
    o, g = _opt()
    t = _texte(o)
    assert 1 <= len(t) <= 5
    for x in t:
        assert not re.search(r"\d,\d", x)                      # keine Nachkommastellen im Diagramm
    hoch = next(x for x in t if "höchster Wert" in x)
    zahl = hoch.split(":")[1].split()[0]
    assert f"bis zu {zahl} von" in g.titel                     # dieselbe Zahl in Überschrift und Beschriftung
    assert any("noch nicht abgeschlossen" in x for x in t)


def test_achse_rund_und_fenster_12_plus_12():
    o, _ = _opt()
    assert o["yAxis"]["min"] == 0 and o["yAxis"]["max"] % o["yAxis"]["interval"] == 0
    assert o["yAxis"]["max"] > 250                             # Luft über „voll“
    labels = o["xAxis"]["data"]
    assert labels[0] == "Nov 2025" and labels[12] == "Nov 2026" and labels[-1] == "Okt 2027"
    assert ds.runde_achse(928) == (1000, 200) and ds.runde_achse(329) == (400, 100)


def test_nahtstelle_ist_und_prognose_treffen_sich():
    o, _ = _opt()
    reihe = {se["name"]: se for se in o["series"]}
    ist_, prog = reihe["Ist"]["data"], reihe["Prognose"]["data"]
    h = 12
    assert ist_[h] == prog[h] and ist_[h + 1] is None and prog[h - 1] is None
    linien = reihe["Ist"]["markLine"]["data"]
    assert any(li.get("xAxis") == "Nov 2026" for li in linien)
    assert any("voll: 250 Plätze" in li["label"]["formatter"] for li in linien if "label" in li and "formatter" in li["label"])
    assert any(li["label"].get("formatter", "").startswith("eng ab") for li in linien if "label" in li)


def test_legende_symbole_passen_zur_form():
    o, _ = _opt()
    ic = {d["name"]: d["icon"] for d in o["legend"]["data"]}
    assert ic["Ist"] != ic["Prognose"] and ic[pd_.GF_LEGENDE["band80"]] == "rect" and ic["Eng-Zone"] == "rect"
    assert o["legend"]["selectedMode"] is False


def test_alle_bewohner_standard():
    a = SimpleNamespace(aw_status=False, aw_nur_tn=False)
    assert pd_.alle_bewohner(a) is True
    a.aw_nur_tn = True
    assert pd_.alle_bewohner(a) is False
    a.aw_status = True
    assert pd_.alle_bewohner(a) is True
    src = (Path(pd_.__file__).parent / "seite_prognose.py").read_text(encoding="utf-8")
    assert "mit = alle_bewohner(a)" in src
