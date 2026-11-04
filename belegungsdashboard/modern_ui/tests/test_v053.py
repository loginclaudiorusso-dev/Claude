"""0.53: Zimmer hinzufügen und entfernen; Maßnahmen-Vergleich je Maßnahme. Erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def test_zimmer_anlegen_merkmale_und_loeschen(leer):
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import zimmer_zusatz_kern as zz

    vorher = len(zp.laden().zimmer)
    assert "angelegt" in zz.hinzufuegen_schritt("2", "", "699", 2)
    st = zp.laden()
    z = next(x for x in st.zimmer if x.id == "GS-2-699")
    assert len(st.zimmer) == vorher + 1 and z.etage == "6" and z.betten == 2 and z.aktiv
    assert any(x.id == "GS-2-699" for x in st.lage.zimmer.values())                     # auch in der Belegung
    with pytest.raises(ValueError, match="gibt es schon"):
        zz.hinzufuegen("2", "6", "699")
    z.tiere = True
    zp.stammdaten_speichern(st.zimmer, st.plan)                                          # Merkmale wie bei jedem Zimmer
    assert next(x for x in zp.laden().zimmer if x.id == "GS-2-699").tiere
    zz.entfernen_schritt("GS-2-699")
    assert len(zp.laden().zimmer) == vorher
    ok, _t = kern.rueckgaengig()
    assert ok and any(x.id == "GS-2-699" for x in zp.laden().zimmer)


def test_zimmer_aus_dem_plan_wird_nur_deaktiviert(leer):
    from belegung import zimmerplan as zp
    from modern import zimmer_zusatz_kern as zz

    z = next(x for x in zp.laden().zimmer if x.aktiv and not x.gaeste)
    assert "nicht mehr zum Internat" in zz.entfernen(z.id)
    assert not next(x for x in zp.laden().zimmer if x.id == z.id).aktiv


def test_verplantes_zusatzzimmer_nicht_loeschen(leer):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import zimmer_zusatz_kern as zz

    zz.hinzufuegen("2", "6", "698", 1)
    an = date.today() + timedelta(days=5)
    anreiseliste.speichern([anreiseliste.Person("Muster, Mara", "GS RVL", an, True, tn_id="1", abreise=an + timedelta(days=30))], {})
    st = zp.laden()
    zp.zuweisung_setzen(st, st.bedarf[0].schluessel, "GS-2-698")
    with pytest.raises(ValueError, match="verplant"):
        zz.entfernen("GS-2-698")


def test_zimmer_id_je_standort():
    from modern import standort_kern as sk
    from modern import zimmer_zusatz_kern as zz

    assert zz.zimmer_id("2", "201") == "GS-2-201" and zz.etage_vorschlag("E05") == "E" and zz.etage_vorschlag("312") == "3"
