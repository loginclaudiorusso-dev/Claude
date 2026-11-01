"""0.43: Einzelzimmer (komplett / nur Möbel), Varianten mit Empfehlung, Kostenherleitung, Szenarien über 5 Jahre,
Werte für Kennzahlen, Zustandsnoten, Entscheidungsvorlage, Engpass-Einzelheiten. Erfundene Daten und Beträge."""

from datetime import date, timedelta

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
            "einzel_aufschlag_pct": 25,
            "kosten": {"2": {"bau_etage": 90000, "bau_zimmer": 0, "moebel_zimmer": 1000, "aufbau_zimmer": 200, "dauer_tage": 30},
                       "6": {"bau_etage": 18000, "bau_zimmer": 0, "moebel_zimmer": 1000, "aufbau_zimmer": 200, "dauer_tage": 30}},
            **mehr}


def _bedarf(zp, maengel, zimmer):
    for z in zimmer:
        maengel.setzen(z.id, "renovierung", True, date(2029, 1, 1))


def test_kosten_einzelzimmer_und_nur_moebel_mit_herleitung(leer):
    from modern import renovierung_kern as rk

    p = _p(rk)
    z = rk.kosten(p, "6", 2, 2031, "zimmer", 9)
    assert round(z.bau) == round(18000 / 9 * 1.25 * 2) and z.moebel == 2000 and z.aufbau == 400
    m = rk.kosten(p, "6", 3, 2031, "moebel")
    assert m.bau == 0 and m.moebel == 3000 and m.instandhaltung == 0 and not any("Baukosten" in l for l in m.luecken)
    e = rk.kosten(p, "6", 9, 2031)
    texte = [t for t, _b in e.herleitung]
    assert texte[0].startswith("Angebot/Annahme Bau") and any("Möbel" in t for t in texte) and any("Umsatzsteuer" in t for t in texte)
    p2 = {**p, "kosten": {**p["kosten"], "6": {**p["kosten"]["6"], "bau_zimmer": 2500}}}
    assert rk.kosten(p2, "6", 1, 2031, "zimmer", 9).bau == 2500                    # eigener Preis geht vor


def test_varianten_kombi_und_empfehlung(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    h2 = [z for z in st.zimmer if z.haus == "2" and z.etage == "3"][:3]
    _bedarf(zp, maengel, h2)
    p = _p(rk, modus="budget", budget_bau=40000, budget_moebel=15000)
    fl = rk.flure(zp.laden(), date(2030, 1, 1), p)
    vs, empf = rk.varianten(fl, p, 2031)
    v = {x.schluessel: x for x in vs}
    assert set(v) == {"etagen", "kombi", "zimmer", "moebel"}
    assert v["kombi"].zimmer >= v["etagen"].zimmer and v["kombi"].punkte >= v["etagen"].punkte
    for x in vs:                                                                     # alle im Budget
        assert x.kosten.instandhaltung <= 40000 + 1 and x.kosten.investition <= 15000 + 1
    assert {z.id for m in v["zimmer"].massnahmen for z in m.zimmer} == {z.id for z in h2}
    assert abs(v["moebel"].punkte - v["zimmer"].punkte / 2) < .1                     # nur Möbel deckt die Hälfte
    assert empf in ("zimmer", "kombi") and v[empf].punkte == max(x.punkte for x in vs)


def test_einzelzimmer_termine_vormerken_und_entfernen(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import renovierung_kern as rk

    st = zp.laden()
    h2 = [z for z in st.zimmer if z.haus == "2" and z.etage == "4"][:2]
    _bedarf(zp, maengel, h2)
    st = zp.laden()
    p = _p(rk, modus="budget", budget_bau=0, budget_moebel=5000)
    fl = rk.flure(st, date(2030, 1, 1), p)
    vs, _e = rk.varianten(fl, p, 2031)
    moebel = next(x for x in vs if x.schluessel == "moebel")
    vor = rk.vorschlaege_variante(st, fl, 2031, date(2030, 1, 1), p, None, moebel)
    teile = [t for v in vor for t in v.teile]
    assert len(teile) == 2 and all((b - a).days + 1 == p["moebel_tage"] for _z, a, b in teile)
    zeilen = rk.jahresplan(st, 2031, vor, p)
    assert len(zeilen) == 1 and zeilen[0].art == "moebel" and zeilen[0].zimmer == 2 and len(zeilen[0].teile) == 2
    assert rk.gesperrte_betten(zeilen, date(2031, teile[0][1].month, 1)) > 0
    rk.vormerken_mehrere_schritt([(v.flur.schluessel, a, b, v.art, [z.id]) for v in vor for z, a, b in v.teile])
    plan = rk.plan()
    assert len(plan) == 2 and all(e["art"] == "moebel" and len(e["zimmer"]) == 1 for e in plan)
    z = rk.jahresplan(st, 2031, None, p)[0]
    assert z.status == "vorgemerkt" and z.zimmer == 2
    rk.entfernen_mehrere_schritt([(z.flur, t[2].isoformat(), z.art) for t in z.teile])
    assert rk.plan() == []
    ok, _t = kern.rueckgaengig()
    assert ok and len(rk.plan()) == 2


def test_szenarien_mehrjaehrig(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    p = _p(rk, preis_pct=10)
    fl = rk.flure(st, date(2030, 1, 1), p)
    st_ = {s.schluessel: s for s in rk.szenarien_mehrjahr(fl, p, 2031, 5)}
    assert set(st_) == {"eingestellt", "etage1", "etage2", "moebel", "warten"}
    assert all(len(s.jahre) == 5 for s in st_.values())
    assert st_["etage2"].zimmer > st_["etage1"].zimmer > st_["warten"].zimmer
    assert st_["warten"].jahre[0]["zimmer"] == 0 and "Aufschieben" in st_["warten"].erklaerung
    e1 = st_["etage1"]
    assert e1.jahre[1]["bau"] > 0 and e1.zyklus and "Jahren" in e1.deutung
    assert st_["moebel"].summe("bau") == 0                                        # nur Möbel: kein Bau
    ids = [z.id for f in fl for z in f.zimmer]
    assert st_["etage2"].zimmer <= len(set(ids))                                  # nichts doppelt


def test_werte_und_zustandsnoten_fliessen_ein(leer):
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    st = zp.laden()
    z = st.zimmer[0]
    st.lage.belegungen.setdefault(z.id, []).append(gebaeudeplan.Belegung(z.id, date(2030, 1, 1), date(2030, 12, 31), "belegt",
                                                                          "Muster, Max", "GS RVL"))
    sk.werte_schritt({"tagessaetze": {"RVL": 100}, "abweisungen": {"2030-05": 3}})
    w = sk.werte()
    assert w["tagessaetze"] == {"RVL": 100.0} and w["abweisungen"] == {"2030-05": 3}
    p = rk.parameter()
    kz = {k.titel: k for k in sk.kennzahlen(st, date(2030, 6, 1), rk.flure(st, date(2030, 6, 1), p), [], p)}
    assert kz["Erlös (12 Monate)"].wert == f"{152 * 100:,} €".replace(",", ".")
    assert kz["Abweisungen (12 Monate)"].wert == "3" and "Leerstandskosten (12 Monate, Schätzung)" in kz
    f = rk.flure(st, date(2030, 6, 1), p)[-1]
    rk.zustand_schritt({f.schluessel: 5})
    f2 = next(x for x in rk.flure(st, date(2030, 6, 1), p) if x.schluessel == f.schluessel)
    assert f2.zustand == 5 and f2.bedarf == 40 and any("Zustandsnote 5" in t for _p, t in f2.gruende)
    assert not [l for l in sk.luecken() if l[0].startswith(("Erlös", "Abweisungen", "Zustandsnote"))]


def test_entscheidungsvorlage_mit_erklaerungen(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    st = zp.laden()
    p = _p(rk, modus="budget", budget_bau=50000, budget_moebel=20000)
    fl = rk.flure(st, date(2030, 1, 1), p)
    vs, empf = rk.varianten(fl, p, 2031)
    v = next(x for x in vs if x.schluessel == empf)
    zeilen = rk.jahresplan(st, 2031, rk.vorschlaege_variante(st, fl, 2031, date(2030, 1, 1), p, None, v), p)
    html = sk.bericht_html({"standort": "Goslar", "heute": date(2030, 11, 1), "jahr": 2031, "p": p, "kz": [], "li": sk.Linie(),
                            "guete": None, "varianten": vs, "empfehlung": empf, "zeilen": zeilen,
                            "strategien": rk.szenarien_mehrjahr(fl, p, 2031, 5), "entscheidungen": ["X"], "luecken": []})
    for teil in ("Entscheidungsvorlage", "Empfehlung und Beschluss", "☐ Zustimmung", "Die Varianten im Vergleich",
                 "Wie die Kosten zustande kommen", "Szenarien über 5 Jahre", "Begriffe", "So zu lesen"):
        assert teil in html, teil
    assert "Angebot/Annahme Bau" in html


def test_engpass_einzelheiten_je_woche(leer):
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import seiten_kern as sk

    st = zp.laden()
    h = date(2030, 3, 4)
    emr = [z for z in st.zimmer if z.aktiv and not z.gaeste and zp.erlaubt(z, "EMR")]
    st.lage.belegungen.setdefault(emr[0].id, []).append(gebaeudeplan.Belegung(emr[0].id, h, h + timedelta(days=30), "belegt",
                                                                               "Muster, Mia", "GS EMR"))
    aw = sk.auswertung(st, h, 2)
    assert aw.wochen[0].montag == h and aw.lage is not None
    d = sk.engpass_detail(st, aw.lage, h, "emr", h)
    assert len(d["tage"]) == 7 and all(n == len(emr) - 1 for _t, n in d["tage"])
    belegt = [z for z in d["zimmer"] if z.frei_tage == 0]
    assert belegt and belegt[0].wer[0][0] and not belegt[0].wer[0][3]              # echte Belegung, nicht probeweise
