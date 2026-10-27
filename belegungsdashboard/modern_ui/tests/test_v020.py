"""0.20: Ordner-Import beim Start, Klassenstärken, Ziehen im Zeitstrahl, Kalender-Klick – erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def test_ordner_import_mit_rueckgaengig(leer, monkeypatch):
    from belegung import aenderungen, anreiseliste, einheitsliste, speicher, uwt
    from modern import daten_kern as dk

    monkeypatch.setattr(uwt, "automatisch_importieren", lambda: [])
    monkeypatch.setattr(einheitsliste, "automatisch_importieren", lambda: [])
    assert dk.ordner_importieren() == [] and aenderungen.letzter() is None      # nichts Neues → kein Schritt

    def liste_kommt():
        speicher.schreiben(anreiseliste.DATEI, {"personen": [{"name": "Beispiel, Bea"}]})
        return ["Kurs_Test.xlsx: 1 Anreisen neu, 0 aktualisiert"]

    def kaputt():
        raise OSError("Ordner gesperrt")

    monkeypatch.setattr(einheitsliste, "automatisch_importieren", liste_kommt)
    monkeypatch.setattr(uwt, "automatisch_importieren", kaputt)               # ein Fehler bricht den Rest nicht ab
    assert dk.ordner_importieren() == ["Liste: Kurs_Test.xlsx: 1 Anreisen neu, 0 aktualisiert"]
    assert "Automatisch eingelesen" in aenderungen.letzter().titel
    aenderungen.rueckgaengig()
    assert speicher.lesen(anreiseliste.DATEI, None) is None
    assert set(dk.eingangsordner()) == {"UWT", "Listen"}


def test_heute_karte_neuer_gebaeudeplan(leer, monkeypatch):
    from belegung import gebaeudeplan
    from modern import kern

    monkeypatch.setattr(gebaeudeplan, "neuer_plan_da", lambda: True)
    assert any(k.id == "gebaeudeplan" for k in kern.karten(None, date(2030, 1, 7)))
    monkeypatch.setattr(gebaeudeplan, "neuer_plan_da", lambda: False)
    assert not any(k.id == "gebaeudeplan" for k in kern.karten(None, date(2030, 1, 7)))


def test_klassenstaerken_beim_import(leer):
    from belegung import aenderungen, uwt
    from modern import daten_kern as dk

    an = date(2030, 2, 4)
    liste = uwt.UwtListe("Blockplan_Test.pdf", bloecke=[uwt.Block("TESTA1", 5, an, an + timedelta(days=11)),
                                  uwt.Block("TESTA1", 5, an + timedelta(days=28), an + timedelta(days=39)),
                                  uwt.Block("TESTB2", 7, an, an + timedelta(days=11))])
    assert dk.klassen_der_liste(liste) == {"TESTA1": 5, "TESTB2": 7}
    dk.uwt_uebernehmen("bloecke", liste, "Blockplan_Test.pdf", {"TESTA1": 12, "TESTB2": 0})
    assert [b.anzahl for b in liste.bloecke] == [12, 12, 0]
    assert uwt.klassenstaerken()["TESTA1"] == 12 and uwt.klassenstaerken()["TESTB2"] == 0
    aenderungen.rueckgaengig()
    assert "TESTA1" not in uwt.klassenstaerken()
    assert dk.klassenstaerken_setzen({"TESTB2": 4}).startswith("Klassenstärken gespeichert")
    assert uwt.klassenstaerken()["TESTB2"] == 4 and dk.klassenstaerken()["TESTB2"] == 4


def test_zeitstrahl_ziehen(leer):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern, seiten_kern as sk
    from modern import zimmer_kern as zk

    heute = date.today()
    p = [anreiseliste.Person("Zieher, Zora", "GS ASS", heute + timedelta(days=3), True, tn_id="901",
                             abreise=heute + timedelta(days=20))]
    anreiseliste.speichern(p, {})
    kern.vorschlaege_uebernehmen((heute + timedelta(days=3)).isoformat(), "alle")
    st = zp.laden()
    zw = next(z for z in st.zuweisungen)
    person, vorher = zw["person"], zw["zimmer"]
    z_alt = st.lage.zimmer[vorher]
    # ziehbar im Zeitstrahl
    zeilen = sk.zeitstrahl(st, z_alt.haus, heute, 28, heute)
    balken = [b for z in zeilen for b in z.balken if b.person == person]
    assert balken and "Ziehen" in balken[0].titel
    # Ziel: ein anderes freies Einzelzimmer im selben Haus
    ziel = next(z for z in st.zimmer if z.aktiv and z.haus == z_alt.haus and z.id != vorher and z.betten == 1
                and not zk.wechsel_pruefen(person, z.id).fehler)
    w = zk.wechsel_pruefen(person, ziel.id)
    assert w.vorher == z_alt.kurz and w.nach_kurz == ziel.kurz and w.name == "Zieher, Zora"
    assert zk.wechsel_pruefen(person, vorher).fehler                         # schon dort
    zk.wechseln(person, ziel.id)
    assert zp.laden().zugewiesen(person)["zimmer"] == ziel.id
    aenderungen.rueckgaengig()
    assert zp.laden().zugewiesen(person)["zimmer"] == vorher
