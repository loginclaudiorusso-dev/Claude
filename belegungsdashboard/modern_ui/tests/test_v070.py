"""0.70: Zimmerzustände – vier Zustände (frei, geplant, belegt, nicht nutzbar), die sich ausschließen und zusammen
alle Zimmer ergeben, plus zwei Markierungen (nicht bezugsfertig, mit Mangel). Erfundene Daten."""

from datetime import date

import pytest

from modern import zimmer_kern as zk


def test_zustand_regeln():
    z = zk.zustand
    assert z("frei") == "frei" and z("teilweise") == "frei"
    assert z("gesperrt") == "nicht_nutzbar" and z("frei", True) == "nicht_nutzbar" and z("teilweise", True) == "nicht_nutzbar"
    assert z("belegt", True) == "belegt" and z("geplant", True) == "geplant"   # belegt bleibt belegt, die Markierung warnt
    assert list(zk.ZUSTAENDE) == ["frei", "geplant", "belegt", "nicht_nutzbar"]
    assert list(zk.MARKEN) == ["unfertig", "maengel"]


def test_alte_schluessel_und_filter():
    assert zk.kacheln("gesperrt") == {"nicht_nutzbar"} and zk.kacheln(["unbewohnbar", "frei"]) == {"nicht_nutzbar", "frei"}
    p = zk.kachel_passt
    assert p("gesperrt", 0, False, set(), {"nicht_nutzbar"}) and p("frei", 3, True, set(), {"nicht_nutzbar"})
    assert not p("frei", 0, False, set(), {"nicht_nutzbar"})
    # Markierung „nicht bezugsfertig“ liegt auf „frei“ – zuteilbar, also nicht „nicht nutzbar“
    assert p("frei", 0, False, set(), {"frei", "unfertig"}, None, True)
    assert p("belegt", 2, False, {"heizung"}, {"maengel"})                       # Mangel auch an belegten Zimmern
    f = zk.filter_bauen(status="gesperrt")
    assert f.status == "" and f.zustand == "nicht_nutzbar"
    assert zk.filter_bauen(status="belegt").status == "belegt" and zk.filter_bauen(status="belegt").zustand == ""


@pytest.fixture
def stand(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    from belegung import zimmerplan as zp

    yield zp.laden()
    aenderungen.verlauf_leeren()


def test_zustaende_ergeben_alle_zimmer(stand):
    tag = date(2026, 12, 1)
    n = zk.zaehler(stand, "", tag)
    assert sum(n[s] for s in zk.ZUSTAENDE) == n[""] and n[""] > 0
    alle = [k for et in zk.uebersicht(stand, tag).values() for ks in et.values() for k in ks]
    zu = [zk.zustand(k.status, k.unbewohnbar) for k in alle]
    assert set(zu) <= set(zk.ZUSTAENDE) and len(zu) == len(alle)
    frei = zk.liste(stand, zk.filter_bauen(status="frei"), tag)
    assert all(r.status in ("frei", "teilweise") for r in frei)
