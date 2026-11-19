"""1.16 – Cockpit (neu): Karten an/ab, Monat schieben, Bewertung (Budget, Möbel, Reserve, Umzüge), Übernehmen."""

import calendar
from datetime import date

from modern import cockpit_kern as ck
from modern import renovierung_kern as rk


def _kosten(bau, moebel):
    k = rk.Kosten(4, 2027, bau=bau, moebel=moebel, herkunft_bau="angebot", herkunft_moebel="eingabe")
    return k._unsicherheit()


def _karte(schl, betten, bau, moebel, monat=3, art="etage", umzuege=None, bau_kl=(0, 1, 0)):
    start = date(2027, monat, 1)
    ende = date(2027, monat, calendar.monthrange(2027, monat)[1])        # ganzer Monat (Baustellen zählen anteilig je Tag)
    z = rk.PlanZeile(f"F{schl}", f"Flur {schl}", 4, betten, start, ende, date(2027, monat - 1 or 1, 1),
                     "vorschlag", _kosten(bau, moebel), art=art)
    k = ck.Karte(schl, f"Flur {schl}", art, f"F{schl}", "2", ["a", "b"], betten, z.kosten, bau_kl, (0, 0, 0), False, z)
    if art == "etage":
        for m in range(1, 13):
            k.monate[m] = ck.Monat(m != 8, (umzuege or {}).get(m, 0), 0, "gesperrt" if m == 8 else "")
    return k


def _bedarf():
    return ck.Bedarf([date(2027, m, 1) for m in range(1, 13)], [80] * 12, [90] * 12, [100] * 12, [False] * 12, 120, 5)


def test_haken_und_monat_wirken_sofort():
    a, b = _karte("a", 10, 50000, 8000, 3, umzuege={3: 4, 5: 1}), _karte("b", 12, 20000, 5000, 6)
    bd = _bedarf()
    bw = ck.bewerten([a, b], {"a": 3, "b": 6}, bd, 100000, 7000, [])
    assert round(bw.bau) == round(a.kosten.instandhaltung + b.kosten.instandhaltung)
    assert bw.verplant == bw.bau + 7000 and bw.rest == 100000 - bw.verplant
    assert round(bw.moebel) == round(a.kosten.investition + b.kosten.investition) and bw.moebel_zimmer == 4
    assert bw.reserve[2] == 120 - 5 - 10 - 100 and bw.reserve[5] == 120 - 5 - 12 - 100 and bw.reserve[0] == 15
    assert bw.knappster == 5 and bw.umzuege == 4
    bw2 = ck.bewerten([a, b], {"a": 5}, bd, 100000, 0, [])           # b abgehakt, a in den Mai geschoben
    assert bw2.reserve[2] == 15 and bw2.reserve[4] == 5 and bw2.umzuege == 1 and bw2.knappster == 4
    assert bw2.bau < bw.bau


def test_engpass_und_nicht_moeglicher_monat():
    a = _karte("a", 30, 1000, 0, 3)
    bw = ck.bewerten([a], {"a": 8}, _bedarf(), None, 0, [])
    assert bw.engpaesse == [7] and bw.reserve[7] == -15
    assert any("nicht möglich" in h for h in bw.hinweise)              # August gesperrt
    assert ck.wirkung_text(a, 8, bw) == ("im Aug fehlen 15 Betten", "krit")


def test_monat_schieben_behaelt_dauer_und_vorlauf():
    a = _karte("a", 10, 1000, 0, 3)
    z = a.zeile_im(9)
    assert z.start == date(2027, 9, 1) and (z.ende - z.start) == (a.zeile.ende - a.zeile.start)
    assert (z.start - z.stopp_ab) == (a.zeile.start - a.zeile.stopp_ab)
    k = _karte("k", 2, 1000, 0, 3, art="zimmer")
    assert not k.schiebbar and k.zeile_im(9) is k.zeile                 # Kampagne: Termin bleibt


def test_standard_auswahl_und_eintraege():
    a, b = _karte("a", 10, 1, 0, 4), _karte("b", 10, 1, 0, 6)
    b.vorschlag = False
    assert ck.standard_auswahl([a, b]) == {"a": 4}
    b.vorgemerkt = True                                                  # sobald vorgemerkt: nur das Vorgemerkte
    assert ck.standard_auswahl([a, b]) == {"b": 6}
    assert ck.eintraege(a, 7) == [("Fa", date(2027, 7, 1), date(2027, 7, 30))]   # April: 30 Tage, Dauer bleibt


def test_uebernehmen(monkeypatch):
    rufe = []
    monkeypatch.setattr(rk, "vormerken", lambda *x: rufe.append(("+",) + x))
    monkeypatch.setattr(rk, "entfernen", lambda *x: rufe.append(("-",) + x))
    neu, alt, weg = _karte("n", 5, 1, 0, 4), _karte("v", 5, 1, 0, 5), _karte("w", 5, 1, 0, 6)
    alt.vorgemerkt = weg.vorgemerkt = True
    txt = ck.uebernehmen([neu, alt, weg], {"n": 4, "v": 9})               # v verschoben, w abgehakt
    assert ("-", "Fv", "2027-05-01", "etage") in rufe and ("-", "Fw", "2027-06-01", "etage") in rufe
    assert ("+", "Fn", date(2027, 4, 1), date(2027, 4, 30), "", "etage", None) in rufe
    assert ("+", "Fv", date(2027, 9, 1), date(2027, 10, 1), "", "etage", None) in rufe   # Dauer bleibt: 31 Tage wie im Mai
    assert "2 vorgemerkt" in txt and "2 entfernt" in txt


def test_diagramm_bleibt_bilanz():
    a = _karte("a", 30, 1000, 0, 3)
    o = ck.diagramm(_bedarf(), ck.bewerten([a], {"a": 3}, _bedarf(), None, 0, []))
    assert all(s.get("m_fest") for s in o["series"])                    # Diagrammtyp stellt es nicht um
    eng = next(s for s in o["series"] if s["name"] == "Engpass")
    assert eng["data"][2] == 15 and eng["data"][0] is None
    from modern import diagramm_stil as ds

    assert ds.anwenden(o, {"dg_typ": "linie"})["series"][4]["type"] == "bar"
