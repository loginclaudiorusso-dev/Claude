"""6.26: Neuen Gebäudeplan vor dem Übernehmen mit dem Zimmerplan (bisheriger Gebäudeplan + eigene Einträge) vergleichen – Vorrang wählbar.
Nur erfundene Namen."""

import dataclasses
from datetime import date

import pytest

HEUTE = date(2026, 10, 24)


@pytest.fixture
def welt(tmp_path, monkeypatch):
    """Bisheriger Gebäudeplan mit zwei Personen, eigene Planung für zwei weitere (eine wohnt schon, eine kommt)."""
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import assistenz, gebaeudeplan as gp
    from belegung import zimmerplan as zp

    st = zp.laden()
    probe = zp.Bedarf("x", "x", "", "Reha", date(2026, 1, 1), date(2027, 12, 31), "m")
    frei = [z.id for z in st.zimmer if z.aktiv and z.betten == 1 and not z.nur_maenner
            and zp.passt(st.lage, z, probe) is None][:6]
    k = [z.removeprefix("GS-") for z in frei]
    plan_zimmer = [gp.PlanZimmer(z.id, z.haus, z.etage, z.nr, z.betten) for z in st.zimmer]
    alt = gp.Gebaeudeplan("alt.docx", date(2026, 10, 1), plan_zimmer, [
        gp.Belegung(frei[0], date(2026, 9, 1), date(2027, 2, 28), "belegt", "Altbestand, Anna", "GS VW 2609"),
        gp.Belegung(frei[1], date(2026, 9, 1), date(2027, 2, 28), "belegt", "Bleibt, Bernd", "GS VW 2609"),
    ])
    gp.speichern(alt)
    bek = {z.id for z in st.zimmer}
    assistenz.ausfuehren(assistenz.verstehen_alle(
        f"Wohnt, Willi vom 01.10.2026 bis 31.03.2027 in {k[2]}\nKommt, Klara vom 02.11.2026 bis 30.04.2027 in {k[3]}",
        bek, HEUTE), HEUTE)
    return alt, frei, plan_zimmer


def _neu(alt, belegungen):
    return dataclasses.replace(alt, datei="neu.docx", stand=date(2026, 10, 23), belegungen=belegungen)


def test_gleicher_plan_ohne_unterschiede(welt):
    from belegung import planabgleich as pa
    from belegung import zimmerplan as zp

    alt, frei, _ = welt
    # Planung: Willi wohnt schon (belegt) und steht im neuen Plan; Klara kommt erst – fehlt dort, das ist normal
    neu = _neu(alt, alt.belegungen + [
        dataclasses.replace(alt.belegungen[0], zimmer=frei[2], name="Wohnt, Willi", von=date(2026, 10, 1),
                            bis=date(2027, 3, 31))])
    assert pa.vergleichen(neu, zp.laden(), HEUTE) == []
    assert "Keine Unterschiede" in pa.zusammenfassung([])


def test_unterschiede_und_vorrang(welt):
    from belegung import planabgleich as pa
    from belegung import zimmerplan as zp

    alt, frei, _ = welt
    b = alt.belegungen
    neu = _neu(alt, [
        dataclasses.replace(b[1], bis=date(2027, 6, 30)),                                   # Bernd länger
        dataclasses.replace(b[0], zimmer=frei[4], name="Wohnt, Willi", von=date(2026, 10, 1),
                            bis=date(2027, 3, 31)),                                         # Willi woanders
        dataclasses.replace(b[0], zimmer=frei[3], name="Fremd, Frieda", von=date(2026, 11, 1),
                            bis=date(2027, 1, 31)),                                         # in Klaras Zimmer
    ])                                                                                      # Anna fehlt
    us = pa.vergleichen(neu, zp.laden(), HEUTE)
    art = {u.name: u.art for u in us}
    assert art == {"Altbestand, Anna": "fehlt", "Bleibt, Bernd": "zeitraum", "Wohnt, Willi": "zimmer",
                   "Kommt, Klara": "konflikt", "Fremd, Frieda": "neu"}
    entscheidbar = {u.name: (u.wahl, list(u.optionen)) for u in us if u.entscheidbar}
    assert entscheidbar == {"Wohnt, Willi": ("plan", ["plan", "planung"]),
                            "Kommt, Klara": ("planung", ["planung", "entfernen"])}
    assert "Frieda" in next(u.plan for u in us if u.art == "konflikt")
    # Planung behalten: Willi bleibt in seinem Zimmer, auch gegen den neuen Gebäudeplan
    next(u for u in us if u.name == "Wohnt, Willi").wahl = "planung"
    assert pa.anwenden(neu, us) == 1
    st = zp.laden()
    assert st.plan.datei == "neu.docx"
    wo = {x.zimmer for bs in st.lage.belegungen.values() for x in bs if x.name == "Wohnt, Willi"}
    assert wo == {frei[2]}
    # nächster Abgleich: die Entscheidung ist vorausgewählt
    assert next(u for u in pa.vergleichen(neu, st, HEUTE) if u.name == "Wohnt, Willi").wahl == "planung"
    # Gebäudeplan gilt: Willi steht im Zimmer laut Plan
    us = pa.vergleichen(neu, st, HEUTE)
    next(u for u in us if u.name == "Wohnt, Willi").wahl = "plan"
    next(u for u in us if u.name == "Kommt, Klara").wahl = "entfernen"
    pa.anwenden(neu, us)
    st = zp.laden()
    wo = {x.zimmer for bs in st.lage.belegungen.values() for x in bs if x.name == "Wohnt, Willi"}
    assert wo == {frei[4]} and not any(z["name"] == "Kommt, Klara" for z in zp.zuweisungen_laden())


def test_import_rueckgaengig(welt):
    from belegung import aenderungen, gebaeudeplan as gp, planabgleich as pa
    from belegung import zimmerplan as zp

    alt, frei, _ = welt
    neu = _neu(alt, alt.belegungen[1:])
    vorher = aenderungen.schnappschuss(aenderungen.dateien_mit_plan())
    pa.anwenden(neu, pa.vergleichen(neu, zp.laden(), HEUTE))
    assert aenderungen.merken("Gebäudeplan übernommen", vorher) is not None
    assert gp.laden()[0].datei == "neu.docx"
    ok, _text = aenderungen.rueckgaengig()
    assert ok and gp.laden()[0].datei == "alt.docx" and len(gp.laden()[0].belegungen) == 2


def test_neuer_plan_im_ordner_wird_nicht_still_gespeichert(welt, tmp_path, monkeypatch):
    """6.26: Der Zimmerplan übernimmt einen neuen Plan aus dem Ordner „Gebaeudeplan“ erst nach der Prüfung –
    ``neuer_plan`` liest nur, speichert nichts."""
    from belegung import gebaeudeplan as gp

    alt, _frei, _ = welt
    ordner = tmp_path / "eingang"
    ordner.mkdir()
    (ordner / "plan.docx").write_bytes(b"kein echtes Word")
    monkeypatch.setattr(gp, "lesen", lambda pfad: _neu(alt, alt.belegungen[:1]))
    plan, kennung = gp.neuer_plan(ordner)
    assert kennung["pfad"] == "plan.docx" and len(plan.belegungen) == 1
    assert gp.laden()[0].datei == "alt.docx"                 # nichts gespeichert
    gp.speichern(plan, kennung)
    assert gp.neuer_plan(ordner) is None                      # schon übernommen


def test_sperrungen_und_freigaben(welt):
    """6.27: Sperrungen und Zimmerfreigaben – neu, entfällt, anderer Zeitraum – werden gemeldet (nur Information)."""
    from belegung import gebaeudeplan as gp
    from belegung import planabgleich as pa
    from belegung import zimmerplan as zp

    alt, frei, _ = welt
    sperre = gp.Belegung(frei[4], date(2026, 11, 1), date(2026, 12, 31), "gesperrt", grund="Reno offen")
    freigabe = gp.Belegung(frei[5], date(2026, 12, 1), date(2027, 1, 31), "freigabe", grund="Zimmerfreigabe")
    gp.speichern(dataclasses.replace(alt, belegungen=alt.belegungen + [sperre, freigabe]))
    st = zp.laden()
    gleich = _neu(alt, alt.belegungen + [sperre, freigabe])
    assert [u for u in pa.vergleichen(gleich, st, HEUTE) if u.art in ("sperre", "freigabe")] == []
    neu = _neu(alt, alt.belegungen + [dataclasses.replace(sperre, bis=date(2027, 3, 31)),
                                      gp.Belegung(frei[0], date(2027, 3, 1), date(2027, 3, 31), "gesperrt",
                                                  grund="Renovierung")])
    us = [u for u in pa.vergleichen(neu, st, HEUTE) if u.art in ("sperre", "freigabe")]
    assert sorted((u.art_text, u.name.split()[-1]) for u in us) == sorted([
        ("Sperrung geändert", frei[4].removeprefix("GS-")), ("Sperrung neu", frei[0].removeprefix("GS-")),
        ("Zimmerfreigabe entfällt", frei[5].removeprefix("GS-"))])
    assert all(not u.entscheidbar for u in us)
    assert "Sperrung" in pa.zusammenfassung(us) and "Zimmerfreigabe" in pa.zusammenfassung(us)


def test_umzug_im_programm_ist_keine_doppelbelegung(welt):
    """6.27.2: Umzug im Programm (im Gebäudeplan noch nicht nachgetragen) – das alte Zimmer ist frei; wer danach dort
    eingeplant ist, steht nicht als Doppelbelegung da. Der Umzug bleibt nach dem Übernehmen bestehen."""
    from belegung import assistenz, umzug
    from belegung import planabgleich as pa
    from belegung import zimmerplan as zp

    alt, frei, _ = welt
    st = zp.laden()
    anna = next(x for x in st.lage.belegungen[frei[0]] if x.name == "Altbestand, Anna")
    umzug.speichern(st, anna, frei[4], date(2026, 10, 20), "Test")
    st = zp.laden()
    vs = assistenz.verstehen_alle(f"Neu, Nora vom 21.10.2026 bis 31.01.2027 in {frei[0].removeprefix('GS-')}",
                                  {z.id for z in st.zimmer}, HEUTE)
    for a in vs[0].aktionen:
        a.an = True
    assistenz.ausfuehren(vs, HEUTE)
    neu = _neu(alt, alt.belegungen)                          # Gebäudeplan kennt den Umzug noch nicht
    us = pa.vergleichen(neu, zp.laden(), HEUTE)
    assert not any(u.art == "konflikt" for u in us)
    anna_u = next(u for u in us if u.name == "Altbestand, Anna")
    assert anna_u.art == "zimmer" and "(Umzug im Programm)" in anna_u.system and "nachtragen" in anna_u.info
    assert not anna_u.entscheidbar
    pa.anwenden(neu, us)
    wo = {x.zimmer for bs in zp.laden().lage.belegungen.values() for x in bs
          if x.name == "Altbestand, Anna" and x.bis >= HEUTE}
    assert wo == {frei[4]}
