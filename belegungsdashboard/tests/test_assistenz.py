"""6.22: Assistenz – normale Eingaben verstehen und in Kalender, Mängel und Zimmernotizen umsetzen (mit Rückgängig)."""

from datetime import date

import pytest

HEUTE = date(2026, 10, 18)          # ein Sonntag
BEKANNT = {"GS-6-403", "GS-3.1-E02", "GS-2-115", "GS-2-204", "GS-3.2-108"}


def _v(text):
    from belegung import assistenz

    return assistenz.verstehen(text, BEKANNT, HEUTE)


@pytest.mark.parametrize("text, zimmer, datum, frist, mangel", [
    ("6-403 Fliegen beseitigen bis 1.11.26", ["GS-6-403"], date(2026, 11, 1), True, "ungeziefer"),
    ("3.1-E02 Rollo defekt", ["GS-3.1-E02"], None, False, "fenster"),
    ("morgen Schlüssel 2-204 an FM übergeben", ["GS-2-204"], date(2026, 10, 19), False, ""),   # Aufgabe, kein Mangel
    ("Zimmer 108 Schimmel prüfen bis Ende des Monats", ["GS-3.2-108"], date(2026, 10, 31), True, "schimmel"),
    ("am 3.11. Grundreinigung 2-204", ["GS-2-204"], date(2026, 11, 3), False, "grundreinigung"),
    ("Freitag Teambesprechung", [], date(2026, 10, 23), False, ""),
    ("6-403 Tür klemmt in 3 Tagen prüfen", ["GS-6-403"], date(2026, 10, 21), False, "tuer"),
    ("3.1.27 2-115 Heizung kalt", ["GS-2-115"], date(2027, 1, 3), False, "heizung"),
])
def test_verstehen(text, zimmer, datum, frist, mangel):
    v = _v(text)
    assert (v.zimmer, v.datum, v.frist, v.mangel) == (zimmer, datum, frist, mangel)


def test_uhrzeit_und_hinweise():
    v = _v("Freitag 10:30 Teambesprechung")
    assert v.uhrzeit == "10:30" and v.aufgabe == "Teambesprechung"
    assert any("10:30 Uhr – Teambesprechung" in a.text for a in v.aktionen)
    assert _v("irgendwas ohne alles").aktionen == [] and _v("irgendwas ohne alles").hinweise
    assert any("mehreren" in h for h in _v("Zimmer 403 Licht defekt").hinweise) or _v("Zimmer 403 Licht defekt").zimmer


def test_ausfuehren_und_rueckgaengig(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import assistenz, maengel, termine
    from belegung import zimmerplan as zp

    v = _v("6-403 Fliegen beseitigen bis 1.11.26")
    assert [a.art for a in v.aktionen] == ["termin", "mangel", "sperren", "notiz"]
    assert all(a.an for a in v.aktionen)                    # Ungeziefer sperrt von sich aus
    e = assistenz.ausfuehren([v], HEUTE)
    t = termine.eigene()
    assert len(t) == 1 and t[0].titel == "Frist: 6-403: Fliegen beseitigen" and t[0].datum == date(2026, 11, 1)
    assert t[0].erinnern_am == date(2026, 10, 30)
    m = maengel.offen("GS-6-403")
    assert [(x.art, x.unbewohnbar) for x in m] == [("ungeziefer", True)] and "bis 01.11.2026" in m[0].notiz
    assert termine.notizen(zp.zimmer_schluessel("GS-6-403"))[0].text == "Fliegen beseitigen – bis 01.11.2026"
    # erledigt: Mangel behoben, Frist abgehakt
    fertig = _v("6-403 Fliegen erledigt")
    assert {a.art for a in fertig.aktionen} >= {"behoben", "termin_erledigt"}
    e2 = assistenz.ausfuehren([fertig], HEUTE)
    assert maengel.offen("GS-6-403") == [] and termine.eigene()[0].erledigt
    # Rückgängig: erst „erledigt“, dann der Auftrag selbst
    assert assistenz.rueckgaengig(e2["id"]) >= 2
    assert maengel.offen("GS-6-403") and not termine.eigene()[0].erledigt
    assistenz.rueckgaengig(e["id"])
    assert termine.eigene() == [] and maengel.offen("GS-6-403") == []
    assert termine.notizen(zp.zimmer_schluessel("GS-6-403")) == []
    assert assistenz.rueckgaengig(e["id"]) == 0             # zweimal geht nicht
