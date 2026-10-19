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
