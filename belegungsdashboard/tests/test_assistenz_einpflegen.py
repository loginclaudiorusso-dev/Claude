"""6.23: Assistenz pflegt Personen ein – „Name vom … bis … in 2-408“ wird eine echte Belegung im Zimmerplan
(nicht nur eine Erinnerung). Nur erfundene Namen."""

from datetime import date

import pytest

HEUTE = date(2026, 10, 19)


@pytest.fixture
def stand(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import zimmerplan as zp

    st = zp.laden()
    probe = zp.Bedarf("x", "x", "", "Reha", date(2025, 6, 26), date(2027, 6, 24), "m")
    frei = [z for z in st.zimmer if z.aktiv and z.betten == 1 and zp.passt(st.lage, z, probe) is None]
    return {z.id for z in st.zimmer}, frei


def test_erkennt_person_zeitraum_und_zimmer(stand):
    from belegung import assistenz

    bekannt, frei = stand
    kurz = frei[0].id.removeprefix("GS-")
    haus, nr = kurz.rsplit("-", 1)
    for text in (f"Beispiel, Kai Leon vom 26.06.2025 bis 24.06.2027 in haus {kurz}",
                 f"Beispiel, Kai Leon 26.06.2025 24.06.2027 Haus {haus} Zimmer {nr}"):
        v = assistenz.verstehen(text, bekannt, HEUTE)
        assert (v.name, v.von, v.bis, v.zimmer) == ("Beispiel, Kai Leon", date(2025, 6, 26), date(2027, 6, 24), [frei[0].id])
        assert [a.art for a in v.aktionen] == ["einpflegen"] and v.aktionen[0].an
        assert "gleich als belegt" in v.aktionen[0].text
    v = assistenz.verstehen(f"Probe, Lena ab 1.12.26 {kurz} einpflegen Mieterin Frau", bekannt, HEUTE)
    d = v.aktionen[0].daten
    assert (v.bis, d["massnahme"], d["geschlecht"], d["belegt"]) == (None, "Miete Goslar", "w", False)
    # kein Name: „Fliegen, Tür klemmt“ bleibt ein Mangel-Auftrag
    v = assistenz.verstehen(f"{kurz} Fliegen, Tür klemmt bis 1.11.26", bekannt, HEUTE)
    assert v.name == "" and "mangel" in [a.art for a in v.aktionen]
    # Name ohne Zimmer: Hinweis statt Erinnerung
    v = assistenz.verstehen("Beispiel, Kai vom 1.11.26 bis 30.4.27", bekannt, HEUTE)
    assert v.aktionen == [] and "Zimmer" in v.hinweise[0]


def test_einpflegen_belegt_und_rueckgaengig(stand):
    from belegung import anreiseliste, assistenz
    from belegung import zimmerplan as zp

    bekannt, frei = stand
    zid = frei[0].id
    v = assistenz.verstehen(f"Beispiel, Kai vom 26.06.2025 bis 24.06.2027 in {zid.removeprefix('GS-')}", bekannt, HEUTE)
    e = assistenz.ausfuehren([v], HEUTE)
    st = zp.laden()
    b = [x for x in st.lage.belegungen[zid] if x.name == "Beispiel, Kai"]
    assert len(b) == 1 and (b[0].art, b[0].von, b[0].bis) == ("belegt", date(2025, 6, 26), date(2027, 6, 24))
    # zweites Mal in ein anderes Zimmer: wird umgetragen, nicht doppelt
    v2 = assistenz.verstehen(f"Beispiel, Kai vom 26.06.2025 bis 24.06.2027 in {frei[1].id.removeprefix('GS-')}",
                             bekannt, HEUTE)
    assert v2.aktionen[0].an and any("umgetragen" in h for h in v2.hinweise)
    # gleiches Zimmer, längerer Zeitraum: Verlängerung, kein Konflikt
    v4 = assistenz.verstehen(f"Beispiel, Kai vom 26.06.2025 bis 30.09.2027 in {zid.removeprefix('GS-')}", bekannt, HEUTE)
    assert v4.aktionen[0].an and any("wird auf 26.06.2025 – 30.09.2027 gesetzt" in h for h in v4.hinweise)
    # belegtes Zimmer für jemand anderen: Warnung, Haken aus
    v3 = assistenz.verstehen(f"Probe, Lena vom 1.11.26 bis 30.4.27 in {zid.removeprefix('GS-')}", bekannt, HEUTE)
    assert not v3.aktionen[0].an and any("belegt" in h for h in v3.hinweise)
    assert assistenz.rueckgaengig(e["id"]) == 1
    assert anreiseliste.laden()[0] == [] and zp.zuweisungen_laden() == []
    assert not [x for x in zp.laden().lage.belegungen[zid] if x.name == "Beispiel, Kai"]


def test_vorhandene_person_wird_uebernommen(stand):
    from belegung import anreiseliste, assistenz
    from belegung import zimmerplan as zp

    bekannt, frei = stand
    alt = anreiseliste.Person("Beispiel, Kai", "GS VW 2611", date(2026, 11, 2), True, tn_id="T-1")
    anreiseliste.person_speichern(alt)
    v = assistenz.verstehen(f"Beispiel, Kai vom 2.11.26 bis 30.4.27 in {frei[0].id.removeprefix('GS-')}", bekannt, HEUTE)
    assert any("Personenliste" in h for h in v.hinweise)
    e = assistenz.ausfuehren([v], HEUTE)
    personen = anreiseliste.laden()[0]
    assert len(personen) == 1 and personen[0].tn_id == "T-1" and personen[0].abreise == date(2027, 4, 30)
    assert personen[0].massnahme == "GS VW 2611"
    assert [z["zimmer"] for z in zp.zuweisungen_laden()] == [frei[0].id]
    assistenz.rueckgaengig(e["id"])
    personen = anreiseliste.laden()[0]
    assert len(personen) == 1 and personen[0].abreise is None and zp.zuweisungen_laden() == []


@pytest.mark.parametrize("text, frage", [
    ("Wie viele Plätze sind im November in Goslar frei?", True),
    ("Belegung Goslar im Oktober", True),
    ("welche Zimmer sind morgen frei", True),
    ("6-403 Fliegen beseitigen bis 1.11.26", False),
    ("Beispiel, Kai vom 1.11.26 bis 30.4.27 in 2-408", False),
    ("Freitag 10 Uhr Teambesprechung", False),
])
def test_frage_oder_auftrag(text, frage):
    from belegung import assistenz

    assert assistenz.ist_frage(text) is frage


def test_zweiter_aufenthalt_ist_eigene_zeile(stand):
    from belegung import anreiseliste, assistenz

    bekannt, frei = stand
    kurz = frei[0].id.removeprefix("GS-")
    zeilen = [f"Beispiel, Kai vom 26.06.2025 bis 30.09.2026 in {kurz}", f"Beispiel, Kai vom 1.4.27 bis 24.6.27 in {kurz}"]
    assistenz.ausfuehren([assistenz.verstehen(z, bekannt, HEUTE) for z in zeilen], HEUTE)
    assert sorted(p.anreise for p in anreiseliste.laden()[0]) == [date(2025, 6, 26), date(2027, 4, 1)]


@pytest.mark.parametrize("text, erwartet", [
    ("25.-30.01.2027", [date(2027, 1, 25), date(2027, 1, 30)]),
    ("25.01. – 30.01.2027", [date(2027, 1, 25), date(2027, 1, 30)]),
    ("28.12. - 03.01.2027", [date(2026, 12, 28), date(2027, 1, 3)]),
    ("vom 19.12.2026 bis 02.01.2027", [date(2026, 12, 19), date(2027, 1, 2)]),
])
def test_zeitraeume(text, erwartet):
    from belegung import assistenz

    assert assistenz._alle_daten(text, HEUTE) == erwartet


def test_vorname_nachname_reservierung_und_kopfzeile(stand):
    """6.25: so, wie der Nutzer schreibt – Kopfzeile mit Zeitraum, darunter Zimmer mit „Gast reserviert“ oder
    „Vorname Nachname“; vorher wurde daraus nur ein Termin bzw. eine Notiz."""
    from belegung import assistenz
    from belegung import zimmerplan as zp

    bekannt, _frei = stand
    st = zp.laden()
    probe = zp.Bedarf("x", "x", "Gast", "Gast", date(2026, 12, 1), date(2027, 2, 28), "m")
    frei = [z for z in st.zimmer if z.aktiv and z.betten == 1 and not z.nur_maenner
            and zp.passt(st.lage, z, probe) is None]                          # Gästezimmer
    a, b, c = (z.id.removeprefix("GS-") for z in frei[:3])
    text = f"25.01.2027 – 30.01.2027 Tagung\n{a} Tagung Gast reserviert\n{b} Gast reserviert\nKai Leon Beispiel {c}"
    vs = assistenz.verstehen_alle(text, bekannt, HEUTE)
    assert vs[0].kopf and vs[0].aktionen == [] and "3 Zeile(n)" in vs[0].hinweise[0]
    assert [v.reservierung for v in vs[1:3]] == ["Tagung", "Tagung"]        # Bezeichnung auch aus der Kopfzeile
    assert vs[3].name == "Beispiel, Kai Leon" and (vs[3].von, vs[3].bis) == (date(2027, 1, 25), date(2027, 1, 30))
    assert all(len(v.aktionen) == 1 and v.aktionen[0].art == "einpflegen" for v in vs[1:])
    assert vs[1].aktionen[0].daten["massnahme"] == "Gast reserviert"
    assert vs[3].aktionen[0].daten["massnahme"] == "Gast" and "Gästezimmer" in vs[3].hinweise[0]   # Gästezimmer → Gast
    e = assistenz.ausfuehren(vs, HEUTE)
    st = zp.laden()
    namen = {x.name for z in frei[:3] for x in st.lage.belegungen[z.id] if x.von == date(2027, 1, 25)}
    assert namen == {f"Tagung ({a})", f"Tagung ({b})", "Beispiel, Kai Leon"}
    assert assistenz.rueckgaengig(e["id"]) == 3 and zp.zuweisungen_laden() == []
    # mehrere Zimmer in einer Zeile, „ / “ als Trenner
    v = assistenz.verstehen(f"{a}, {b} Tagung reserviert 25.-30.01.2027", bekannt, HEUTE)
    assert [x.daten["zimmer"] for x in v.aktionen] == [frei[0].id, frei[1].id]
    vs = assistenz.verstehen_alle(f"19.12.2026 bis 02.01.2027\nKai Beispiel {a} / Lena Probe {b}", bekannt, HEUTE)
    assert [v.name for v in vs[1:]] == ["Beispiel, Kai", "Probe, Lena"]
    # zwei Blöcke: jede Kopfzeile zählt nur ihre eigenen Zeilen
    vs = assistenz.verstehen_alle(f"25.-30.01.2027 Tagung\n{a} reserviert\n{b} reserviert\n"
                                  f"1.-5.2.2027\n{c} reserviert", bekannt, HEUTE)
    assert "2 Zeile(n)" in vs[0].hinweise[0] and "1 Zeile(n)" in vs[3].hinweise[0]
    assert (vs[4].von, vs[4].bis) == (date(2027, 2, 1), date(2027, 2, 5))


def test_keine_falschen_namen(stand):
    from belegung import assistenz

    bekannt, frei = stand
    kurz = frei[0].id.removeprefix("GS-")
    for text in (f"{kurz} Fliegen Beseitigen bis 1.11.26", f"am 3.11. Grundreinigung {kurz}",
                 f"morgen Schlüssel {kurz} an FM übergeben", f"{kurz} Tür klemmt Freitag"):
        v = assistenz.verstehen(text, bekannt, HEUTE)
        assert not v.name and not v.reservierung, text
    assert not assistenz._klarname("Verkehrsgerichtstag Gast reserviert")
    assert assistenz._klarname("Lena Marie Testfall") == "Testfall, Lena Marie"
