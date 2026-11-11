"""0.95 – Diagramme für Laien (Karte): drei Fragen, Probe statt Backtest-Linie, lesbare Prognose (Achse ab 0, Voll,
Warnzone, zwei Bänder, Fortschreibung grau), Tagesverlauf als Säulen. Erfundene Zahlen."""

from datetime import date

from modern import blick_kern as bk


def _reihe():
    ms = [date(2025, m, 1) for m in range(11, 13)] + [date(2026, m, 1) for m in range(1, 13)] + \
         [date(2027, m, 1) for m in range(1, 11)]
    werte = [200.0 + (10 if m.month in (11, 12, 1) else 0) for m in ms]
    ist = [m < date(2026, 11, 1) for m in ms]
    return ms, werte, ist, [None if i else w + 12 for w, i in zip(werte, ist)]


def test_drei_fragen():
    ms, w, ist, hi = _reihe()
    f = bk.prognose_fragen(ms, w, ist, 330, hi, 3.2, .8)
    assert [x.frage for x in f] == ["Wird es voller oder leerer?", "Wird es eng?", "Wie verlässlich ist das?"]
    assert f[1].antwort == "Nein" and "eng wird es ab 280" in f[1].zeile
    assert f[2].antwort == "Sehr verlässlich" and "80 % im Band" in f[2].zeile
    eng = bk.prognose_fragen(ms, w, ist, 240, hi, 20.0)
    assert eng[1].antwort.startswith("Ja, ab ") and eng[2].antwort == "Mit Vorsicht"
    assert bk.prognose_fragen(ms, w, ist, 330, hi, .3)[2].zeile.startswith("im Schnitt weniger als 1 Platz")
    assert bk.prognose_fragen(ms, w, ist, None)[1].antwort == "Offen"


def test_probe():
    r = [(date(2026, m, 1), 100.0 + d, 100.0) for m, d in ((5, 1), (6, -2), (7, -18), (8, 0))]
    p = bk.probe(r, 5)
    assert p.titel == "In 3 von 4 Monaten lagen wir richtig" and "± 5 Plätze" in p.satz
    assert [drin for _m, _d, drin in p.punkte] == [True, True, False, True]
    assert bk.probe_text(date(2026, 7, 1), -18) == "Juli: 18 weniger" and bk.probe_text(date(2026, 2, 1), .4) == "Februar: 0,4 mehr"
    assert bk.probe([], 1).titel == "Noch keine Probe möglich"


def test_tag_beschriftung():
    assert bk.tag_beschriftung(date(2026, 11, 2)) == "Mo 02.11." and bk.tag_beschriftung(date(2026, 11, 8)) == "So 08.11."


def test_quelltext_regeln():
    from pathlib import Path

    mod = Path(__file__).resolve().parent.parent / "modern"
    p = (mod / "seite_prognose.py").read_text(encoding="utf-8")
    for teil in ('"min"] = 0', "Voll: {bk.zahl(kap)} Plätze", "wird es eng", "Fortschreibung, nicht geprüft",
                 "Plätze Luft bis zur Warnschwelle", "def _probe_karte", "def _fragen", '"backtest": a.aw_backtest and klassisch',
                 'z.art == "prognose"]'):
        assert teil in p, teil
    assert 'renderer="svg"' in (mod / "diagramm_karte.py").read_text(encoding="utf-8")
    a = (mod / "seite_auswertung.py").read_text(encoding="utf-8")
    assert "def _tage_saeulen" in a and "Wochenende" in a and '"Vollster Tag"' in a
