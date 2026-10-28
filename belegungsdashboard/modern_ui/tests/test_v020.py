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


def _kreuztabelle(pfad):
    """Kleine erfundene Kreuztabelle (ohne Pivot-Objekt) im üblichen Aufbau."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Daten"
    ws.append(["Belegungen", "Spaltenbeschriftungen", None, None, None])
    ws.append([None, "BFW BP", "BFW GS", "BFW WE", "Gesamtergebnis"])
    ws.append(["Zeilenbeschriftungen", "Haus Test A", "Haus Test B", "Haus Test C", None])
    for i in range(10):
        ws.append([f"{i + 1:02d}.03.2030", 10 + i, 20, 30, 60 + i])
    wb.save(pfad)


def test_pivot_struktur(leer):
    from belegung import aenderungen, pivot
    from modern import daten_kern as dk

    pfad = leer / "Kreuz_Test.xlsx"
    _kreuztabelle(pfad)
    felder = pivot.PivotProfil().to_dict()
    ok, text = dk.pivot_vorschau(pfad, felder)
    assert not ok and "Pivot" in text                                     # automatisch: keine Pivot-Tabelle
    felder.update(name="Kreuz", sheet_modus="manuell", sheet_name="Daten")
    ok, text = dk.pivot_vorschau(pfad, felder)
    assert ok and text.startswith("✓ 10 Tage vom 01.03.2030") and "Haus Test B" in text
    with pytest.raises(ValueError):
        dk.pivot_struktur_speichern(pfad, {**felder, "datumsformat": "%Y-%m-%d"})   # passt nicht → nichts gespeichert
    assert dk.pivot_struktur_speichern(pfad, felder).startswith("Pivot-Struktur „Kreuz“")
    assert pivot.profil_fuer_datei("Kreuz_Test.xlsx").sheet_name == "Daten"
    aenderungen.rueckgaengig()
    assert pivot.profil_fuer_datei("Kreuz_Test.xlsx").sheet_name is None


def test_gebaeudeplan_aus_zwischenablage(leer):
    from belegung import speicher
    from modern import daten_kern as dk

    zeilen = ["Gebäudeplan", "GS-Haus-2", "01. Etage", "GS-2-101", "1 Bett", "Frei",
              "GS-2-102", "2 Betten", "Beispiel, Bea (GS RVL 2601)", "01.10.2030 - 31.12.2030"]
    html = "<table>" + "".join(f"<tr><td>{z}</td></tr>" for z in zeilen) + "</table>"
    plan, unterschiede, quelle = dk.gebaeudeplan_aus_zwischenablage("", html)
    assert [z.id for z in plan.zimmer] == ["GS-2-101", "GS-2-102"] and quelle["pfad"] == "Zwischenablage"
    assert isinstance(unterschiede, list)
    assert speicher.lesen(f"{speicher.IMPORT_ORDNER}/gebaeudeplan_eingefuegt.json", {})["html"] == html
    with pytest.raises(ValueError):
        dk.gebaeudeplan_aus_zwischenablage("irgendwas ohne Zimmer", "")


def test_meldungen_und_autostart(leer, monkeypatch):
    from belegung import neuigkeiten
    from belegung import termine as tm
    from modern import melder

    heute = date.today()
    tm.eigenen_speichern(tm.Termin("", heute, "Testtermin <Hausrundgang>", "Notiz", "eigen", vorlauf=0))
    ms = melder.sammeln(heute)
    assert [m.ziel for m in ms] == ["termine"] and "Testtermin" in ms[0].titel + ms[0].text
    assert melder.sammeln(heute) == []                                      # jede Meldung nur einmal am Tag
    assert any("Testtermin" in n.text for n in neuigkeiten.laden())
    xml = melder.toast_xml("Titel & mehr", "Zeile <1>\nZeile 2\nZeile 3\nZeile 4")
    assert "Titel &amp; mehr" in xml and "Zeile &lt;1&gt;" in xml and "Zeile 4" not in xml
    assert melder.an() and (melder.setzen(False) or not melder.an())
    if melder.sys.platform != "win32":
        assert melder.windows_zeigen("x", "y") is False
        with pytest.raises(OSError):
            melder.autostart_setzen(True, leer)
    befehl = melder.autostart_befehl(leer)
    assert "--minimiert" in befehl and "\r\n" in befehl and str(leer) in befehl and "Start.bat" in befehl
    (leer / ".venv" / "Scripts").mkdir(parents=True)
    (leer / ".venv" / "Scripts" / "pythonw.exe").write_text("")
    assert "pythonw.exe\" app.py --minimiert" in melder.autostart_befehl(leer)
    monkeypatch.setattr(melder.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(leer / "appdata"))
    assert melder.autostart_moeglich() and not melder.autostart_aktiv()
    melder.autostart_setzen(True, leer)
    assert melder.autostart_aktiv()
    melder.autostart_setzen(False, leer)
    assert not melder.autostart_aktiv()


def test_powershell_kodiert():
    import base64

    from modern import melder

    assert base64.b64decode(melder.ps_kodiert("Größe 'ü'")).decode("utf-16-le") == "Größe 'ü'"


def test_zaehler_und_glocke(leer):
    from belegung import neuigkeiten as nk
    from belegung import termine as tm
    from modern import kern

    heute = date.today()
    assert kern.nav_zahlen(None, heute) == {}
    tm.eigenen_speichern(tm.Termin("", heute, "Testtermin Zähler", "", "eigen", vorlauf=0))
    z = kern.nav_zahlen(None, heute)
    assert z["termine"].n == 1 and "fällig" in z["termine"].tipp and "assistenz" not in z
    nk.hinzufuegen("Erste Meldung", "info", "zimmerplan:Reinigung")
    nk.hinzufuegen("Zweite Meldung", "warnung", "unbekannt")
    liste, ungelesen = kern.neuigkeiten()
    assert ungelesen == 2 and {(n.text, n.seite, n.ansicht) for n in liste} >= {("Erste Meldung", "reinigung", ""),
                                                                                ("Zweite Meldung", "", "")}
    kern.neu_gelesen(next(n.id for n in liste if n.text == "Erste Meldung"))
    assert kern.neuigkeiten()[1] == 1
    kern.neu_gelesen(None)
    assert kern.neuigkeiten()[1] == 0
    assert kern.neu_ziel("zimmerplan:Aufgaben") == ("reinigung", "facility") and kern.neu_ziel("termine") == ("termine", "")
    assert kern.neu_ziel("posteingang") == ("assistenz", "")


def test_hinweise_und_allergiker_etage(leer):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import hinweise_kern as hk
    from modern import kern, melder

    assert [h.text for h in hk.erkennen("ev. Anr. 11.10. benötigt Duschhocker")] == ["Duschhocker", "evtl. Vortag"]
    assert [h.art for h in hk.erkennen("will Ehemann mitbringen in DZ")] == ["begleitung"]
    assert hk.allergiker("Hausstauballergie") and not hk.allergiker("keine Besonderheit")
    assert hk.rest("ev. Anr. 11.10.") == "" and hk.rest("ev. Anr. 11.10. Allergiker") == "Allergiker"
    heute = date.today()
    an = heute + timedelta(days=3)
    p = [anreiseliste.Person("Allergisch, Anna", "GS ASS", an, True, tn_id="801", abreise=an + timedelta(days=10),
                             bemerkung="Allergiker (Hausstaub)"),
         anreiseliste.Person("Normal, Nora", "GS ASS", an, True, tn_id="802", abreise=an + timedelta(days=10))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    zs = {z.name: z for z in kern.zeilen(st, an.isoformat(), heute)}
    a = zs["Allergisch, Anna"]
    assert [h.art for h in a.hinweise] == ["allergie"] and not zs["Normal, Nora"].hinweise
    assert a.vorschlag and hk.auf_allergie_etage(st.lage.zimmer[a.vorschlag])          # Vorschlag auf Haus 2, 1. OG
    k = kern.allergie_karte(st, heute)
    assert k.stufe == "dringend" and "nicht auf der Allergiker-Etage" in k.titel and "noch ohne Zimmer" in k.detail
    ms = melder.sammeln(heute)
    assert any("Allergiker" in m.titel and "Haus 2, 1. OG einplanen" in m.text for m in ms)
    assert not any("Allergiker" in m.titel for m in melder.sammeln(heute))           # nur einmal je Zustand
    kern.zuweisen(a.schluessel, a.vorschlag)
    st = zp.laden()
    k = kern.allergie_karte(st, heute)
    assert k.stufe == "info" and "alle auf der" in k.titel
    a = {z.name: z for z in kern.zeilen(st, an.isoformat(), heute)}["Allergisch, Anna"]
    assert a.status == "ok"
    # Schimmel im geplanten Zimmer: Warnung + Ausweichvorschlag auf der Etage (nie ein Zimmer mit Schimmel)
    from belegung import maengel as mg

    zid = next(z["zimmer"] for z in st.zuweisungen if z["person"] == a.schluessel)
    mg.setzen(zid, "geruch", True, heute)
    a = {z.name: z for z in kern.zeilen(zp.laden(), an.isoformat(), heute)}["Allergisch, Anna"]
    assert a.status == "handeln" and "Geruch oder Schmutz" in a.grund
    assert a.vorschlag and a.vorschlag != zid and hk.auf_allergie_etage(zp.laden().lage.zimmer[a.vorschlag])
    assert hk.meiden({zid: [mg.Mangel(zid, "geruch", heute)], "X": [mg.Mangel("X", "fenster", heute)]}) == {zid}


def test_bereitschaft_je_anreise(leer):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern

    heute = date.today()
    an = heute + timedelta(days=4)
    p = [anreiseliste.Person("Bereit, Berta", "GS ASS", an, True, tn_id="811", abreise=an + timedelta(days=10),
                             bemerkung="benötigt Duschhocker"),
         anreiseliste.Person("Ohne, Otto", "GS ASS", an, True, tn_id="812", abreise=an + timedelta(days=10))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    zs = {z.name: z for z in kern.zeilen(st, an.isoformat(), heute)}
    kern.zuweisen(zs["Bereit, Berta"].schluessel, zs["Bereit, Berta"].vorschlag)
    st = zp.laden()
    b = kern.bereitschaft(st, kern.zeilen(st, an.isoformat(), heute), an)
    assert (b.n, b.bereit, b.stufe) == (2, 0, "krit")
    assert ("blocker", "Ohne, Otto", "noch kein Zimmer") in b.punkte
    assert any(a == "blocker" and n == "Bereit, Berta" and "Vorbereiten" in t and "nicht erledigt" in t for a, n, t in b.punkte)
    assert any(a == "vorbereiten" and n == "Bereit, Berta" and "Duschhocker bereitstellen" in t for a, n, t in b.punkte)
    from modern import seiten_kern as sk

    offen = [r for r in sk.reinigung(st, heute, an, heute) if not r.erledigt]
    sk.reinigung_setzen([r.schluessel for r in offen], True, heute, an)
    st = zp.laden()
    b = kern.bereitschaft(st, kern.zeilen(st, an.isoformat(), heute), an)
    assert (b.bereit, b.stufe) == (1, "warn")


def test_reinigung_last_6_wochen(leer):
    from belegung import anreiseliste
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import seiten_kern as sk

    heute = date.today()
    an = heute + timedelta(days=9)
    p = [anreiseliste.Person(f"Last, Person{i}", "GS ASS", an, True, tn_id=f"82{i}", abreise=an + timedelta(days=12))
         for i in range(6)]
    einzeln = [an + timedelta(days=d) for d in (2, 3, 4) if (an + timedelta(days=d)).weekday() < 5][:2]
    p += [anreiseliste.Person(f"Einzeln, Ella{i}", "GS ASS", d, True, tn_id=f"83{i}", abreise=d + timedelta(days=20))
          for i, d in enumerate(einzeln)]
    anreiseliste.speichern(p, {})
    for d in {an, *einzeln}:
        kern.vorschlaege_uebernehmen(d.isoformat(), "alle")
    tage, je_haus, schnitt = sk.reinigung_last(zp.laden(), heute)
    assert len(tage) == 42 and tage[0].tag.weekday() == 0
    assert sum(t.n for t in tage) == sum(je_haus.values()) >= 12            # Vorbereiten vor Anreise + Auszug danach
    spitzen = [t for t in tage if t.spitze]
    assert spitzen and all(t.n == 6 for t in spitzen) and not any(t.spitze for t in tage if t.n < 5)


def _anreiseliste_xlsx(pfad, tag, zeilen):
    """Erfundene Anreiseliste im Aufbau der echten Listen (Titel, Leerzeile, Kopf, Zeilen)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append([f"Anreiseliste {tag:%d-%m-%Y} EMR"])
    ws.append([])
    ws.append(["Status", "lfd. Nr", "TN-ID", "Name, Vorname", "Wohnort", "Geb.-Datum", "KT", "Internat", "RIM/Koord.",
               "Maßn.", "Bemerkung", "Internatsdienst"])
    for i, (tn, name, dienst) in enumerate(zeilen, 1):
        ws.append(["E/", i, tn, name, "Musterstadt", date(1980, 1, 1), "DRV (EMR)", "ja", "Fr. Beispiel", "EMR ASS",
                   "Fahrtkosten", dienst])
    wb.save(pfad)


def test_import_aenderungsbericht_und_bezugsfertig(leer):
    from belegung import zimmerplan as zp
    from modern import daten_kern as dk
    from modern import kern
    from modern import zimmer_kern as zk

    heute = date.today()
    tag = heute + timedelta(days=6)
    p1 = leer / "liste1.xlsx"
    _anreiseliste_xlsx(p1, tag, [(990001, "Erstens, Emil", "ev. Anr."), (990002, "Zweitens, Zora", "ev. Anr."),
                                 (990003, "Drittens, Dora", "")])
    v = dk.anreisen_lesen([p1], ["liste1.xlsx"])
    assert v.listen and not v.fehler
    erst = dk.anreisen_aenderungen(v)
    assert {x.art for x in erst} == {"neu"} and len(erst) == 3
    dk.anreisen_uebernehmen(v)
    st = zp.laden()
    kennung = next(b.von.isoformat() for b in st.bedarf if b.name == "Erstens, Emil")
    emil = next(z for z in kern.zeilen(st, kennung, heute) if z.name == "Erstens, Emil")
    kern.zuweisen(emil.schluessel, emil.vorschlag)
    # zweite Fassung der Liste: Dora fehlt, Emil ist jetzt Allergiker
    p2 = leer / "liste2.xlsx"
    _anreiseliste_xlsx(p2, tag, [(990001, "Erstens, Emil", "ev. Anr. Allergiker"), (990002, "Zweitens, Zora", "ev. Anr.")])
    bericht = dk.anreisen_aenderungen(dk.anreisen_lesen([p2], ["liste2.xlsx"]))
    arten = {(x.art, x.name): x for x in bericht}
    assert ("geaendert", "Erstens, Emil") in arten and "neu: Allergiker" in arten[("geaendert", "Erstens, Emil")].text
    assert arten[("geaendert", "Erstens, Emil")].zimmer                     # geplantes Zimmer betroffen
    assert ("entfernt", "Drittens, Dora") in arten and ("geaendert", "Zweitens, Zora") not in arten
    assert bericht[0].name == "Erstens, Emil"                                # betroffene Planungen zuerst
    # bezugsfertig: das geplante Zimmer braucht vor der Anreise noch „Vorbereiten“ – am Anreisetag also offen
    st = zp.laden()
    unfertig = zk.nicht_bezugsfertig(st, emil.von)
    zid = next(z["zimmer"] for z in st.zuweisungen if z["person"] == emil.schluessel)
    assert zid not in unfertig                                                  # am Anreisetag schon belegt → nicht „frei“
    from modern import seiten_kern as sk

    r = next(r for r in sk._reinigungen(st, heute, emil.von) if r.zimmer.id == zid)
    assert "nicht" not in r.art and zid in zk.nicht_bezugsfertig(st, r.tag)      # am Tag der Vorbereitung: frei, aber offen
    sk.reinigung_setzen([f"{zid}|{r.tag.isoformat()}"], True, heute, emil.von)
    assert zid not in zk.nicht_bezugsfertig(zp.laden(), r.tag)                    # abgehakt → bezugsfertig
    assert zk.kachel_passt("frei", 0, False, set(), {"unfertig"}, None, True)
    assert not zk.kachel_passt("frei", 0, False, set(), {"unfertig"}, None, False)
