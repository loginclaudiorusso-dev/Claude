"""1.59: Szenarien – zusätzliche Belegungen (Mieter, Events), wirtschaftliche Lage je Maßnahme; Versandprotokoll."""

from datetime import date, datetime
from pathlib import Path

import pytest

from modern import massnahmen_lage as ml
from modern import szenario_zusatz as sz
from modern import versand_protokoll as vp

MOD = Path(sz.__file__).parent


def test_zusatz_anteilig_je_monat():
    z = sz.neu("event", "Tagung", 10, date(2027, 1, 16), bis=date(2027, 1, 31))
    assert sz.im_monat(z, date(2027, 1, 1)) == pytest.approx(10 * 16 / 31)
    assert sz.im_monat(z, date(2027, 2, 1)) == 0
    m = sz.neu("mieter", "", 5, date(2027, 1, 1), monate=12)
    assert m.bis == date(2027, 12, 31) and sz.im_monat(m, date(2027, 6, 1)) == 5
    assert sz.je_monat([z, m], [date(2027, 1, 1), date(2028, 1, 1)]) == pytest.approx([5 + 10 * 16 / 31, 0])
    assert "5 Mieter" in m.text and "Tagung" in z.text
    with pytest.raises(ValueError):
        sz.neu("mieter", "", 0, date(2027, 1, 1), monate=12)
    with pytest.raises(ValueError):
        sz.neu("mieter", "", 3, date(2027, 1, 1))                     # weder Dauer noch bis


def test_szenario_vergleich_mit_extra():
    from modern import analytik_kern as an
    from modern import auswertung_kern as ak

    zeilen = [ak.SZeile(date(2027, m, 1), "prognose", None, 200.0, 190.0, 210.0, 180.0, 220.0, None, 50.0, "ok", "")
              for m in (1, 2, 3)]
    neu = an.mit_extra(zeilen, 250, [sz.neu("mieter", "", 20, date(2027, 2, 1), monate=2)])
    assert [round(z.erwartet) for z in neu] == [200, 220, 220] and neu[1].reserve == 30
    assert an.mit_extra(zeilen, 250, None) is zeilen


def _reihe():
    from modern.massnahmen_neuanmeldungen import HZeile, NReihe

    z = [HZeile((2026, 1), "ist", 10, 0, 10, 10, 10), HZeile((2027, 1), "prognose", 2, 4, 16, 12, 20, False, 10, 24)]
    return NReihe("GS TEST", "lang", z, 10, 10, 10, 16, False, False)


def test_wirtschaftliche_lage_nur_auf_offene_nachbuchung():
    r = {"GS TEST": _reihe()}
    neu = ml.anwenden(r, -50, 2027)["GS TEST"]
    p = neu.zeilen[1]
    assert neu.zeilen[0].erwartet == 10                              # Ist bleibt Ist
    assert p.erwartet == 6 + (16 - 6) * .5 and p.klein == 6 + (12 - 6) * .5   # gebucht + begonnen (6) bleiben
    assert neu.naechstes_jahr == pytest.approx(16 - 5)
    assert r["GS TEST"].zeilen[1].erwartet == 16                     # Original unverändert
    assert ml.anwenden(r, 0) is r and ml.begrenzen(99) == 50 and ml.begrenzen("x") == 0
    assert ml.text(-10).startswith("Annahme: -10 %")


def test_versandprotokoll_eintrag_und_filter():
    e = vp.eintrag("fm", "Outlook gesendet", " fm@example.org ", "FM-Auftrag: Zimmer 2-108", "x " * 400, wer="Alex",
                   jetzt=datetime(2026, 11, 24, 15, 0))
    assert e.zeit == "2026-11-24T15:00:00" and e.an == "fm@example.org" and e.art_text == "Mail an FM"
    assert len(e.text) <= vp.TEXT_ANFANG + 1 and e.text.endswith("…")
    f = vp.eintrag("antwort", "Outlook-Entwurf", "erika@example.org", "AW: Zimmer", "", "Fehler: Outlook zu", wer="Kim")
    assert not f.ok
    alle = [e, f]
    assert vp.filtern(alle, "2-108") == [e] and vp.filtern(alle, art="antwort") == [f]
    assert vp.filtern(alle, nur_fehler=True) == [f] and vp.filtern(alle, "kim") == [f]


def test_oberflaeche_verdrahtet():
    sp = (MOD / "seite_prognose.py").read_text(encoding="utf-8")
    assert "_zusatz_planen(a, extra, alles_neu)" in sp and "Szenarien schließen" in sp
    assert 'a.setzen(aw_bereich="dashboard" if a.aw_bereich == k_ else k_' in sp and '"Rückblick", "history"' in sp
    assert 'graph_zeichnen(False)' in sp
    assert "vp.eintragen" in (MOD / "seite_heute.py").read_text(encoding="utf-8")
    assert "vp.eintragen" in (MOD / "outlook_kern.py").read_text(encoding="utf-8")
    assert "vp.eintragen" in (MOD / "seiten.py").read_text(encoding="utf-8")
    assert "Wirtschaftliche Lage:" in (MOD / "seite_massnahmen.py").read_text(encoding="utf-8")
    assert 'A("versandprotokoll")' in (MOD / "menueband.py").read_text(encoding="utf-8")
