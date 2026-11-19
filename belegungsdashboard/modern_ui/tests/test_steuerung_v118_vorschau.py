"""1.18 – Cockpit: Vorschau beim Überfahren (Kacheln und Diagramm), ohne die Seite neu aufzubauen."""

import inspect

from modern import cockpit_kern as ck
from test_steuerung_v116_cockpit import _bedarf, _karte


def test_vorschau_dazu_und_weg():
    a, b = _karte("a", 10, 50000, 8000, 3, umzuege={3: 4}), _karte("b", 30, 20000, 5000, 6, umzuege={6: 2})
    bd = _bedarf()
    jetzt = ck.bewerten([a, b], {"a": 3}, bd, 60000, 0, [])
    v = ck.vorschau([a, b], {"a": 3}, b, 6, bd, 60000, 0, [], jetzt)            # b käme im Juni dazu
    assert v.an and round(v.bau) == round(b.kosten.instandhaltung) and v.umzuege == 2 and v.zimmer == 2
    assert v.neue_engpaesse == [5] and v.knapp_nachher == (5, -15)
    t = ck.vorschau_texte(v, 2027)
    assert t["engpass"] == "Vorschau: Jun fehlen 15 Betten" and t["umzuege"] == "Vorschau: +2 Umzüge"
    assert "über Budget" in t["budget"]
    w = ck.vorschau([a, b], {"a": 3}, a, 3, bd, 60000, 0, [], jetzt)            # a fiele weg
    assert not w.an and w.bau < 0 and ck.vorschau_texte(w, 2027)["umzuege"] == "Vorschau: −4 Umzüge"


def test_gleicher_engpasswert_wird_nicht_gemeldet():
    a, b = _karte("a", 10, 1, 0, 3), _karte("b", 10, 1, 0, 6)
    bd = _bedarf()
    jetzt = ck.bewerten([a, b], {"a": 3}, bd, None, 0, [])
    v = ck.vorschau([a, b], {"a": 3}, b, 6, bd, None, 0, [], jetzt)             # zweiter Monat genauso knapp
    assert "engpass" not in ck.vorschau_texte(v, 2027)


def test_diagramm_zeigt_vorschau_getrennt():
    a, b = _karte("a", 10, 1, 0, 3), _karte("b", 12, 1, 0, 6)
    bd = _bedarf()
    jetzt = ck.bewerten([a], {"a": 3}, bd, None, 0, [])
    o = ck.diagramm(bd, jetzt, vor=ck.bewerten([a, b], {"a": 3, "b": 6}, bd, None, 0, []))
    reihe = {s["name"]: s["data"] for s in o["series"]}
    assert reihe["Vorschau: Baustelle dazu"][5] == 12 and reihe["Baustelle"][2] == 10
    assert reihe["Vorschau: verfügbar"][5] == 120 - 5 - 12 and reihe["verfügbare Betten"][5] == 115
    assert all(s.get("m_fest") for s in o["series"])


def test_oberflaeche_ohne_neuaufbau():
    from modern import cockpit_ui

    q = inspect.getsource(cockpit_ui._vorschau_an)
    assert "a.setzen" not in q and "set_text" in q and "_diagramm_setzen" in q
    assert '"mouseenter"' in inspect.getsource(cockpit_ui._karte)
