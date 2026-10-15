"""Kritische Planungsänderungen: nur das Angeforderte ändert sich, Konflikte blockieren, Fehler hinterlassen keinen
halben Stand, Rückgängig stellt genau den Stand davor her. Nur erfundene Namen."""

from datetime import date

import pytest


@pytest.fixture
def daten(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    leute = [anreiseliste.Person("Anders, Anna", "GS ASS", date(2026, 10, 19), True, tn_id="1", abreise=date(2026, 11, 13)),
             anreiseliste.Person("Berger, Bea", "GS ASS", date(2026, 10, 19), True, tn_id="2", abreise=date(2026, 11, 13)),
             anreiseliste.Person("Clever, Clara", "GS ASS", date(2026, 10, 19), True, tn_id="3", abreise=date(2026, 11, 13))]
    anreiseliste.speichern(leute, {})
    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Anders"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Berger"], st.lage.zimmer["GS-2-302"])])
    zp.status_setzen(b["Berger"].schluessel, True)          # Bea ist „fest“
    yield b
    aenderungen.verlauf_leeren()


def _zimmer(person):
    from belegung import zimmerplan as zp

    return (zp.laden().zugewiesen(person.schluessel) or {}).get("zimmer", "")


def test_freies_zimmer_zuweisen_ist_einfach(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    st = zp.laden()
    zt = [zp.Zuteilung(daten["Clever"], st.lage.zimmer["GS-2-303"])]
    v = aenderungen.zuweisungen_vorschau(st, zt, gesehen=st.zuweisungen)
    assert v.einfach and [a.art for a in v.aenderungen] == ["neu"] and not v.konflikte
    zp.zuweisungen_speichern(zt)
    assert _zimmer(daten["Clever"]) == "GS-2-303"


def test_zimmerwechsel_aendert_nur_die_person(daten):
    from belegung import zimmerplan as zp

    vorher = {z["person"]: dict(z) for z in zp.zuweisungen_laden()}
    st = zp.laden()
    zp.zuweisung_setzen(st, daten["Anders"].schluessel, "GS-2-303", "Test")
    nachher = {z["person"]: z for z in zp.zuweisungen_laden()}
    assert nachher[daten["Anders"].schluessel]["zimmer"] == "GS-2-303"
    assert nachher[daten["Berger"].schluessel] == vorher[daten["Berger"].schluessel]   # Bea unverändert, weiter „fest“
    assert set(nachher) == set(vorher)                                                 # niemand dazu, niemand weg


def test_belegtes_zielzimmer_wird_abgelehnt(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    roh = zp.zuweisungen_laden()
    st = zp.laden()
    with pytest.raises(ValueError, match="belegt"):
        zp.zuweisung_setzen(st, daten["Anders"].schluessel, "GS-2-302", "Test")      # dort wohnt Bea
    assert zp.zuweisungen_laden() == roh                                            # abgelehnt = nichts geändert
    v = aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(daten["Anders"], st.lage.zimmer["GS-2-302"])])
    assert v.konflikte and "belegt" in v.konflikte[0] and not v.einfach


def test_ueberschneidung_nur_wenn_zeitraeume_sich_treffen(daten):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp

    spaeter = anreiseliste.Person("Dorn, Dora", "GS ASS", date(2026, 12, 7), True, tn_id="4", abreise=date(2027, 1, 15))
    frueher = anreiseliste.Person("Ernst, Eva", "GS ASS", date(2026, 11, 2), True, tn_id="5", abreise=date(2026, 12, 4))
    personen, _ = anreiseliste.laden()
    anreiseliste.speichern(personen + [spaeter, frueher], {})
    st = zp.laden()
    d = next(x for x in st.bedarf if x.name == "Dorn, Dora")
    e = next(x for x in st.bedarf if x.name == "Ernst, Eva")
    z = st.lage.zimmer["GS-2-301"]                                     # Anna bis 13.11.
    assert not aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(d, z)]).konflikte      # danach: frei
    assert aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(e, z)]).konflikte          # überschneidet sich
    # zwei aus derselben Zuteilung ins selbe Einzelzimmer – auch das ist ein Konflikt
    v = aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(daten["Clever"], st.lage.zimmer["GS-2-303"]),
                                              zp.Zuteilung(e, st.lage.zimmer["GS-2-303"])])
    assert len(v.konflikte) == 1


def test_folgen_werden_gezeigt(daten):
    """„Neu“ + „Übernehmen“: Bea (fest) bekäme ein anderes Zimmer, Anna verlöre ihres – beides steht in der Vorschau."""
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    st = zp.laden()
    zts = [zp.Zuteilung(daten["Berger"], st.lage.zimmer["GS-2-303"]), zp.Zuteilung(daten["Anders"], None),
           zp.Zuteilung(daten["Clever"], st.lage.zimmer["GS-2-304"])]
    v = aenderungen.zuweisungen_vorschau(st, zts, {daten["Anders"].schluessel}, angefordert=set(), gesehen=st.zuweisungen)
    arten = {a.name: a for a in v.aenderungen}
    assert arten["Berger, Bea"].art == "umgeplant" and any("fest" in f for f in arten["Berger, Bea"].folgen)
    assert arten["Anders, Anna"].art == "entfernt"
    assert arten["Clever, Clara"].art == "neu" and not arten["Clever, Clara"].angefordert
    assert not v.einfach and not v.konflikte
    text = aenderungen.vorschau_text(v)
    assert "Umgeplant" in text and "entfernt" in text and "GS-2" not in text


def test_gleichzeitige_aenderung_wird_erkannt(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    gesehen = zp.laden().zuweisungen                     # Seite zeigt diesen Stand …
    st = zp.laden()
    zp.zuweisung_setzen(st, daten["Anders"].schluessel, "GS-2-305", "anderes Fenster")   # … woanders geändert
    st = zp.laden()
    v = aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(daten["Anders"], st.lage.zimmer["GS-2-303"])],
                                         gesehen=gesehen)
    assert v.konflikte and "woanders" in v.konflikte[0]


def test_rueckgaengig_stellt_genau_wieder_her(daten):
    from belegung import aenderungen, protokoll
    from belegung import zimmerplan as zp

    vorher = aenderungen.schnappschuss()
    st = zp.laden()
    zp.zuweisung_setzen(st, daten["Anders"].schluessel, "GS-2-303", "Test")
    assert aenderungen.merken("Anna nach 303", vorher) is not None
    ok, text = aenderungen.rueckgaengig()
    assert ok and "Anna nach 303" in text
    assert aenderungen.schnappschuss() == vorher                 # Byte für Byte der alte Stand
    assert _zimmer(daten["Anders"]) == "GS-2-301"
    assert protokoll.laden(1)[0]["aktion"] == "rückgängig"
    assert aenderungen.rueckgaengig()[0] is False               # nichts mehr übrig


def test_rueckgaengig_ueberschreibt_keine_spaeteren_aenderungen(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    vorher = aenderungen.schnappschuss()
    zp.zuweisung_setzen(zp.laden(), daten["Anders"].schluessel, "GS-2-303", "Test")
    aenderungen.merken("Anna nach 303", vorher)
    zp.zuweisung_setzen(zp.laden(), daten["Clever"].schluessel, "GS-2-304", "anderes Fenster")   # nicht gemerkt
    danach = aenderungen.schnappschuss()
    ok, text = aenderungen.rueckgaengig()
    assert not ok and "nicht mehr" in text
    assert aenderungen.schnappschuss() == danach               # nichts angefasst
    assert _zimmer(daten["Clever"]) == "GS-2-304"


def test_umzug_tausch_rueckgaengig(daten, monkeypatch):
    """Tausch = zwei verbundene Umzüge: zurücknehmen nimmt beide, Rückgängig holt beide wieder."""
    from belegung import aenderungen
    from belegung import umzug as um
    from belegung import zimmerplan as zp

    st = zp.laden()
    ba = next(x for x in st.lage.belegungen["GS-2-301"] if x.art in ("geplant", "belegt"))
    bb = next(x for x in st.lage.belegungen["GS-2-302"] if x.art in ("geplant", "belegt"))
    u1, _u2 = um.tausch_speichern(st, ba, bb, date(2026, 10, 26))
    assert len(um.laden()) == 2
    vorher = aenderungen.schnappschuss()
    um.entfernen(u1.id)
    aenderungen.merken("Tausch zurückgenommen", vorher)
    assert um.laden() == []
    assert aenderungen.rueckgaengig()[0]
    assert {u.id for u in um.laden()} == {u1.id, u1.partner}


def test_fehler_beim_speichern_hinterlaesst_nichts(daten, monkeypatch, qapp):
    """Bricht das Speichern mittendrin ab, wird der Stand davor wiederhergestellt; es gibt keine Erfolgsmeldung
    und keinen Protokolleintrag für etwas, das nicht gespeichert wurde."""
    from PySide6.QtWidgets import QMessageBox

    from belegung import aenderungen, protokoll, speicher
    from belegung import zimmerplan as zp
    from belegung.ui import aenderung_ui
    from belegung.ui.basis import Zustand

    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    z = Zustand()
    meldungen = []
    z.meldung.connect(lambda t, a: meldungen.append((a, t)))
    z.aenderung_gespeichert.connect(lambda t, a: meldungen.append(("undo", t)))
    vorher, prot = aenderungen.schnappschuss(), protokoll.laden()

    def halb():                                          # erster Teil gespeichert, dann Abbruch
        zp.zuweisung_setzen(zp.laden(), daten["Anders"].schluessel, "GS-2-303", "Test")
        raise OSError("Netzlaufwerk weg")

    assert aenderung_ui.ausfuehren(None, z, "Test", halb, "gespeichert") is False
    assert aenderungen.schnappschuss() == vorher
    assert [a for a, _t in meldungen] == ["fehler"]
    assert aenderungen.letzter() is None
    # Protokoll erst nach erfolgreichem Schreiben: schlägt das Schreiben fehl, kein Eintrag
    echt = speicher.schreiben
    prot = protokoll.laden()

    def kaputt(name, *a, **k):
        if name == zp.ZUWEISUNGEN:
            raise OSError("schreibgeschützt")
        return echt(name, *a, **k)

    monkeypatch.setattr(speicher, "schreiben", kaputt)
    with pytest.raises(OSError):
        zp.zuweisungen_entfernen({daten["Anders"].schluessel})
    with pytest.raises(OSError):
        zp.status_setzen(daten["Anders"].schluessel, True)
    assert protokoll.laden() == prot


def test_erfolg_bietet_rueckgaengig(daten, qapp):
    from belegung import aenderungen
    from belegung import zimmerplan as zp
    from belegung.ui import aenderung_ui
    from belegung.ui.basis import Zustand

    z = Zustand()
    meldungen = []
    z.aenderung_gespeichert.connect(lambda t, a: meldungen.append(t))
    ok = aenderung_ui.ausfuehren(None, z, "Anna nach 303",
                                 lambda: zp.zuweisung_setzen(zp.laden(), daten["Anders"].schluessel, "GS-2-303"), "ok")
    assert ok and meldungen == ["ok"] and aenderungen.letzter().titel == "Anna nach 303"
    aenderung_ui.rueckgaengig(None, z, fragen=False)
    assert _zimmer(daten["Anders"]) == "GS-2-301"


def test_konflikt_neu_planen_zeigt_erst_vorschau(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    roh = aenderungen.schnappschuss()
    verwaist, erg = zp.neu_planen_vorschlag(zp.laden(), {daten["Anders"].schluessel})
    assert aenderungen.schnappschuss() == roh                      # Vorschlag speichert nichts
    assert not verwaist and erg and erg[0].bedarf.name == "Anders, Anna"


def test_reiter_gruppiert_und_alte_nummern(qapp):
    from belegung.ui.seiten import zimmerplan as seite

    assert seite.TABS[0] == "Zuteilen" and set(seite.TABS) == set(seite.TAB_TIPPS)
    assert all(seite.TABS_VOR_610[i] in seite.TABS for i in range(len(seite.TABS_VOR_610)))


def test_frei_nur_wenn_niemand_nachrueckt(daten):
    from belegung import aenderungen
    from belegung import zimmerplan as zp

    st = zp.laden()                                      # Anna 301 → 303, Bea 302 → 301
    v = aenderungen.zuweisungen_vorschau(st, [zp.Zuteilung(daten["Anders"], st.lage.zimmer["GS-2-303"]),
                                              zp.Zuteilung(daten["Berger"], st.lage.zimmer["GS-2-301"])])
    a = {x.name: x for x in v.aenderungen}
    assert not any("frei" in f for f in a["Anders, Anna"].folgen)       # Bea rückt in 301 nach
    assert any("302 wird dafür frei" in f for f in a["Berger, Bea"].folgen)
    assert not v.konflikte                               # Tausch innerhalb der Zuteilung ist kein Konflikt
