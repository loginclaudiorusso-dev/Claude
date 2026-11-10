"""0.86 – Prognose nach der Challenge: Verbleibskurve nur mit beobachteten Tagen und nur vorzeitigen Abgängen,
geplantes Ende in der Simulation, keine Doppelzählung bekannter Eintritte, gemeinsamer Jahresfaktor, Frühindikator
mit Zufallsprüfung, Rückblick monatlich mit „Bestand bleibt“, Wenn-dann als bedingte Simulation, Archiv der Stände.
Alles mit erfundenen Daten."""

import random
from datetime import date, timedelta

import numpy as np

from modern import bestand_kern as bk
from modern import bestand_prognose as bp

L = date(2026, 11, 8)
T = bk.tabelle_bereinigen([{"muster": "GS CNC", "art": "Hauptmaßnahme CNC", "gruppe": "Hauptmaßnahme", "soll_tage": 730},
                           {"muster": "GS ASS", "art": "Assessment", "gruppe": "Assessment", "soll_tage": 42}])


def _cnc(n=400, abbruch=.20, seed=7):
    """Gestaffelte Eintritte über 5 Jahre, 730 Tage geplant, 20 % gehen vorzeitig (60–600 Tage). Der Pivot zeigt bei
    Laufenden die geplanten Tage bis zum Ende – auch in der Zukunft; einige Eintritte liegen ganz in der Zukunft."""
    rnd = random.Random(seed)
    auf = []
    for p in range(1, n + 1):
        ein = date(2021, 11, 1) + timedelta(days=rnd.randint(0, (L - date(2021, 11, 1)).days + 60))
        plan_ende = ein + timedelta(days=729)
        ende = plan_ende
        if rnd.random() < abbruch:
            austritt = ein + timedelta(days=rnd.randint(60, 600))
            if austritt <= L:                   # schon passiert – im Pivot sichtbar; sonst steht noch der Plan drin
                ende = austritt
        auf.append(bk.Aufenthalt(p, f"GS CNC {ein:%y%m}", ein, ende, (ende - ein).days + 1, 0, 0))
    return auf


def test_kurve_trifft_bekannte_abbruchquote():
    fs = bp.faelle(_cnc(), T, {}, L)
    assert any(f.geplant for f in fs) and any(f.ein > L for f in fs)
    md = bp.modell(fs, L, T)
    neu = bp.abgangsquote(md, "Hauptmaßnahme CNC")
    alt = md.abgang_alt["Hauptmaßnahme CNC"]
    assert .14 < neu < .26, neu                     # wahr: 20 %
    assert alt < neu - .03, (alt, neu)              # die bisherige Rechnung lag systematisch zu niedrig


def test_beobachtete_tage_und_vorzeitig():
    f = bp.Fall(1, "GS CNC 2601", "Hauptmaßnahme CNC", "Hauptmaßnahme", date(2026, 1, 1), date(2027, 12, 31), True, 730,
                date(2027, 12, 31))
    assert f.dauer == 730 and f.beobachtet(L) == (L - date(2026, 1, 1)).days + 1 and not f.vorzeitig(730)
    g = bp.Fall(2, "GS CNC 2401", "Hauptmaßnahme CNC", "Hauptmaßnahme", date(2024, 1, 1), date(2025, 12, 20), False, 730)
    assert not g.vorzeitig(730)                     # 11 Tage vor dem Soll-Ende = regulär
    h = bp.Fall(3, "GS CNC 2401", "Hauptmaßnahme CNC", "Hauptmaßnahme", date(2024, 1, 1), date(2024, 6, 1), False, 730)
    assert h.vorzeitig(730) and bp.Fall(4, "X", "a", "b", L, L, False, None).vorzeitig(None)


def test_geplantes_ende_wird_genutzt():
    f = bp.Fall(1, "GS CNC 2601", "Hauptmaßnahme CNC", "Hauptmaßnahme", date(2025, 1, 1), L + timedelta(days=60), True,
                730, L + timedelta(days=60))
    md = bp.modell([f], L, T)                       # Kurve ohne Ereignis: früher blieb der Fall „für immer“
    e = bp.simulieren(md, 0, 50, horizont=6)
    assert e.median[-1, 1] == 1 and e.median[-1, 3] == 0 and e.median[-1, 6] == 0


def _ass_modell(extra=()):
    rnd = random.Random(5)
    auf = []
    for p in range(1, 200):
        ein = date(2023, 1, 1) + timedelta(days=rnd.randint(0, (L - date(2023, 1, 1)).days))
        auf.append(bk.Aufenthalt(p, f"GS ASS PS {ein:%y%m%d}", ein, min(L, ein + timedelta(days=41)), 42, 0, 0))
    auf += list(extra)
    fs = bp.faelle(auf, T, {}, L)
    return bp.modell(fs, L, T)


def test_bekannte_eintritte_nicht_doppelt():
    k = 2
    start = bp.messtage(L)[k - 1] + timedelta(days=3)
    extra = [bk.Aufenthalt(900 + i, f"GS ASS PS {start:%y%m%d}", start, start + timedelta(days=41), 42, 0, 0) for i in range(4)]
    ohne, mit = _ass_modell(), _ass_modell(extra)
    assert np.allclose(ohne.raten["Assessment"], mit.raten["Assessment"])     # Erfahrungsrate unverändert
    e0, e1 = bp.simulieren(ohne, 0, 600), bp.simulieren(mit, 0, 600)
    z = e0.zeile("Assessment")
    weitere0, weitere1 = e0.zerlegung[3, z, k], e1.zerlegung[3, z, k]
    assert weitere0 - weitere1 > 1.0, (weitere0, weitere1)
    gesamt_plus = e1.median[z, k] - e0.median[z, k]
    assert gesamt_plus < 4                          # vorher: + 4 obendrauf


def test_jahresfaktor_macht_spanne_breiter(monkeypatch):
    md = _ass_modell()
    breit = bp.simulieren(md, 0, 800)
    monkeypatch.setattr(bp, "JAHR_STREUUNG", 0.0)
    schmal = bp.simulieren(md, 0, 800)
    z = breit.zeile(None)
    assert (breit.p90[z, 12] - breit.p10[z, 12]) > (schmal.p90[z, 12] - schmal.p10[z, 12])


def test_fruehindikator_zufall():
    assert not bp.ueber_zufall(25, 25) and not bp.ueber_zufall(18, 25) and bp.ueber_zufall(10, 30)
    ein = [L - timedelta(days=10 + i) for i in range(20)] + [L - timedelta(days=375 + i) for i in range(23)]
    fs = [bp.Fall(i, "GS ASS", "Assessment", "Assessment", d, d + timedelta(days=41), False, 42) for i, d in enumerate(ein)]
    sz, r, jetzt, vorher = bp.fruehindikator(fs, L)
    assert (jetzt, vorher) == (20, 23) and r < .9 and sz == "basis"          # früher: „schwach“


def test_rueckblick_monatlich_mit_vergleich():
    fs = bp.faelle(_cnc(150), T, {}, L)
    rb = bp.rueckblick(fs, L, T, monate=6, durchlaeufe=60)
    eins = next(x for x in rb if x.horizont == 1)
    assert eins.n >= 5 and eins.mae_bleibt is not None and 0 <= eins.treffer <= eins.n


def test_wenn_dann_ausserhalb():
    md = _ass_modell()
    w = bp.wenn_dann(md, 3, 10_000, None, 400)
    assert not w.erreichbar and w.spanne[1] < 10_000 and w.anteil == 0


def test_archiv(tmp_path, monkeypatch):
    from belegung import speicher

    from modern import massnahmen_kern as mk

    monkeypatch.setattr(speicher, "pfad", lambda name, ordner=None: tmp_path / name)
    for _ in range(2):
        assert mk.archivieren({"bis": "2026-11-01"}, [[1, "GS CNC 2601", "2026-01-01", "2026-11-01", 300, 80, 0, 0]])
    assert len(mk.archiv_staende()) == 1                                      # ein Stand je Tag
    monkeypatch.setattr(mk, "ARCHIV_MAX", 1)
    (tmp_path / mk.ARCHIV_ORDNER / "bestand_2020-01-01.json").write_text("{}", encoding="utf-8")
    mk.archivieren({}, [])
    assert len(mk.archiv_staende()) == 1


# ---- Oberfläche --------------------------------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

MOD = Path(__file__).resolve().parent.parent / "modern"


def _q(name):
    return (MOD / name).read_text(encoding="utf-8")


def test_namen_und_querverweise():
    assert '"prognose": "Belegungs\\u00adprognose"' in _q("seite_auswertung.py")
    assert '"prognose": "Teilnehmer-Prognose"' in _q("seite_massnahmen.py")
    assert 'a.oeffnen("auswertung", ansicht="prognose")' in _q("bestand_prognose_ui.py")
    assert 'ansicht="massnahmen", mn_ansicht="prognose"' in _q("seite_prognose.py")
    assert "schon da oder angemeldet" in _q("bestand_prognose_ui.py") and '"Davon bekannt"' in _q("kennzahlen_katalog.py")


def test_belegungsprognose_band_nur_12_monate():
    q = _q("seite_prognose.py")
    assert 'band("lo80"), band("hi80")' in q and "i >= fort_ab" in q and '36: "36M"' not in q
    assert "self.aw_95, self.aw_backtest = False, False" in _q("oberflaeche.py")


def test_besen_fuehrt_zur_liste_und_kachel_mit_bett_segmenten():
    z = _q("seite_zimmer.py")
    assert 'besen.on("click.stop"' in z and 'rg_zeitraum="offen", rg_filter="offen", rg_zimmer=k.zimmer' in z
    assert 'a.oeffnen("zimmer", ansicht="maengel")' in z                     # Besen wegen dringendem Mangel
    s = _q("seiten.py")
    assert 'z.schluessel.rsplit("|", 1)[0] == nur' in s and "filter_alt_off" in s
    t = _q("themes.py")
    block = t.split(".m-kachel.teilweise", 1)[1].split("}", 1)[0]
    assert "linear-gradient(90deg" in block and "dashed" not in block


def test_rueckblick_und_wenn_dann_texte():
    u = _q("bestand_prognose_ui.py")
    assert "Bestand bleibt wie heute" in u and "100</b> durchgerechneten Verläufen" in u and "bis 0.85:" in u
    assert "im Rahmen des Zufalls" in u


def test_pivot_ende_ist_kein_geplantes_ende():
    ende = L + timedelta(days=60)                  # Pivot reicht nur 60 Tage voraus
    auf = [bk.Aufenthalt(1, "GS CNC 2601", date(2026, 1, 1), ende, 400, 0, 0),
           bk.Aufenthalt(2, "GS CNC 2602", date(2026, 2, 1), L + timedelta(days=20), 300, 0, 0)]
    fs = bp.faelle(auf, T, {}, L, ende)
    assert fs[0].geplant is None and fs[1].geplant == L + timedelta(days=20)
    md = bp.modell(fs, L, T)
    e = bp.simulieren(md, 0, 50, horizont=6)
    assert e.median[-1, 6] >= 1                    # der Abgeschnittene läuft weiter (Solldauer), nicht nur 60 Tage
