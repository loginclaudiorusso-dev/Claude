"""Neue Oberfläche ab 0.3: Anreisen-Zusätze, Zimmerkarte, Termine, Inventar, Einstellungen, Daten – nur erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def haus(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date.today()
    p = [anreiseliste.Person("Abreise, Alma", "GS RVL", heute - timedelta(days=30), True, tn_id="1", abreise=heute),
         anreiseliste.Person("Neu, Nils", "GS RVL", heute + timedelta(days=2), True, tn_id="2", abreise=heute + timedelta(days=40)),
         anreiseliste.Person("Ohne, Olga", "GS RVL", heute + timedelta(days=2), True, tn_id="3", abreise=heute + timedelta(days=40))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Abreise"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Neu"], st.lage.zimmer["GS-2-302"])])
    yield heute
    aenderungen.verlauf_leeren()


def test_abreisen_eintragen_und_zuruecknehmen(haus):
    from belegung import zimmerplan as zp
    from modern import anreisen_kern as ank
    from modern import kern

    st = zp.laden()
    ab = ank.abreisen(st, haus, haus)
    assert [x.name for x in ab] == ["Abreise, Alma"] and ab[0].zimmer == "2-301"
    assert "Abreiseliste" in ank.abreisen_druck(st, haus, haus)
    ein = ank.eintragen_liste(st, haus)
    assert {e.name for e in ein} == {"Abreise, Alma", "Neu, Nils"} and not any(e.haken for e in ein)
    ank.eintragen_setzen([e.schluessel for e in ein], True, haus)
    assert all(e.haken for e in ank.eintragen_liste(zp.laden(), haus))
    assert "2-302" in ank.eintragen_text(zp.laden(), haus, nur_offen=False)
    kennung = (haus + timedelta(days=2)).isoformat()
    assert "<" in ank.anreise_druck(zp.laden(), kennung, "schilder", "Test")
    ank.anreise_zuruecknehmen(kennung)
    assert not zp.laden().zugewiesen(next(b.schluessel for b in st.bedarf if b.name.startswith("Neu")))
    assert kern.rueckgaengig()[0]


def test_person_angaben_anlegen_entfernen(haus):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import anreisen_kern as ank

    st = zp.laden()
    s = next(b.schluessel for b in st.bedarf if b.name.startswith("Ohne"))
    ank.angaben_setzen(s, "w", True)
    p = ank.person(zp.laden(), s)
    assert p.geschlecht == "w" and p.tier and p.aus_liste
    ank.person_aendern(s, haus + timedelta(days=20), "Erfundene Bemerkung")
    assert ank.person(zp.laden(), s).abreise == haus + timedelta(days=20)
    with pytest.raises(ValueError):
        ank.person_anlegen("OhneKomma", "GS RVL", haus, None)
    ank.person_anlegen("Probe, Paula", "GS RVL", haus + timedelta(days=5), None, "99")
    assert any(x.name == "Probe, Paula" for x in anreiseliste.laden()[0])
    ank.person_entfernen("id:99")
    assert not any(x.name == "Probe, Paula" for x in anreiseliste.laden()[0])


def test_zimmerkarte_mangel_notiz_umzug(haus):
    from belegung import maengel as mg
    from belegung import termine as tm
    from belegung import umzug as um
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import zimmer_kern as zk

    k = zk.karte(zp.laden(), "GS-2-301", haus)
    assert k.kurz == "2-301" and [p.name for p in k.personen] == ["Abreise, Alma"]
    zk.mangel_setzen("GS-2-301", "heizung", True)
    assert mg.offen("GS-2-301")
    assert kern.rueckgaengig()[0] and not mg.offen("GS-2-301")
    zk.notiz_hinzu("zimmer:GS-2-301", "Zimmer 2-301", "Rollo prüfen", haus + timedelta(days=1))
    assert any(n.text == "Rollo prüfen" for n in tm.notizen("zimmer:GS-2-301"))
    zk.hinweis_setzen("GS-2-301", "Erfundener Hinweis")
    assert zk.karte(zp.laden(), "GS-2-301", haus).hinweis == "Erfundener Hinweis"
    p = zk.karte(zp.laden(), "GS-2-301", haus).personen[0]
    ziele = zk.umzug_ziele("GS-2-301", p.schluessel, p.name, haus)
    assert ziele and "GS-2-301" not in ziele
    zk.umzug_speichern("GS-2-301", p.schluessel, p.name, next(iter(ziele)), haus)
    assert um.laden()
    liste = zk.liste(zp.laden(), zk.filter_bauen(haus="2", schnell={"maengel"}), haus)
    assert all(r.zimmer.startswith("GS-2-") for r in liste)


def test_termine_inventar_einstellungen_daten(haus):
    from belegung import inventar as iv
    from belegung import laden, speicher
    from belegung import termine as tm
    from modern import daten_kern as dk
    from modern import kern, seite_einstellungen, seite_inventar, seite_termine

    seite_termine.eigener_speichern("", haus, "Erfundener Termin", "", 1)
    t = next(x for x in tm.alle() if x.titel == "Erfundener Termin")
    seite_termine.erledigt_setzen(t.id, True)
    assert next(x for x in tm.alle() if x.id == t.id).erledigt
    seite_termine.eigener_loeschen(t.id)
    assert not any(x.titel == "Erfundener Termin" for x in tm.alle())

    seite_inventar.gegenstand_speichern(None, "Testlampe", "Elektro", 10, "")
    g = iv.laden().nach_name("Testlampe")
    seite_inventar.verteilen(g.id, [("GS-2-301", 1), ("GS-2-302", 2)], 1, True)
    inv = iv.laden()
    assert inv.verteilt(g.id) == 3 and inv.frei(g.id) == 7
    seite_inventar.kopieren("GS-2-302", ["GS-2-303"])
    assert iv.laden().anzahl("GS-2-303", g.id) == 2

    seite_einstellungen.zahl_setzen("zimmer_puffer", 2)
    assert speicher.einstellungen()["zimmer_puffer"] == 2
    assert kern.rueckgaengig()[0] and speicher.einstellungen().get("zimmer_puffer", 1) == 1
    with pytest.raises(ValueError):
        seite_einstellungen.zahl_setzen("zimmer_puffer", 99)
    seite_einstellungen.stammdaten_setzen("GS-2-310", {"tiere": True, "notiz": "Erfunden"})
    from belegung import zimmerplan as zp
    z = next(x for x in zp.laden().zimmer if x.id == "GS-2-310")
    assert z.tiere and z.notiz == "Erfunden"

    dk.manuell_hinzu("Gäste", "BFW GS", haus, haus + timedelta(days=3), 2, "Erfundene Gruppe")
    assert laden.manuelle_laden()[-1]["bezeichnung"] == "Erfundene Gruppe"
    dk.manuell_loeschen(0)
    assert laden.manuelle_laden() == []
    dk.kapazitaeten_speichern({"BFW GS": {"netto": 80, "brutto": 100}})
    assert dk.kapazitaeten()["BFW GS"]["netto"] == 80
    assert {q.schluessel for q in dk.uebersicht()} >= {"anreisen", "uwt", "gebaeudeplan", "pivot", "manuell"}


def test_defekte_zimmer_uebersicht_nach_planung(haus):
    from belegung import maengel as mg
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import zimmer_kern as zk

    mg.setzen("GS-2-303", "schimmel", True, haus)
    mg.setzen("GS-2-304", "fenster", True, haus)
    st = zp.laden()
    zs = zk.maengel_liste(st, haus)
    assert [z.kurz for z in zs] == ["2-303", "2-304"] and zs[0].stufe == 3 and zs[1].stufe == 1
    assert "2-303" in zk.fm_mailtext(st) and "<" in zk.fm_bericht_html(st, haus)
    haeuser = zk.uebersicht(st, haus)
    kachel = next(k for et in haeuser["2"].values() for k in et if k.kurz == "2-303")
    assert kachel.stufe == 3 and kachel.unbewohnbar
    np_ = kern.nach_planung(st, haus, 4)
    assert len(np_.wochen) == 4 and np_.tiefst is not None and np_.offen >= 1
