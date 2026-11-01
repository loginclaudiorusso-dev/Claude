"""0.41: Steuerung – Kostenmodell, Ausweichprüfung, Zimmerziel, Szenarien, Angebot einlesen, Prognosegüte,
Buchungsstände, Kennzahlen, Bericht. Erfundene Daten und Beträge."""

from datetime import date
from types import SimpleNamespace

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _belegung(zid, name, von, bis, art="belegt", massnahme="GS RVL"):
    from belegung import gebaeudeplan

    return gebaeudeplan.Belegung(zid, von, bis, art, name, massnahme)


def test_kostenmodell_steuer_puffer_preissteigerung(leer):
    from modern import renovierung_kern as rk

    p = {**rk.parameter(), "preisstand": 2030, "preis_pct": 10, "puffer_pct": 10, "neben_pct": 20, "vorsteuer_pct": 0,
         "kosten": {"6": {"bau_etage": 10000, "moebel_zimmer": 1000, "aufbau_zimmer": 100, "dauer_tage": 30}}}
    k = rk.kosten(p, "6", 2, 2030)
    assert (k.bau, k.neben, k.moebel, k.aufbau) == (10000, 2000, 2000, 200)
    assert round(k.puffer) == 1420 and round(k.netto) == 15620 and round(k.summe) == round(15620 * 1.19)
    assert round(k.instandhaltung + k.investition) == round(k.summe)
    assert round(rk.kosten(p, "6", 2, 2032).bau) == 12100                       # +10 % je Jahr
    assert rk.kosten({**p, "vorsteuer_pct": 100}, "6", 2, 2030).ust == 0          # voll abziehbar = netto
    assert rk.kosten({**p, "kosten": {"6": {"bau_etage": 0}}}, "6", 2).luecken    # fehlende Preise sind Lücken


def test_angebot_auswerten_und_uebernehmen(leer):
    from modern import renovierung_kern as rk

    bau = rk.angebot_auswerten("Objekt: Musterbau, Gebäude 6, Etage 3\nPos 01 ...\nNettosumme = EUR 12.345,67\n"
                               "Bruttosumme = EUR 14.691,35")
    assert bau == {"netto": 12345.67, "art": "bau", "haus": "6", "zimmer": 0}
    moebel = rk.angebot_auswerten("  4 Stück  Bettgestell  10,00 €\n  4 Stück Matratze\n  8 Stück Kopfteil\n"
                                  "Warenwert o. MwSt.   4.000,00 €")
    assert moebel["art"] == "moebel" and moebel["netto"] == 4000.0 and moebel["zimmer"] == 4
    p = rk.angebot_uebernehmen(rk.parameter(), {**moebel, "haus": "6", "datum": "2031-02-01", "datei": "x.pdf"})
    assert p["kosten"]["6"]["moebel_zimmer"] == 1000 and p["preisstand"] == 2031 and len(p["angebote"]) == 1
    p = rk.angebot_uebernehmen(p, {**bau, "datum": ""})
    assert p["kosten"]["6"]["bau_etage"] == 12345.67 and len(p["angebote"]) == 2
    with pytest.raises(ValueError):
        rk.angebot_uebernehmen(p, {**moebel, "haus": "6", "zimmer": 0})
    with pytest.raises(ValueError):
        rk.angebot_uebernehmen(p, {**bau, "haus": "99"})


def test_ausweich_je_zimmertyp_in_allen_haeusern(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    f = next(x for x in rk.flure(st, date(2030, 1, 1)) if x.schluessel == "2|4|")
    a = f.zimmer[0].id
    st.lage.belegungen.setdefault(a, []).append(_belegung(a, "Lang, Lea", date(2029, 6, 1), date(2031, 5, 31)))
    fe = rk.fenster(st, f, date(2030, 6, 1))
    assert fe.stufe == "ok" and sum(fe.ausweich.values()) == 1 and fe.frei_gesamt > fe.frei_im_haus
    # alles andere belegt → kein Ausweich
    ids = {z.id for z in f.zimmer}
    for z in st.zimmer:
        if z.id not in ids:
            st.lage.belegungen.setdefault(z.id, []).append(_belegung(z.id, "Voll, Vera", date(2030, 1, 1), date(2030, 12, 31)))
    fe = rk.fenster(st, f, date(2030, 6, 1))
    assert fe.stufe == "eng" and fe.ohne_ausweich and fe.ohne_ausweich[0][0] == "Lang, Lea"


def test_bester_monat_gleichwertig_ohne_klaren_abstand():
    from modern import renovierung_kern as rk

    def fe(m, prog):
        x = rk.Fenster(date(2031, m, 1), date(2031, m, 28), date(2030, 12, 1))
        x.prognose = prog
        return x
    knapp = [fe(m, (100 - m * .5, 90, 110)) for m in range(1, 7)]
    best = rk.bester_monat(knapp, date(2030, 1, 1))
    assert best.start.month == 1 and best.gleichwertig                        # Unterschied < halbe Spanne
    klar = [fe(1, (100, 98, 102)), fe(2, (60, 58, 62)), fe(3, (100, 98, 102))]
    best = rk.bester_monat(klar, date(2030, 1, 1))
    assert best.start.month == 2 and not best.gleichwertig


def test_ziel_szenarien_vorschlaege_jahresplan(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk

    st = zp.laden()
    p = rk.parameter()
    fl = rk.flure(st, date(2030, 1, 1), p)
    aw = rk.ziel_auswahl(fl, p, 2031, 30)
    assert len(aw) == 2 and aw[0].zimmer < 30 <= aw[1].zimmer                 # knapp darunter / knapp darüber
    sz = rk.szenarien(fl, p, 2031)
    assert [s.etagen for s in sz] == [1, 2, 3] and sz[0].jahre_bis_durch == len(fl)
    assert sz[0].zyklus == rk.zyklus(fl, sz[0].zimmer)
    vs = rk.vorschlaege(st, fl, 2031, date(2030, 1, 1), p, auswahl=aw[1])
    monate = [v.fenster.start.month for v in vs if v.fenster]
    assert len(monate) == len(set(monate)) == len(aw[1].flure)                # keine zwei Baustellen im selben Monat
    zeilen = rk.jahresplan(st, 2031, vs, p)
    assert all(z.status == "vorschlag" for z in zeilen)
    assert rk.gesperrte_betten(zeilen, date(2031, monate[0], 1)) > 0
    rk.vormerken_mehrere_schritt([(v.flur.schluessel, v.fenster.start, v.fenster.ende) for v in vs])
    assert len(rk.plan()) == len(vs) and all(z.status == "vorgemerkt" for z in rk.jahresplan(st, 2031, None, p))
    assert rk.vorschlaege(st, fl, 2031, date(2030, 1, 1), p, auswahl=aw[1]) == []    # schon vorgemerkt


def _pg(rueck):
    from modern import auswertung_kern as ak

    zeilen = [ak.PZeile(date(2030, m, 1), "ist", 100.0, 0, 0, 0, 0, None, 100.0) for m in range(1, 13)]
    zeilen += [ak.PZeile(date(2031, m, 1), "prognose", 108.0, 100.0, 112.0, 95, 125, 80.0, None) for m in range(1, 13)]
    return ak.Prognose(zeilen, 120, "M", "Test", 2.0, 4.0, .8, [], rueck)


def test_guete_trennt_spanne_und_pruefung():
    from modern import steuerung_kern as sk

    rueck = [(date(2028, 1, 1) + __import__("datetime").timedelta(days=31 * i), 100.0, 100.0 + (i % 5)) for i in range(18)]
    g = sk.guete(_pg(rueck))
    assert g.n == 18 and g.test_n == 6 and g.k80 is not None and "±" in g.satz and "unabhängige" in g.hinweis.lower()
    assert sk.guete(_pg([])).mae is None


def test_buchungsstand_einmal_je_monat_und_linie(leer):
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    pg = _pg([])
    assert sk.buchungsstand_merken(pg, date(2030, 12, 5)) and not sk.buchungsstand_merken(pg, date(2030, 12, 20))
    assert sk.buchungsstaende()["2030-12"]["monate"]["2031-01"] == 80.0
    z = rk.PlanZeile("6|3|", "Haus 6 · 3. OG", 9, 9, date(2031, 3, 1), date(2031, 3, 31), date(2031, 1, 4), "vorgemerkt",
                     rk.Kosten(9, 2031))
    li = sk.linie(pg, [z], 12, 12)
    i = li.monate.index(date(2031, 3, 1))
    assert li.kapazitaet[i] == 111 and li.kapazitaet[i - 1] == 120 and li.vorjahr[i] == 100.0
    assert sk.warnmonate(li) == [date(2031, 3, 1)]                             # 112 ≥ 95 % von 111, aber < 95 % von 120
    html = sk.bericht_html({"standort": "Goslar", "heute": date(2030, 12, 5), "jahr": 2031, "p": rk.parameter(),
                            "kz": [sk.Kennzahl("A", "1")], "li": li, "guete": sk.guete(pg), "zeilen": [z],
                            "entscheidungen": ["Etwas entscheiden"]})
    assert "<svg" in html and "Etwas entscheiden" in html and "Haus 6 · 3. OG" in html


def test_kennzahlen_aus_vorhandenen_daten(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk
    from modern import steuerung_kern as sk

    st = zp.laden()
    z = st.zimmer[0]
    st.lage.belegungen.setdefault(z.id, []).append(_belegung(z.id, "Muster, Max", date(2030, 1, 1), date(2030, 12, 31)))
    p = rk.parameter()
    kz = {k.titel: k for k in sk.kennzahlen(st, date(2030, 6, 1), rk.flure(st, date(2030, 6, 1), p), [], p)}
    assert kz["Verfügbare Betten heute"].wert == str(sum(x.betten for x in st.zimmer if x.aktiv))
    assert "100 %" in kz["Belegtage je Gruppe (12 Monate)"].unter
    assert "Zimmer innerhalb des Zyklus" in kz and sk.luecken()


def test_navigation_steuerung_unten_und_zimmer_ohne_renovierung():
    from modern import register, seite_zimmer

    assert register.NAV[-1][0] == "steuerung" and "steuerung" in register.SEITEN
    assert {g for *_x, g in register.NAV} >= {"Betrieb", "Leitung"} and "Täglich" not in {g for *_x, g in register.NAV}
    assert "renovierung" not in seite_zimmer.ANSICHTEN
    assert seite_zimmer._ansicht(SimpleNamespace(ansicht_von=lambda s, d: "renovierung")) == "uebersicht"
