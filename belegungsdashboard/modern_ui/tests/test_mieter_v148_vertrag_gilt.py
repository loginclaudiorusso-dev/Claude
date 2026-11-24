"""1.48 – Mietvertrag gilt: der Gebäudeplan überstimmt das Zimmer eines Mieters nicht mehr; Verlängern mit
Optionen und automatischer Verlängerung. Erfundene Namen und Beträge."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


def _zwei_vertraege():
    from belegung import mieter as mt
    from modern import mieter_kern as mk

    zimmer = list(mk.zimmer_auswahl(date(2027, 3, 1), date(2027, 8, 31), "Frau"))
    a = mt.Mietvertrag("27-101", "Frau", "Erika", "Beispiel", zimmer[0], date(2027, 3, 1), date(2027, 8, 31), 400.0)
    b = mt.Mietvertrag("27-102", "Herr", "Alex", "Musterhoff", zimmer[1], date(2027, 3, 1), date(2027, 8, 31), 400.0)
    mt.anlegen(a)
    mt.anlegen(b)
    return a, b, zimmer


def test_gebaeudeplan_ueberstimmt_den_vertrag_nicht(goslar):
    from belegung import zimmerplan as zp
    from modern import mietbindung as mb

    a, b, zimmer = _zwei_vertraege()
    stand = zp.laden()
    # Gebäudeplan bucht beide Mieter in andere Zimmer (so kam es vor)
    plan = SimpleNamespace(stand=None, belegungen=[
        zp.Belegung(zimmer[5], date(2027, 3, 1), date(2027, 8, 31), "belegt", "Beispiel, Erika", "Miete", "w"),
        zp.Belegung(zimmer[6], date(2027, 3, 1), date(2027, 8, 31), "belegt", "Musterhoff, Alex", "Miete", "m")])
    zuw = [z for z in zp.zuweisungen_laden() if z["person"].startswith("mv:")]
    assert {z["vorrang"] for z in zuw} == {"planung"}
    lage = zp.lage_bauen(stand.zimmer, plan, zuw)
    def wo(name):
        return [zid for zid, bs in lage.belegungen.items() for x in bs if x.name == name and x.art in ("belegt", "geplant")]
    assert wo("Beispiel, Erika") == [a.zimmer] and wo("Musterhoff, Alex") == [b.zimmer]
    ab = mb.abweichungen(plan, [a, b], date(2027, 2, 1))
    assert [(x.nr, x.vertrag, x.gebaeudeplan) for x in ab] == [("27-101", a.zimmer, zimmer[5]), ("27-102", b.zimmer, zimmer[6])]


def test_falsche_oder_fehlende_zuweisung_wird_aus_dem_vertrag_gesetzt(goslar):
    from belegung import speicher
    from belegung import zimmerplan as zp

    a, b, zimmer = _zwei_vertraege()
    roh = zp.zuweisungen_laden._roh()
    for z in roh:
        if z["person"] == a.person:
            z["zimmer"], z["vorrang"] = zimmer[9], "plan"       # von Hand verschoben, „Gebäudeplan gilt“ gewählt
    roh = [z for z in roh if z["person"] != b.person]          # Zuweisung fehlt ganz
    speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": roh})
    zuw = {z["person"]: z for z in zp.zuweisungen_laden()}
    assert zuw[a.person]["zimmer"] == a.zimmer and zuw[a.person]["vorrang"] == "planung"
    assert zuw[b.person]["zimmer"] == b.zimmer
    stand = zp.laden()
    assert any(x.person == b.person for x in stand.lage.belegungen[b.zimmer])


def test_verlaengern_optionen_und_automatisch(goslar):
    from belegung import mieter as mt
    from modern import kern
    from modern import mietbindung as mb

    a, b, _z = _zwei_vertraege()
    assert mb.neues_ende(date(2027, 8, 31), 6) == date(2028, 2, 29)
    assert mb.neues_ende(date(2027, 8, 31), 3) == date(2027, 11, 30)
    assert mb.neues_ende(date(2027, 8, 31), 12) == date(2028, 8, 31)
    assert "6 Monate" in mb.auto_setzen("27-101", 6)
    assert mb.auto() == {"27-101": 6}
    assert mb.auto_faellig(mt.laden(), date(2027, 7, 1)) == []                 # noch zu früh
    fs = mb.auto_faellig(mt.laden(), date(2027, 8, 10))
    assert [(f.nr, f.neu) for f in fs] == [("27-101", date(2028, 2, 29))]
    k = kern.mieter_auto_karte(date(2027, 8, 10))
    assert k is not None and "27-101" in k.detail and k.zweite.zeigen == "mieter"
    mb.auto_setzen("27-101", None)
    assert mb.auto() == {}


def test_optionen_menue_in_der_mieterliste():
    q = (Path(__file__).parents[1] / "modern" / "seiten.py").read_text(encoding="utf-8")
    assert "Mietvertrag verlängern …" in q and "Automatisch verlängern: je" in q and "_mt_optionen(a, m)" in q
    o = (Path(__file__).parents[1] / "modern" / "oberflaeche.py").read_text(encoding="utf-8")
    assert "mg.DATEI" in o and "mietbindung.AUTO_DATEI" in o
