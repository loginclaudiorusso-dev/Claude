"""0.44: Klassen A/B/C (Bau/Möbel getrennt), Baubudget fest + Möbelantrag, beste Kombination, Herkunft und Spanne,
Einheitspreise aus dem Angebot, nicht prüfbare Monate, Kampagnen, Kernbestand, Strategien mit Alterung,
Entscheidungsvorlage mit Kurzfassung. Erfundene Daten und Beträge."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _p(rk, **mehr):
    p = rk.parameter()
    p["kosten"]["2"].update(bau_etage=90000, moebel_zimmer=1000, aufbau_zimmer=0)
    p["kosten"]["6"].update(bau_etage=18000, moebel_zimmer=1000, aufbau_zimmer=0)
    return {**p, "preisstand": 2031, "preis_pct": 0, "preis_moebel_pct": 0, "neben_pct": 0, "vorsteuer_pct": 100, **mehr}


def _zimmer(st, haus, etage, n=None):
    zs = [z for z in st.zimmer if z.haus == haus and z.etage == etage]
    return zs[:n] if n else zs


def test_klassen_bau_und_moebel_getrennt(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    z = SimpleNamespace(renoviert="", id="x")
    m = lambda art: SimpleNamespace(art=art, seit=date(2030, 1, 1), stufe=1)
    assert (rk.zimmer_bedarf(z, [m("renovierung")], date(2031, 1, 1), None).bau,
            rk.zimmer_bedarf(z, [m("renovierung")], date(2031, 1, 1), None).moebel) == ("A", "A")
    b = rk.zimmer_bedarf(z, [m("matratze")], date(2031, 1, 1), None)
    assert (b.bau, b.moebel, b.a) == (None, "A", True)
    b = rk.zimmer_bedarf(z, [m("wand")], date(2031, 1, 1), 4)
    assert (b.bau, b.moebel) == ("B", None)
    frisch = SimpleNamespace(renoviert="2029-06-01", id="y")
    b = rk.zimmer_bedarf(frisch, [m("wand"), m("moebel")], date(2031, 1, 1), 5)
    assert b.frisch and b.wert_bau == 0 and b.moebel == "A"                      # harte Regel: kein Bau, Möbel geht
    alt = SimpleNamespace(renoviert="2008-01-01", id="z")
    b = rk.zimmer_bedarf(alt, [], date(2031, 1, 1), None)
    assert (b.bau, b.moebel) == ("A", "B")                                        # ≥ 20 bzw. ≥ 15 Jahre
    assert rk.KLASSEN_WERT["A"] > 9 * rk.KLASSEN_WERT["B"]                        # erst alle A, dann B


def test_herkunft_spanne_und_angebotspreis(leer):
    from modern import renovierung_kern as rk

    p = rk.parameter()
    assert rk.herkunft(p, "2", "bau_etage") == "platzhalter" and p["puffer_bau_pct"] == 0 and p["modus"] == "budget"
    p = rk.angebot_uebernehmen(p, {"haus": "2", "art": "bau", "netto": 50000, "datum": "2031-02-01",
                                   "einheit_boden": 40, "einheit_wand": 15, "einheit_tuer": 200})
    assert rk.herkunft(p, "2", "bau_etage") == "angebot" and p["kosten"]["2"]["einheit_boden"] == 40
    k = rk.kosten(p, "2", 10, 2031)
    assert k.basis_brutto == pytest.approx(50000 * 1.19) and k.instandhaltung == pytest.approx(50000 * 1.19)
    von, bis = k.spanne_von("bau")
    assert von == pytest.approx(k.instandhaltung * .9) and bis == pytest.approx(k.instandhaltung * 1.1)
    p2 = rk.herkunft_merken(p, {**p, "kosten": {**p["kosten"], "6": {**p["kosten"]["6"], "moebel_zimmer": 1234}}})
    assert rk.herkunft(p2, "6", "moebel_zimmer") == "eingabe"
    assert rk.tsd(94_600) == "95 T€" and rk.spanne_text(90_000, 110_000) == "90 T€–110 T€"
    assert rk.angebote_alt(p, date(2032, 6, 1)) and not rk.angebote_alt(p, date(2031, 6, 1))


def test_einheitspreise_aus_positionen_und_einzelzimmer(leer):
    from modern import renovierung_kern as rk

    text = """Objekt: Musterbau, Gebäude 6, Etage 3
 01  100,00 m²  Boden Altbelag entfernen  5,00  500,00
 02  100,00 m²  Design-Bodenbelag liefern und verlegen  20,00  2.000,00
 03  300,00 m²  Decken- und Wandflächen streichen  5,00  1.500,00
 04  10,00 Stck  Türflächen beidseitig  100,00  1.000,00
 Nettosumme = EUR 5.000,00"""
    ang = rk.angebot_auswerten(text)
    assert ang["art"] == "bau" and ang["netto"] == 5000 and ang["haus"] == "6"
    assert (ang["einheit_boden"], ang["einheit_wand"], ang["einheit_tuer"]) == (25.0, 5.0, 100.0)
    p = rk.angebot_uebernehmen(rk.parameter(), {**ang, "datum": ""})
    p["kosten"]["6"].update(zimmer_boden_m2=12, zimmer_wand_m2=40, zimmer_tueren=1)
    je, hk, wie = rk.bau_je_einzelzimmer(p, "6", 9)
    assert je == 12 * 25 + 40 * 5 + 100 and hk == "angebot" and "Einheitspreise" in wie
    p["kosten"]["6"].update(zimmer_boden_m2=0)
    assert rk.bau_je_einzelzimmer(p, "6", 9)[1] == "schaetzung"                   # ohne Fläche: Schätzung


def test_baubudget_fest_moebel_als_antrag_beste_kombination(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    for z in _zimmer(st, "2", "3", 3):
        maengel.setzen(z.id, "renovierung", True, date(2029, 1, 1))
    for z in _zimmer(st, "6", "4"):
        maengel.setzen(z.id, "wand", True, date(2029, 1, 1))
    for z in _zimmer(st, "6", "5", 2):
        maengel.setzen(z.id, "matratze", True, date(2029, 1, 1))
    p = _p(rk, budget_bau=30000)
    fl = rk.flure(zp.laden(), date(2030, 1, 1), p)
    vs, empf = rk.varianten(fl, p, 2031)
    v = {x.schluessel: x for x in vs}
    assert empf == "kombi"
    for x in vs[:3]:
        assert x.kosten.instandhaltung <= 30000 + 1                               # Bau = harte Grenze
    kombi = v["kombi"]
    bau_ids = {z.id for m in kombi.massnahmen if m.art != "moebel" for z in m.zimmer}
    assert {z.id for z in _zimmer(st, "2", "3", 3)} <= bau_ids                  # Klasse A zuerst
    assert {z.id for z in _zimmer(st, "6", "4")} & bau_ids                      # dann B, so weit das Budget reicht
    assert any(m.art == "moebel" for m in kombi.massnahmen)                       # Möbel-A-Zimmer im Antrag
    ant = rk.moebelantrag(kombi)
    assert ant["summe"] == pytest.approx(kombi.kosten.investition) and ant["nur_moebel"] > 0
    assert kombi.wert >= max(v["etagen"].wert, v["zimmer"].wert)                 # Kombination ist nie schlechter
    assert "stabil" in rk.robustheit(fl, p, 2031, empf) or "Achtung" in rk.robustheit(fl, p, 2031, empf)
    # Etagen ohne erfassten Bedarf werden nicht gewählt, nur weil Geld übrig ist
    assert all(m.flur.wert > 0 for m in kombi.massnahmen if m.art == "etage")


def test_machbar_reserve_und_vorrang(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    for h, e in (("2", "3"), ("6", "4")):
        for z in _zimmer(st, h, e):
            maengel.setzen(z.id, "wand", True, date(2029, 1, 1))
    p = _p(rk, budget_bau=200000)
    fl = rk.flure(zp.laden(), date(2030, 1, 1), p)
    vs, _e = rk.varianten(fl, p, 2031, machbar={"6|4|"})
    assert {m.flur.schluessel for m in vs[0].massnahmen} == {"6|4|"}             # nicht machbare Etage fällt heraus
    vs, _e = rk.varianten(fl, p, 2031, reserve={"6|4|"})
    assert "6|4|" not in {m.flur.schluessel for x in vs for m in x.massnahmen}
    p6 = {**_p(rk, budget_bau=25000), "haus_vorrang": "6"}
    vs, e = rk.varianten(fl, p6, 2031)
    assert any(m.flur.haus == "6" for m in next(x for x in vs if x.schluessel == e).massnahmen)


def test_nicht_pruefbar_und_kampagnen(leer):
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    z1, z2, z3 = _zimmer(st, "2", "4", 3)
    for z in (z1, z2):                                                           # belegt bis Ende März
        st.lage.belegungen.setdefault(z.id, []).append(gebaeudeplan.Belegung(z.id, date(2030, 1, 1), date(2031, 3, 31),
                                                                              "belegt", "Muster, Max", "GS RVL"))
    rk._HORIZONT.clear()
    assert rk.buchungshorizont(st) == date(2030, 1, 1)
    f = next(x for x in rk.flure(st, date(2030, 1, 1)) if x.schluessel == "2|4|")
    assert not rk.fenster(st, f, date(2031, 6, 1)).pruefbar
    teile, ohne = rk.kampagnen(st, [z1, z2, z3], date(2031, 1, 1), date(2031, 12, 31), 3, [])
    starts = {a for _z, a, _b in teile}
    assert not ohne and len(teile) == 3 and len(starts) <= 2                    # gebündelt in höchstens 2 Kampagnen
    assert all(a.weekday() == 0 for a in starts) and all(a > date(2031, 3, 31) for z, a, _b in teile if z in (z1, z2))


def test_kernbestand_und_reserve_etagen(leer):
    from belegung import zimmerplan as zp
    from modern import auswertung_kern as ak
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    st = zp.laden()
    p = rk.parameter()
    fl = rk.flure(st, date(2030, 1, 1), p)
    gesamt = sum(z.betten for z in st.zimmer if z.aktiv and not z.gaeste)
    zeilen = [ak.PZeile(date(2031, m, 1), "prognose", 250.0, 240.0, 260.0, 230, 270, 200.0, None) for m in range(1, 13)]
    pg = ak.Prognose(zeilen, gesamt, "M", "Test", 1, 1, .8, [], [])
    k = sk.kernbestand(st, pg, fl, p, date(2030, 6, 1))
    assert k.spitze == 260 and k.kern == min(gesamt, int(-(-(260 + k.ausfall + 260 * .03 + 260 * .05) // 1)))
    assert k.reserve == gesamt - k.kern and k.reserve_betten <= k.reserve
    assert all(not f.sonderzimmer for f in k.etagen) and k.etagen
    kz = {x.titel: x for x in sk.kennzahlen(st, date(2030, 6, 1), fl, [], p, k)}
    assert "Kernbestand" in kz and "Strukturelle Reserve" in kz and "Offene Klasse-A-Zimmer" in kz
    assert sk.kernbestand(st, None, fl, p, date(2030, 6, 1)).hinweis


def test_strategien_mit_alterung(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    z = _zimmer(st, "6", "4")
    for x in z:
        x.renoviert = "2013-01-01"                                                # wird 2033 zu Klasse A (≥ 20 Jahre)
    p = _p(rk, budget_bau=60000)
    fl = rk.flure(st, date(2031, 1, 1), p)
    ss = {s.schluessel: s for s in rk.strategien(fl, p, 2031, date(2030, 11, 1), 5, {"2|6|"}, "x")}
    assert set(ss) == {"nichts", "empfohlen", "kuerzung", "schneller", "kern"}
    nichts = ss["nichts"]
    assert nichts.zimmer == 0 and nichts.a_ende > nichts.a_start                  # ohne Maßnahme wächst A
    assert ss["empfohlen"].a_ende < nichts.a_ende
    assert ss["schneller"].summe("bau") >= ss["empfohlen"].summe("bau") >= ss["kuerzung"].summe("bau")
    assert all(j["bau"] <= 60000 * 1.5 + 1 for j in ss["schneller"].jahre)
    assert "Klasse-A-Zimmer" in nichts.deutung


def test_entscheidungsvorlage_kurzfassung_und_anhang(leer):
    from belegung import maengel
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    st = zp.laden()
    for z in _zimmer(st, "6", "4"):
        maengel.setzen(z.id, "renovierung", True, date(2029, 1, 1))
    st = zp.laden()
    p = _p(rk, budget_bau=40000)
    fl = rk.flure(st, date(2030, 11, 1), p)
    vs, empf = rk.varianten(fl, p, 2031)
    v = next(x for x in vs if x.schluessel == empf)
    zeilen = rk.jahresplan(st, 2031, rk.vorschlaege_variante(st, fl, 2031, date(2030, 11, 1), p, None, v), p)
    html = sk.bericht_html({"standort": "Goslar", "heute": date(2030, 11, 1), "jahr": 2031, "p": p, "fl": fl, "kz": [],
                            "li": sk.Linie(), "guete": None, "varianten": vs, "empfehlung": empf, "empfohlen": empf,
                            "zeilen": zeilen, "strategien": rk.strategien(fl, p, 2031, date(2030, 11, 1), 5),
                            "entscheidungen": [], "luecken": [], "kern": None, "robust": "Empfehlung stabil."})
    for teil in ("Beschlussvorschlag", "Beträge 2031", "Möbel (Antrag)", "Wenn nicht", "Wenn −20 %", "Risiken",
                 "Nächste Schritte", "☐ Bau freigegeben", "Anhang", "A Varianten", "C Wie die Kosten zustande kommen",
                 "E Strategie 5 Jahre", "H Erläuterungen", "Ohne Beschluss bis"):
        assert teil in html, teil
    schritte = sk.naechste_schritte(zeilen, p, date(2030, 11, 1))
    assert schritte and schritte[0][1] == "Beschluss der Geschäftsführung"


def test_steuerung_ansichten_umbenannt():
    from modern import seite_steuerung as ss

    assert list(ss.ANSICHTEN.values()) == ["Übersicht", "Renovierung", "Strategie 5 Jahre", "Belegung", "Kennzahlen"]


def test_schaetzanteil_und_spanne_beim_zusammenrechnen(leer):
    from modern import renovierung_kern as rk

    p = rk.angebot_uebernehmen(rk.parameter(), {"haus": "6", "art": "bau", "netto": 20000, "datum": ""})
    a = rk.kosten(p, "6", 9, art="etage")                         # Bau aus Angebot, Möbel 0
    b = rk.kosten(p, "2", 20, art="etage")                        # Bau Platzhalter
    s = a.plus(b)
    assert 0 < s.geschaetzt < 1 and s.geschaetzt == pytest.approx((a.ungewiss + b.ungewiss) / s.summe) and a.ungewiss < a.summe
    assert s.spanne[1] - s.summe == pytest.approx(a.u_bau + a.u_moebel + b.u_bau + b.u_moebel)
