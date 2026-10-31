"""0.39: Ehrliche Prognose-Kennzahlen, flurweise Renovierungsplanung (Haus 2/6). Erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _pg(n_prognose: int):
    from modern import auswertung_kern as ak

    zeilen = [ak.PZeile(date(2026, m, 1), "ist", 100.0, 0, 0, 0, 0, None, 100.0) for m in range(1, 10)]
    zeilen += [ak.PZeile(date(2026 + (m - 1) // 12, (m - 1) % 12 + 1, 1), "prognose", 120.0 + (m > 22) * 15, 115.0, 125.0 + (m > 22) * 15,
                         110.0, 135.0 + (m > 22) * 15, 90.0, None) for m in range(10, 10 + n_prognose)]
    return ak.Prognose(zeilen, 150, "M", "Testmodell", 2.0, 4.0, .8, [("M", 2.0)], [])


def test_kennzahlen_folgen_dem_zeitraum_und_sind_ehrlich_benannt():
    from types import SimpleNamespace

    from modern import analytik_kern as an

    pg = _pg(36)
    ds = SimpleNamespace(stichtag=date(2026, 9, 30), erster_tag=date(2026, 1, 1),
                         aufschluesselung=lambda *a: SimpleNamespace(belegt=100.0),
                         verlauf=lambda *a: (_ for _ in ()).throw(KeyError()))
    k12 = {k.schluessel: k for k in an.executive(ds, "BFW GS", False, pg, horizont=12).kpis}
    k36 = {k.schluessel: k for k in an.executive(ds, "BFW GS", False, pg, horizont=36).kpis}
    assert k12["risiko"].titel == "Monate an der Warnschwelle" and k12["risiko"].einheit == "von 12 Monaten"
    assert k36["risiko"].einheit == "von 36 Monaten" and "nur fortgeschrieben" in k36["risiko"].bezug
    assert k12["risiko"].wert == "0" and int(k36["risiko"].wert) > 0          # spätere Monate zählen bei 36 mit
    assert "keine Wahrscheinlichkeit" in k12["risiko"].hinweis
    assert k12["guete"].stufe == "neutral" and "kein unabhängiger Test" in k12["guete"].vergleich
    html = an.summary_html(an.executive(ds, "BFW GS", False, pg, horizont=24), pg, "BFW GS", False, 150, 0, None, 24)
    assert "Nächste 24 Monate" in html and "Ab Monat 13 rechnerisch fortgeschrieben" in html
    assert an.szenario_vergleich(pg, 150, 0, 24)[-1].ausgang.endswith("von 24")


def test_untere_bandgrenze_nie_unter_gebucht(monkeypatch):
    from types import SimpleNamespace

    from modern import auswertung_kern as ak

    monkeypatch.setattr(ak, "_monatsprognosen", lambda ds, s, b, monate: {
        monate[0]: {"art": "prognose", "erwartet": 100.0, "lo80": 80.0, "hi80": 120.0, "lo95": 70.0, "hi95": 130.0,
                    "gesichert": 95.0, "ist": None, "vertraege": 0.0}})
    ds = SimpleNamespace(stichtag=date(2026, 10, 15), prognose=SimpleNamespace(modelle={}), kapazitaet=lambda *a: 150)
    z = ak._prognose(ds, "BFW GS", False, 0, 1).zeilen[0]
    assert (z.lo80, z.lo95, z.hi80) == (95.0, 95.0, 120.0)


def _belegung(zid, name, von, bis, art="belegt", massnahme="GS RVL"):
    from belegung import gebaeudeplan

    return gebaeudeplan.Belegung(zid, von, bis, art, name, massnahme)


def test_flur_bedarf_nachvollziehbar_und_luecken(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    h = date(2030, 3, 1)
    st = zp.laden()
    fl = rk.flure(st, h)
    assert {f.haus for f in fl} == {"2", "6"} and len(fl) == 28            # nur Haus 2 und 6
    f2 = next(f for f in fl if f.schluessel == "2|3|Ost")
    zid = f2.zimmer[0].id
    maengel.setzen(zid, "schimmel", True, h - timedelta(days=120))       # Stufe 3, alt
    maengel.setzen(f2.zimmer[1].id, "renovierung", True, h)
    fl = rk.flure(zp.laden(), h)
    f2 = next(f for f in fl if f.schluessel == "2|3|Ost")
    assert fl[0] is f2 and f2.bedarf == round(10 * (3 + 1 + 4) / len(f2.zimmer), 1)
    assert any("Renovierung nötig" in t for _p, t in f2.gruende) and any("unbewohnbar" in t for _p, t in f2.gruende)
    assert any("ohne Renovierungsvermerk" in l for l in f2.luecken)          # Lücke statt Schätzung
    assert f2.kosten == (100000, 100000)
    f6 = next(f for f in fl if f.haus == "6")
    assert f6.kosten == (10000 + 3000 * len(f6.zimmer), 10000 + 4000 * len(f6.zimmer))
    assert any("nur Männer" in s for s in f6.sonder)


def test_zeitfenster_umzug_umleiten_stopp(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    f = next(x for x in rk.flure(st, date(2030, 1, 1)) if x.schluessel == "2|4|West")
    a, b, c = (z.id for z in f.zimmer[:3])
    st.lage.belegungen.setdefault(a, []).append(_belegung(a, "Lang, Lea", date(2029, 6, 1), date(2031, 5, 31)))
    st.lage.belegungen.setdefault(b, []).append(_belegung(b, "Neu, Nils", date(2030, 6, 10), date(2030, 9, 30), "geplant"))
    st.lage.belegungen.setdefault(c, []).append(_belegung(c, "Miete, Mia", date(2030, 5, 15), date(2030, 5, 25), "belegt",
                                                          "Miete Goslar"))
    fe = rk.fenster(st, f, date(2030, 6, 1))
    assert [x[0] for x in fe.umzug] == ["Lang, Lea"] and [x[0] for x in fe.umleiten] == ["Neu, Nils"]
    assert [x[0] for x in fe.nach_stopp] == ["Miete, Mia"] and fe.stopp_ab == date(2030, 4, 6)
    assert fe.betroffen == 2 and fe.stufe == "ok" and fe.frei_im_haus > 2
    fs = rk.monatsfenster(st, f, 2032)
    assert rk.bester_monat(fs, date(2030, 1, 1)).stufe == "frei"


def test_pakete_budget_und_vormerken_mit_rueckgaengig(leer):
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import renovierung_kern as rk

    st = zp.laden()
    fl = rk.flure(st, date(2030, 1, 1))
    pk = {p.titel.split(":")[0]: p for p in rk.pakete(fl)}
    assert len(pk["Haus 2"].flure) == 1 and pk["Haus 2"].kosten[1] <= 100000
    assert len(pk["Haus 6"].flure) >= 2 and pk["Haus 6"].kosten[1] <= 100000
    assert rk.plan() == []
    rk.vormerken_schritt("2|3|Ost", date(2030, 7, 1), date(2030, 7, 30))
    j = rk.jahresuebersicht(zp.laden(), 2030)
    assert j[6]["flure"] == ["Haus 2 · 3. OG Ost"] and j[6]["kosten"] == (100000, 100000) and j[5]["zimmer"] == 0
    ok, _t = kern.rueckgaengig()
    assert ok and rk.plan() == []
    rk.parameter_schritt({**rk.parameter(), "budget": 50000, "gesperrt": [7, 8]})
    p = rk.parameter()
    assert p["budget"] == 50000 and rk.fenster(st, fl[0], date(2030, 7, 1), p).stufe == "gesperrt"
    assert not [x for x in rk.pakete(fl, p) if x.titel.startswith("Haus 2")]    # 100.000 € passen nicht in 50.000 €
