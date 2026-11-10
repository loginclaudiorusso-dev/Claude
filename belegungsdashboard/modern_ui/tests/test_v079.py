"""0.79 – Bestandsprognose: Kaplan-Meier, Übergänge, Simulation (wiederholbar), Kappe VW, Szenarien, Wenn-dann,
Rückblick-Test, Frühindikator. Alles mit erfundenen Daten."""

import random
from datetime import date, timedelta

import numpy as np

from modern import bestand_kern as bk
from modern import bestand_prognose as bp

L = date(2026, 11, 8)
T = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)


def test_kaplan_meier_zensiert():
    k = bp.km([10, 20, 20, 30, 40], [True, True, False, True, False])
    # 5 unter Risiko: t10 → 4/5; t20: 4 unter Risiko, 1 Ereignis → 0.6; t30: 2 unter Risiko → 0.3
    assert np.allclose(k.s, [0.8, 0.6, 0.3]) and list(k.tage) == [10, 20, 30]
    assert k.verbleib(5) == 1.0 and abs(k.verbleib(25) - .6) < 1e-9
    rng = np.random.default_rng(1)
    d = k.ziehen(np.full(2000, 25.0), rng)                # wer 25 Tage da ist: 50 % gehen bei 30, Rest bleibt
    assert np.all(d >= 26) and abs(np.mean(d == 30) - .5) < .05
    leer = bp.km([5, 9], [False, False])
    assert np.all(leer.ziehen(np.zeros(3), rng) == 10 ** 6)


def _daten(n=160, seed=3):
    """Erfundene Historie: Assessments, davon 60 % nach 2 Monaten in eine Hauptmaßnahme (24 Monate, 20 % vorzeitig)."""
    rnd = random.Random(seed)
    auf, p = [], 0
    for i in range(n):
        p += 1
        s = date(2022, 1, 1) + timedelta(days=rnd.randint(0, (L - date(2022, 1, 1)).days - 10))
        auf.append(bk.Aufenthalt(p, f"GS ASS PS {s:%y%m%d}", s, min(L, s + timedelta(days=41)), 42, 12, 0))
        if rnd.random() < .6:
            h = s + timedelta(days=60)
            if h > L:
                continue
            dauer = 730 if rnd.random() < .8 else rnd.randint(60, 500)
            auf.append(bk.Aufenthalt(p, f"GS CNC {h:%y%m}", h, min(L, h + timedelta(days=dauer - 1)), dauer, 0, 0))
    return auf


def _modell():
    fs = bp.faelle(_daten(), T, {}, L)
    return fs, bp.modell(fs, L, T)


def test_modell_uebergaenge_und_abgang():
    fs, md = _modell()
    u = md.uebergaenge["Assessment"]
    assert u.basis > 50 and .45 < u.quote < .75                     # ≈ 60 %
    assert abs(np.median(u.verzoegerung) - 60) < 1 and set(u.ziele) == {"Hauptmaßnahme CNC"}
    q = bp.abgangsquote(md, "Hauptmaßnahme CNC")
    assert q is not None and .05 < q < .4                           # ≈ 20 % vorzeitig
    assert md.raten["Assessment"].sum() > 0 and md.raten["Hauptmaßnahme CNC"].sum() < md.raten["Assessment"].sum()


def test_simulation_wiederholbar_und_plausibel():
    fs, md = _modell()
    a = bp.simulieren(md, 0, 300)
    b = bp.simulieren(md, 0, 300)
    assert np.array_equal(a.median, b.median)                       # fester Startwert
    z = a.zeile("Alle")
    heute = sum(1 for f in fs if f.ein <= L <= f.aus)
    assert abs(a.median[z, 0] - heute) <= 1
    assert np.all(a.p10[z] <= a.median[z]) and np.all(a.median[z] <= a.p90[z])
    bestand = a.zerlegung[0, z]
    assert bestand[0] >= bestand[-1]                                # der heutige Bestand schmilzt ab
    s = bp.simulieren(md, -50, 300)
    assert s.median[z, -1] < a.median[z, -1] and s.median[z, 1] <= a.median[z, 1]


def test_kappe_vw():
    fs = [bp.Fall(i, "GS VW 2506", "Hauptmaßnahme VW", "Hauptmaßnahme", date(2024, 6, 1) + timedelta(days=0),
                  date(2026, 5, 31), False, 730) for i in range(40)]           # 40 Zugänge im Juni 2024 → Rate ~13/Jahr
    fs += [bp.Fall(100 + i, "GS VW 2506", "Hauptmaßnahme VW", "Hauptmaßnahme", date(2025, 6, 1), date(2027, 5, 31), True, 730)
           for i in range(60)]
    md = bp.modell(fs, L, T)
    md.raten["Hauptmaßnahme VW"][5] = 40.0                                     # künstlich hohe Nachfrage im Juni
    e = bp.simulieren(md, 0, 200)
    assert e.ueber_kapazitaet.get("Hauptmaßnahme VW", 0) > 10                  # über 24 wird abgewiesen
    juni = next(i for i, d in enumerate(e.monate) if d.month == 7)
    assert e.zerlegung[3, e.zeile("Hauptmaßnahme VW"), juni] <= 24.5


def test_wenn_dann_und_fruehindikator():
    fs, md = _modell()
    basis = bp.simulieren(md, 0, 300)
    m = 6
    ziel = basis.median[-1, m] + 8
    w = bp.wenn_dann(md, m, ziel, None, 1000)                 # 0.86: bedingte Simulation statt Faktor-Suche
    assert abs(w.erreicht - ziel) <= 2 and w.verlauf[m][1] == w.erreicht
    w2 = bp.wenn_dann(md, m, 0, None, 1000)                                    # unter dem sicheren Bestand
    assert not w2.erreichbar and w2.sicher_im_monat > 0 and w2.anteil == 0
    sz, r, jetzt, vorher = bp.fruehindikator(fs, L)
    assert sz in ("schwach", "basis", "stark") and jetzt >= 0 and vorher >= 0


def test_rueckblick_und_szenarien():
    fs, _md = _modell()
    rb = bp.rueckblick(fs, L, T, monate=12, schritt=6, durchlaeufe=100)
    eins = next(x for x in rb if x.horizont == 1)
    assert eins.n >= 1 and eins.mae is not None and 0 <= eins.treffer80 <= 1
    s = bp.szenarien_lesen({"bestand_szenarien": {"schwach": {"faktor": "-30", "ausloeser": "Kürzung"},
                                                  "basis": {"faktor": 50}, "stark": {"faktor": "quatsch"}}})
    assert s["schwach"] == {"faktor": -30.0, "ausloeser": "Kürzung"} and s["basis"]["faktor"] == 0 and s["stark"]["faktor"] == 10


def test_oberflaeche_und_katalog():
    from modern import bestand_prognose_ui as bpu  # noqa: F401 – Import/Syntax der Ansichten
    from modern import kennzahlen_katalog as kk

    for k in ("planwert", "sicher", "abgangsquote", "uebergangsquote", "rueckblick"):
        assert kk.KATALOG[k].satz and kk.KATALOG[k].formel
    q = (bpu.__file__ and open(bpu.__file__, encoding="utf-8").read())
    assert "Plane mit" in q and "Wenn-dann" in q and "Frühindikator" in q
