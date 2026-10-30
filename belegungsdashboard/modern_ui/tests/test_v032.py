"""0.32: Eigene Planung widerspricht dem Gebäudeplan – nie wieder still „frei“. Erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def fall(tmp_path, monkeypatch):
    """Person laut eigener Planung in 2-505, laut Gebäudeplan in 2-209 (wie im gemeldeten Fall)."""
    from belegung import aenderungen, anreiseliste, gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    h = date.today()
    an, ab = h - timedelta(days=8), h + timedelta(days=80)
    anreiseliste.speichern([anreiseliste.Person("Strittig, Stefan", "GS iBTZ", an, True, tn_id="990", abreise=ab),
                            anreiseliste.Person("Andere, Anna", "GS iBTZ", h + timedelta(days=2), True, tn_id="991",
                                                abreise=h + timedelta(days=60))], {})
    p = next(b for b in zp.laden().bedarf if b.name == "Strittig, Stefan")
    kern.zuweisen(p.schluessel, "GS-2-505")
    gebaeudeplan.speichern(gebaeudeplan.Gebaeudeplan("Plan.docx", h - timedelta(days=1), zp.mitgelieferte_zimmer(), [
        gebaeudeplan.Belegung("GS-2-209", an, ab, "belegt", "Strittig, Stefan", "GS IBTZ 26")]))
    aenderungen.verlauf_leeren()
    yield h, p.schluessel
    aenderungen.verlauf_leeren()


def test_widerspruch_wird_erkannt_und_zimmer_geschuetzt(fall):
    from belegung import zimmerplan as zp
    from modern import kern

    h, person = fall
    st = zp.laden()
    assert st.lage.status_am("GS-2-505", h)[0] == "frei"          # so rechnet das Hauptprogramm (Gebäudeplan gilt still)
    sts = kern.strittige(st)
    assert [(x.geplant, x.gebucht) for x in sts] == [("GS-2-505", "GS-2-209")]
    anna = next(b for b in st.bedarf if b.name == "Andere, Anna")
    with pytest.raises(ValueError, match="klären"):
        kern.zuweisen(anna.schluessel, "GS-2-505")                  # früher: Doppelbelegung möglich
    zeile = next(z for z in kern.zeilen(st, anna.von.isoformat(), h) if z.schluessel == anna.schluessel)
    assert "GS-2-505" not in {o.zimmer for o in zeile.optionen} and zeile.vorschlag != "GS-2-505"
    assert kern.zimmer_pruefen(st, anna.schluessel, "2-505").art == "nein"
    eigen = next(z for z in kern.zeilen(st, st.bedarf[0].von.isoformat(), h) if z.schluessel == person)
    assert eigen.status == "handeln" and "Gebäudeplan: 2-209" in eigen.grund
    assert any(k.id == "strittig" and k.stufe == "dringend" for k in kern.karten(st, h))


def test_planung_stimmt(fall):
    from belegung import zimmerplan as zp
    from modern import kern

    h, person = fall
    kern.strittig_klaeren(person, "planung")
    st = zp.laden()
    assert not kern.strittige(st)
    assert st.lage.status_am("GS-2-505", h)[0] != "frei" and st.lage.status_am("GS-2-209", h)[0] == "frei"
    kern.rueckgaengig()
    assert kern.strittige(zp.laden())


def test_gebaeudeplan_stimmt(fall):
    from belegung import zimmerplan as zp
    from modern import kern

    h, person = fall
    kern.strittig_klaeren(person, "plan")
    st = zp.laden()
    assert not kern.strittige(st) and st.zugewiesen(person)["zimmer"] == "GS-2-209"
    assert st.lage.status_am("GS-2-209", h)[0] != "frei"
    with pytest.raises(ValueError):
        kern.strittig_klaeren(person, "plan")                       # schon geklärt


def _schluesselliste(pfad, zeilen):
    """Erfundene Liste im Aufbau des Empfangs: Leerzeile, Kopf, Leerzeile, Zeilen."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([None] * 9)
    ws.append(["Anreise", "Abreise", "An", "Ab", "Zimmer", "Name", "Unterschrift", "Pförtner", "Bemerkung"])
    ws.append([None] * 9)
    for an, ab, zimmer, name in zeilen:
        ws.append([an, ab, "X", None, zimmer, name, None, None, None])
    wb.save(pfad)
    return pfad


def test_schluesselliste_korrigiert_planung(fall, tmp_path):
    from datetime import datetime

    from belegung import zimmerplan as zp
    from modern import kern
    from modern import schluessel_kern as sk

    h, person = fall
    an, ab = h - timedelta(days=8), h + timedelta(days=80)
    d = lambda x: datetime(x.year, x.month, x.day)                    # noqa: E731 – wie Excel
    liste = _schluesselliste(tmp_path / "Schluessel.xlsx", [
        (d(an), d(ab), "2-505", "Strittig, Stefan"),                  # Schlüssel für 2-505 → Planung stimmt
        (d(h + timedelta(days=2)), d(h + timedelta(days=60)), "NEU 3.2-111", "Andere, Anna"),   # noch ohne Zimmer
        (d(h), d(h + timedelta(days=5)), "2-601", "Unbekannt, Udo")])
    st = zp.laden()
    eintraege = sk.lesen(liste, "Schluessel.xlsx", st)
    assert [e.zimmer for e in eintraege] == ["GS-2-505", "GS-3.2-111", "GS-2-601"]
    punkte = {p.e.name: p for p in sk.vergleichen(st, eintraege)}
    assert punkte["Strittig, Stefan"].art == "korrigieren" and "Gebäudeplan 2-209" in punkte["Strittig, Stefan"].text
    assert punkte["Andere, Anna"].art == "korrigieren" and "ohne Zimmer" in punkte["Andere, Anna"].text
    assert punkte["Unbekannt, Udo"].art == "unbekannt"
    sk.uebernehmen(list(punkte.values()))
    st = zp.laden()
    assert not kern.strittige(st)                                       # Widerspruch durch die Schlüsselliste geklärt
    assert st.lage.status_am("GS-2-505", h)[0] != "frei" and st.lage.status_am("GS-2-209", h)[0] == "frei"
    anna = next(b for b in st.bedarf if b.name == "Andere, Anna")
    assert st.zugewiesen(anna.schluessel)["zimmer"] == "GS-3.2-111"
    again = {p.e.name: p.art for p in sk.vergleichen(st, sk.lesen(liste, "Schluessel.xlsx", st))}
    assert again["Strittig, Stefan"] == "stimmt" and again["Andere, Anna"] == "stimmt"
    kern.rueckgaengig()                                                 # ein Schritt für alles
    assert kern.strittige(zp.laden())
