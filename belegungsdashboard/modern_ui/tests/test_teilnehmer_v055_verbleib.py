"""0.55: Maßnahmen-Prognose ehrlicher – Verbleibskurve, Nachbuchung (Buchungsloch), Kurzkurs-Sockel, Rückwärtstest
ohne Blick in die Zukunft. Nur erfundene Kurse und Zahlen."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from modern import massnahmen_kern as mk


def _kurs(n: int, tage: int, abbruch: float = 0.0, nach: int = 0) -> list[int]:
    """n Personen; nach Tag 60 gehen bis Kursende ``abbruch`` (Anteil) gleichmäßig; ``nach`` kommen in Woche 2 dazu."""
    werte = []
    for a in range(tage):
        w = n + (nach if a >= 10 else 0)
        if a > 60:
            w = round(w * (1 - abbruch * (a - 60) / (tage - 60)))
        werte.append(w)
    return werte


def _roh(kurse: dict[str, tuple[date, list[int]]], von: date, bis: date) -> dict:
    return {"pivot": {"von": von.isoformat(), "bis": bis.isoformat(),
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}}}


# ---- Bausteine ---------------------------------------------------------------------------------------

def test_verbleib_kurve_und_faktor():
    ks = [mk.Kurs(f"GS AA {j}06", "GS AA", date(j, 6, 1), _kurs(20, 400, .3)) for j in (2022, 2023, 2024)]
    r = mk.verbleib_kurve(ks, "GS AA", date(2026, 1, 1))
    assert r and r[30] == pytest.approx(1.0) and r[390] < .75
    assert all(a >= b for a, b in zip(r[60:], r[61:]))                      # ab Tag 60 fallend
    assert mk.verbleib_faktor(r, 390, 10) == pytest.approx(r[390], abs=.01)
    assert mk.verbleib_faktor(r, 390, 300) > mk.verbleib_faktor(r, 390, 10)  # wer schon lange da ist, bleibt eher
    assert mk.verbleib_faktor(None, 390, 10) == 1.0


def test_verbleib_ohne_blick_in_die_zukunft():
    ks = [mk.Kurs("GS AA 2306", "GS AA", date(2023, 6, 1), _kurs(20, 400, .3)),
          mk.Kurs("GS AA 2406", "GS AA", date(2024, 6, 1), _kurs(20, 400, .3))]
    r = mk.verbleib_kurve(ks, "GS AA", date(2024, 9, 1))      # zweiter Kurs erst 3 Monate alt
    assert len(r) < 200                                       # danach nur ein Kurs bekannt → Kurve endet


def test_gebucht_am_mit_verbleib():
    alt = [mk.Kurs(f"GS AA {j}06", "GS AA", date(j, 6, 1), _kurs(20, 400, .3)) for j in (2022, 2023)]
    laufend = mk.Kurs("GS AA 2506", "GS AA", date(2025, 6, 1), [20] * 400)   # Pivot: voll bis Kursende
    st = date(2025, 8, 1)
    r = mk.verbleib_kurve(alt + [laufend], "GS AA", st)
    spaet = laufend.start + timedelta(days=390)
    assert mk.gebucht_am(laufend, spaet, st, r) < 16
    assert mk.gebucht_am(laufend, st, st, r) == 20                          # bis zum Stichtag: Ist
    assert mk.gebucht_am(laufend, spaet, st, None) == 20


def test_nachbuchung_poisson_gamma():
    # weit vor Start (p klein): die Vorjahre zählen
    assert mk.nachbuchung(0, 16, 0.02) == pytest.approx(16, abs=1)
    # kurz vor Start und erst 6 gebucht: kaum mehr als 6 (max(6, 16) hätte 16 gesagt)
    assert mk.nachbuchung(6, 16, 0.97) < 7
    # 14 gebucht bei p = 0,8: mehr als 14 und mehr als nur die Vorjahre
    assert mk.nachbuchung(14, 16, 0.8) > 16
    # Deckel: nie mehr als der größte Kurs der Vorjahre (oder das schon Gebuchte)
    assert mk.nachbuchung(14, 16, 0.3, deckel=18) == 18
    assert mk.nachbuchung(25, 16, 0.3, deckel=18) == 25
    assert mk.nachbuchung(9, 16, 1.0) == 9


def test_pickup_gemessen_oder_annahme():
    p = mk.pickup_kurve([])
    assert "Annahme" in p.quelle and p(0) == 1 and p(mk.PICKUP_HALB) == pytest.approx(.5)
    g = mk.pickup_kurve([5] * 20 + [40] * 20)
    assert "gemessen aus 40" in g.quelle
    assert g(10) == pytest.approx(.5) and g(3) == 1 and g(50) == 0


# ---- Prognose -----------------------------------------------------------------------------------------

def test_buchungsloch_teilgebuchter_kurs_bekommt_nachbuchung():
    st = date(2026, 5, 1)
    kurse = {f"GS AA {j - 2000}06": (date(j, 6, 1), _kurs(16, 300)) for j in (2023, 2024, 2025)}
    kurse["GS AA 2606"] = (date(2026, 6, 1), [6] * 300)                 # erst 6 gebucht, 31 Tage vor Start
    roh = _roh(kurse, date(2023, 1, 1), date(2027, 6, 1))
    neu = mk.erwartete_kurse(mk.kurse(roh), st, date(2027, 1, 1), daten_ab=date(2023, 1, 1))
    nb = [e for e in neu if e.herkunft == "Nachbuchung"]
    assert nb and nb[0].start == date(2026, 6, 1)
    gesamt = 6 + nb[0].spitze
    assert 6 < gesamt <= 16                                           # nicht nur 6 (Buchungsloch), aber nicht doppelt
    # kurz vor Start: fast nichts mehr nachgebucht
    neu2 = mk.erwartete_kurse(mk.kurse(roh), date(2026, 5, 30), date(2027, 1, 1), daten_ab=date(2023, 1, 1))
    nb2 = [e for e in neu2 if e.herkunft == "Nachbuchung"]
    assert not nb2 or nb2[0].spitze < nb[0].spitze


def test_kurzkurse_als_sockel():
    st = date(2026, 1, 1)
    kurse = {}
    for j in (2023, 2024, 2025):                                      # alle 2 Wochen ein 10-Tage-Kurs mit 5 Personen
        for i in range(26):
            s = date(j, 1, 5) + timedelta(days=14 * i)
            kurse[f"GS KZ {j}{i:02d}"] = (s, [5] * 10)
    roh = _roh(kurse, date(2023, 1, 1), date(2025, 12, 31))
    ks = mk.kurse(roh)
    neu = mk.erwartete_kurse(ks, st, date(2026, 12, 31), daten_ab=date(2023, 1, 1))
    s = [e for e in neu if e.familie == "GS KZ"]
    assert len(s) == 1 and s[0].herkunft == "Sockel"
    juni = mk._monatsmittel(lambda t: s[0].am(t), date(2026, 6, 1))
    ist = mk._monatsmittel(lambda t: sum(k.am(t) for k in ks), date(2025, 6, 1))
    assert juni == pytest.approx(ist, rel=.15)                        # nicht nur ein Drittel (±45-Tage-Raster)


def test_prognose_meldet_quelle_und_verbleib():
    st = date(2025, 9, 1)
    kurse = {f"GS AA {j - 2000}06": (date(j, 6, 1), _kurs(20, 500, .3)) for j in (2022, 2023, 2024)}
    kurse["GS AA 2506"] = (date(2025, 6, 1), [20] * 500)
    roh = _roh(kurse, date(2022, 1, 1), date(2026, 12, 31))
    p = mk.prognose(roh, st, 3, 18)
    assert "Annahme" in p.nachbuchung_quelle and p.mit_verbleib == 1
    p2 = mk.prognose(roh, st, 3, 18, vorlauf=[20] * 40)
    assert "gemessen" in p2.nachbuchung_quelle
    spaet = next(z for z in p.zeilen if z.monat == date(2026, 9, 1))
    assert spaet.gebucht < 18                                          # laufender Kurs mit Verbleib, nicht voll 20


def test_rueckwaertstest_ohne_blick_in_die_zukunft():
    kurse = {f"GS AA {j - 2000}06": (date(j, 6, 1), _kurs(20, 500, .3)) for j in (2020, 2021, 2022, 2023)}
    a = mk.rueckwaertstest(_roh(kurse, date(2020, 1, 1), date(2025, 12, 31)), [2024])[0]
    # der damals laufende Kurs bricht später völlig anders ab – die Prognose darf das nicht „wissen“
    w = _kurs(20, 500, .3)
    bis_st = (date(2023, 12, 31) - date(2023, 6, 1)).days
    kurse["GS AA 2306"] = (date(2023, 6, 1), w[:bis_st + 1] + [max(1, x // 4) for x in w[bis_st + 1:]])
    b = mk.rueckwaertstest(_roh(kurse, date(2020, 1, 1), date(2025, 12, 31)), [2024])[0]
    assert [p for _m, _i, p in a.monate] == pytest.approx([p for _m, _i, p in b.monate])
    assert [i for _m, i, _p in a.monate] != [i for _m, i, _p in b.monate]
    ohne = mk.rueckwaertstest(_roh(kurse, date(2020, 1, 1), date(2025, 12, 31)), [2024], verbleib=False)[0]
    assert sum(p for _m, _i, p in ohne.monate) > sum(p for _m, _i, p in b.monate)


def test_nachbuchung_nicht_als_naechster_kurs():
    st = date(2026, 5, 1)
    kurse = {f"GS AA {j - 2000}06": (date(j, 6, 1), _kurs(16, 300)) for j in (2023, 2024, 2025)}
    kurse["GS AA 2606"] = (date(2026, 6, 1), [6] * 300)
    p = mk.prognose(_roh(kurse, date(2023, 1, 1), date(2027, 6, 1)), st, 3, 12, familien={"GS AA"})
    z = next(f for f in p.familien if f.familie == "GS AA")
    assert z.naechster == date(2026, 6, 1) and z.naechster_wie == "gebucht"


# ---- Abtipp-Modus ---------------------------------------------------------------------------------------

def test_abtipp_felder():
    from modern import anreisen_kern as ank

    z = ank.EZeile("id:70012|GS-2-201|2026-12-01", "Erfunden, Erika", "GS VW 2612", "2-201",
                   date(2026, 12, 1), date(2028, 11, 30), False)
    assert z.tn_id == "70012"
    assert z.felder() == [("TN-ID", "70012"), ("Name", "Erfunden, Erika"), ("Zimmer", "2-201"), ("von", "01.12.2026"),
                          ("bis", "30.11.2028"), ("Maßnahme", "GS VW 2612")]
    ohne = ank.EZeile("name:erfunden, max|2026-12-01|GS-2-202|2026-12-01", "Erfunden, Max", "GS RVL", "2-202",
                      date(2026, 12, 1), date(2027, 2, 1), False)
    assert ohne.tn_id == "" and ohne.felder()[0] == ("Name", "Erfunden, Max")
