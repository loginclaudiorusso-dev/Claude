"""0.35: Standorte – getrennte Datenordner, Gebäudeplan-Formate Bad Pyrmont/Weser-Ems, neutrale Regeln. Erfundene Daten."""

from datetime import date, timedelta

import pytest

BP_ZEILEN = """Gebäudeplan
A Gebäude
01. Etage
BP-A 103
1 Bett
Probe, Paula (BP KBM 2601)
01.10.2030 - 31.03.2031
Belegt
BP-A 104
1 Bett
Frei
BP-A 105
2 Betten
Frei
C Gebäude
Erdgeschoß
BP-C 0.18
1 Bett
30.06.2030 - 31.12.2099
Gesperrt
Untergeschoß
BP-C U.06
1 Bett
Frei""".split("\n")

WE_ZEILEN = """Internat A
01. Etage
WE-A 202 R
1 Bett
Muster, Max (WE VW 2601)
01.10.2030 - 31.03.2031
Belegt
WE-A 203 L
1 Bett
Frei
Internat E
Erdgeschoß
WE-E 099 - Testinsel
1 Bett
Frei""".split("\n")


@pytest.fixture
def standorte(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import standort_kern as sk

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    sk.installieren()
    aenderungen.verlauf_leeren()
    yield tmp_path
    sk.waehlen("GS", merken_=False)
    aenderungen.verlauf_leeren()


def test_bad_pyrmont_eigener_ordner_und_format(standorte):
    from belegung import gebaeudeplan, speicher
    from belegung import zimmerplan as zp
    from modern import standort_kern as sk

    sk.waehlen("BP", merken_=False)
    assert speicher.pfad("x") == standorte / "Standorte" / "BP" / "x"
    assert zp.laden().zimmer == []                         # keine Goslar-Zimmer im neuen Standort
    plan = gebaeudeplan.parse_zeilen(BP_ZEILEN, "bp.docx", date(2030, 10, 1))
    assert [(z.id, z.haus, z.etage, z.nr, z.betten) for z in plan.zimmer] == [
        ("BP-A 103", "A", "1", "103", 1), ("BP-A 104", "A", "1", "104", 1), ("BP-A 105", "A", "1", "105", 2),
        ("BP-C 0.18", "C", "E", "0.18", 1), ("BP-C U.06", "C", "U", "U.06", 1)]
    assert {b.art for b in plan.belegungen} == {"belegt", "gesperrt"}
    gebaeudeplan.speichern(plan, {"quelle": "bp.docx"})
    st = zp.laden()
    assert len(st.zimmer) == 5 and not any(z.gaeste for z in st.zimmer)
    assert sk.daten_text("BP") == "5 Zimmer"
    sk.waehlen("GS", merken_=False)                       # Goslar: wieder die eigenen Zimmer, unberührt
    assert speicher.pfad("x") == standorte / "x"
    assert zp.laden().zimmer[0].id.startswith("GS-")


def test_weser_ems_format_und_zimmereingabe(standorte):
    from belegung import gebaeudeplan
    from modern import standort_kern as sk

    sk.waehlen("WE", merken_=False)
    plan = gebaeudeplan.parse_zeilen(WE_ZEILEN, "we.docx", date(2030, 10, 1))
    ids = [z.id for z in plan.zimmer]
    assert ids == ["WE-A 202 R", "WE-A 203 L", "WE-E 099 - Testinsel"]
    assert sk.kurz("WE-A 202 R") == "A 202 R" and sk.kurz("GS-3.2-111") == "3.2-111"
    assert sk.zimmer_aus_text(ids, "a 202r") == "WE-A 202 R"
    assert sk.zimmer_aus_text(ids, "A-203-L") == "WE-A 203 L"
    assert sk.zimmer_aus_text(ids, "Z 999") is None


def test_neutrale_regeln_ausserhalb_von_goslar(standorte):
    from belegung import zimmerplan as zp
    from modern import standort_kern as sk

    sk.waehlen("BP", merken_=False)
    z = zp.Zimmer("BP-A 103", "A", "1", "103")
    assert zp.erlaubt(z, "Reha") and zp.erlaubt(z, "Gast") and zp.erlaubt(z, "EMR")
    assert not zp.erlaubt(zp.Zimmer("BP-A 105", "A", "1", "105", 2), "Reha")     # Doppelzimmer: nur UWT/Gast
    assert not zp.erlaubt(zp.Zimmer("BP-A 106", "A", "1", "106", gaeste=True), "Reha")
    sk.waehlen("GS", merken_=False)
    assert not zp.erlaubt(z, "Reha")                       # Goslar-Regeln wieder aktiv (Haus „A“ gibt es dort nicht)


def test_prognose_liest_immer_aus_goslar(standorte):
    from belegung import speicher
    from modern import standort_kern as sk

    sk.waehlen("WE", merken_=False)
    with sk.haupt():
        assert speicher.pfad("x") == standorte / "x"
    assert speicher.pfad("x") == standorte / "Standorte" / "WE" / "x"
    sk.merken("BP")
    assert sk.gemerkt() == "BP"


def test_zimmer_pruefen_mit_kurzform(standorte):
    from belegung import anreiseliste, gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import standort_kern as sk

    sk.waehlen("BP", merken_=False)
    gebaeudeplan.speichern(gebaeudeplan.parse_zeilen(BP_ZEILEN, "bp.docx", date.today()), {"quelle": "bp.docx"})
    an = date.today() + timedelta(days=3)
    anreiseliste.speichern([anreiseliste.Person("Neu, Nora", "BP KBM 2611", an, True, tn_id="991",
                                                abreise=an + timedelta(days=90))], {})
    st = zp.laden()
    b = st.bedarf[0]
    erg = kern.zimmer_pruefen(st, b.schluessel, "a104")
    assert erg.zimmer == "BP-A 104" and erg.art == "passt", erg.text


def test_haeuser_alphabetisch(standorte):
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import standort_kern as sk

    sk.waehlen("BP", merken_=False)
    gebaeudeplan.speichern(gebaeudeplan.parse_zeilen(BP_ZEILEN, "bp.docx", date(2030, 10, 1)), {"quelle": "bp.docx"})
    assert [z.haus for z in zp.laden().zimmer] == ["A", "A", "A", "C", "C"]
