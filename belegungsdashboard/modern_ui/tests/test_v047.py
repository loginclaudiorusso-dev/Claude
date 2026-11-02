"""0.47: Vorhaben → Maßnahmen → Kostenpositionen, Haupttreiber mit Nachweis, drei Statusachsen, Renovierung als
abgeleitetes Vorhaben, andere Vorhaben verbrauchen ihren Topf. Erfundene Daten und Beträge."""

from datetime import date

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _v(vk, **mehr):
    return vk.leer_vorhaben(**{"titel": "Brandschutztüren Musterhaus", "kategorie": "Brandschutz", "haus": "6",
                               "treiber": "pflicht", "nachweis": "Prüfprotokoll Muster vom 01.02.2030", **mehr})


def test_pflicht_braucht_nachweis_und_ein_treiber(leer):
    from modern import vorhaben_kern as vk

    v = _v(vk, nachweis="")
    with pytest.raises(ValueError, match="Rechtsgrundlage"):
        vk.speichern(v)
    with pytest.raises(ValueError, match="Haupttreiber"):
        vk.speichern({**v, "treiber": ""})
    assert vk.speichern({**v, "nachweis": "Auflage Muster"}) and len(vk.gespeichert()) == 1


def test_status_ergeben_sich_aus_terminen_auftrag_und_rechnungen():
    from modern import vorhaben_kern as vk

    h = date(2031, 6, 15)
    v = _v(vk)
    assert (vk.umsetzung(v, h), vk.finanzen(v)) == ("offen", "geschätzt")
    v["massnahmen"] = [{"id": "m1", "titel": "Türen EG", "von": "2031-09-01", "bis": "2031-09-30"}]
    v["kosten"] = [{"id": "k1", "titel": "Türen", "betrag": 12000, "herkunft": "angebot", "jahr": 2031, "topf": "bau"}]
    assert vk.umsetzung(v, h) == "terminiert"
    v["kosten"][0]["auftrag"] = {"betrag": 11500, "datum": "2031-06-01"}
    assert (vk.umsetzung(v, h), vk.finanzen(v)) == ("beauftragt", "gebunden")
    assert any("Entscheidung" in t for t in vk.hinweise(v, h))              # Idee, aber beauftragt
    v["entscheidung"] = {"status": "freigegeben", "datum": "2031-05-20", "wer": "Leitung"}
    assert not vk.hinweise(v, h)
    assert vk.umsetzung(v, date(2031, 9, 10)) == "in Arbeit"
    v["kosten"][0]["rechnungen"] = [{"betrag": 5000, "datum": "2031-09-15", "bezahlt_am": "2031-09-30"}]
    assert vk.finanzen(v) == "teilweise bezahlt"
    v["kosten"][0]["rechnungen"].append({"betrag": 6500, "datum": "2031-10-05", "bezahlt_am": "2031-10-20"})
    assert (vk.umsetzung(v, date(2031, 11, 1)), vk.finanzen(v)) == ("abgeschlossen", "abgerechnet")
    assert vk.betraege(v) == {"geplant": 12000, "gebunden": 11500, "abgerechnet": 11500, "bezahlt": 11500}


def test_renovierung_erscheint_als_vorhaben_und_zusatz_bleibt(leer):
    from belegung import zimmerplan as zp
    from modern import renovierung_kern as rk
    from modern import vorhaben_kern as vk

    st = zp.laden()
    rk.vormerken("6|3|", date(2031, 3, 1), date(2031, 3, 31))
    p = rk.parameter()
    alle = vk.alle({2031: rk.jahresplan(st, 2031, None, p)})
    r = next(v for v in alle if v["id"] == "reno-2031")
    assert r["abgeleitet"] and r["kategorie"] == "Renovierung" and len(r["massnahmen"]) == 1
    kid = r["kosten"][0]["id"]
    r["kosten"][0]["auftrag"] = {"betrag": 1000, "datum": "2031-01-10"}
    r["entscheidung"] = {"status": "freigegeben", "datum": "2031-01-05", "wer": "Leitung"}
    vk.speichern_auto_schritt(r)
    r2 = next(v for v in vk.alle({2031: rk.jahresplan(st, 2031, None, p)}) if v["id"] == "reno-2031")
    k = next(x for x in r2["kosten"] if x["id"] == kid)
    assert k["auftrag"]["betrag"] == 1000 and r2["entscheidung"]["status"] == "freigegeben" and vk.finanzen(r2) == "gebunden"
    assert len(r2["massnahmen"]) == 1                                         # Maßnahmen kommen weiter aus der Planung


def test_andere_vorhaben_verbrauchen_ihren_topf_abgelehnte_nicht(leer):
    from modern import vorhaben_kern as vk

    v = _v(vk, kosten=[{"id": "k1", "titel": "Türen", "betrag": 12000, "herkunft": "angebot", "jahr": 2031, "topf": "bau"},
                       {"id": "k2", "titel": "Schilder", "betrag": 800, "herkunft": "schaetzung", "jahr": 2032, "topf": "bau"}])
    w = vk.leer_vorhaben(titel="Sitzgruppe", treiber="qualitaet", nachweis="Bezüge verschlissen",
                         kosten=[{"id": "k3", "titel": "Möbel", "betrag": 3000, "herkunft": "eingabe", "jahr": 2031, "topf": "moebel"}],
                         entscheidung={"status": "abgelehnt", "datum": "", "wer": ""})
    assert vk.summe_topf([v, w], 2031, "bau") == 12000 and vk.summe_topf([v, w], 2031, "moebel") == 0
    zeilen = vk.liste([v, w], date(2031, 1, 1), jahr=2032)
    assert [z.v["titel"] for z in zeilen] == ["Brandschutztüren Musterhaus"]
    assert vk.liste([w, v], date(2031, 1, 1))[0].v["treiber"] == "pflicht"   # Pflicht steht oben


def test_speichern_und_loeschen_mit_rueckgaengig(leer):
    from modern import kern
    from modern import vorhaben_kern as vk

    v = _v(vk)
    vk.speichern_auto_schritt(v)
    vk.loeschen_schritt(v["id"], v["titel"])
    assert vk.gespeichert() == []
    ok, _t = kern.rueckgaengig()
    assert ok and [x["id"] for x in vk.gespeichert()] == [v["id"]]
