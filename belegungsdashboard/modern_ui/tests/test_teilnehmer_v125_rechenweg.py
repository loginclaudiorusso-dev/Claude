"""1.25 – Rechenweg der Teilnehmer-Prognose: alle Zutaten der Simulation mit den gemessenen Werten. Erfundene Fälle."""

import inspect

import pytest

from modern import bestand_prognose as bp
from modern import teilnehmer_rechenweg_kern as tr
from test_teilnehmer_v120_startwelle import ASS, VW, L, T, _faelle


@pytest.fixture(scope="module")
def lauf():
    md = bp.modell(_faelle(), L, T)
    return md, bp.simulieren(md, 0, 300)


def _zahl(t: str) -> float:
    return float(t.replace(".", "").replace(",", ".").replace("−", "-"))


def test_schritte_und_summe(lauf):
    md, e = lauf
    sch = tr.rechenweg(md, e, VW, 6)
    titel = [s.titel for s in sch]
    assert titel == ["Datenbasis", "Wer heute da ist – und wie lange er bleibt", "Fest angemeldet",
                     "Übergänge aus Assessment und Vorbereitung", "Weitere Zugänge aus der Erfahrung", "Simulation",
                     "Ergebnis"]
    sim = sch[5].rechnung
    teile = sim.split("Mittel = ")[1].split(" · ")[0]
    summe = _zahl(teile.split(" = ")[-1])
    assert abs(summe - float(e.zerlegung[:, e.zeile(VW), 6].sum())) < 0.06
    assert f"Median = {round(float(e.median[e.zeile(VW), 6]))}" in sim


def test_kurve_uebergang_und_saison(lauf):
    md, e = lauf
    sch = {s.titel: s for s in tr.rechenweg(md, e, VW, 6)}
    assert "Kaplan-Meier" in sch["Wer heute da ist – und wie lange er bleibt"].formel
    ue = " ".join(sch["Übergänge aus Assessment und Vorbereitung"].details)
    assert "Quote" in ue and "Wartezeit Median" in ue and "Startwellen: Jan, Jul" in ue
    assert "Jahresfaktor" in sch["Weitere Zugänge aus der Erfahrung"].rechnung


def test_alle_und_grenzen(lauf):
    md, e = lauf
    assert tr.rechenweg(md, e, "Alle", 3)[0].rechnung.startswith("alle Maßnahmen")
    assert tr.rechenweg(md, e, VW, 0) == [] and tr.rechenweg(md, e, "gibt es nicht", 3) == []
    assert tr.rechenweg(md, e, ASS, 2)


def test_eingebunden():
    from modern import bestand_prognose_ui as bu

    assert "_rechenweg(d, art, k)" in inspect.getsource(bu._planung)
    assert "_rechenweg(d, art, 6)" in inspect.getsource(bu._leitung)
