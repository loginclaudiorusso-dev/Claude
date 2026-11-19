"""1.17 – Stand in einer Zeile: aus Entscheidung, Umsetzung und Finanzen abgeleitet (nichts wird anders gespeichert)."""

import inspect
from datetime import date

from modern import vorhaben_kern as vk

HEUTE = date(2027, 5, 10)


def _v(entscheidung="idee", termine=(), auftrag=0, rechnungen=()):
    return {"entscheidung": {"status": entscheidung},
            "massnahmen": [{"von": a, "bis": b} for a, b in termine],
            "kosten": [{"betrag": 1000, "auftrag": {"betrag": auftrag} if auftrag else {},
                        "rechnungen": [{"betrag": b, "bezahlt_am": bz} for b, bz in rechnungen]}]}


def test_phasen_der_reihe_nach():
    assert vk.phase(_v(), HEUTE) == ("Vorschlag", "")
    assert vk.phase(_v("beantragt"), HEUTE) == ("Vorschlag", "beantragt")
    assert vk.phase(_v("freigegeben"), HEUTE) == ("Freigegeben", "")
    assert vk.phase(_v("freigegeben", auftrag=900), HEUTE) == ("Beauftragt", "")
    assert vk.phase(_v("freigegeben", [("2027-05-01", "2027-05-31")], 900), HEUTE) == ("In Umsetzung", "")
    assert vk.phase(_v("freigegeben", [("2027-04-01", "2027-04-30")], 900, [(900, "2027-05-02")]), HEUTE)[0] == "Abgerechnet"
    assert vk.phase(_v("abgelehnt", auftrag=900), HEUTE) == ("Abgelehnt", "")


def test_luecken_statt_unmoeglicher_kombination():
    assert vk.phase(_v("idee", auftrag=900), HEUTE) == ("Beauftragt", "Freigabe fehlt")
    assert vk.phase(_v("freigegeben", [("2027-04-01", "2027-04-30")], 900), HEUTE) == ("In Umsetzung", "Rechnung fehlt")


def test_liste_und_seiten_zeigen_eine_leiste():
    z = vk.liste([{**_v("freigegeben", auftrag=900), "id": "x", "titel": "Test"}], HEUTE)[0]
    assert (z.phase, z.luecke) == ("Beauftragt", "") and z.entscheidung == "freigegeben"    # Achsen bleiben erhalten
    from modern import cockpit_ui, seite_steuerung

    assert "phasen_leiste(z.phase, z.luecke" in inspect.getsource(seite_steuerung._vorhaben)
    assert "phasen_leiste(" in inspect.getsource(cockpit_ui._drawer)
