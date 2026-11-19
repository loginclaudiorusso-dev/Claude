"""0.82 – Facility-Checks: Zeitraum wählbar (auch ältere offene und eigener Zeitraum), Filter, Druck in der
Reihenfolge vom Bildschirm."""

from datetime import date
from pathlib import Path

from belegung import eintragen

from modern import seiten_kern as sk

MOD = Path(__file__).resolve().parent.parent / "modern"
HEUTE = date(2026, 11, 9)


def test_zeitraeume():
    assert sk.fc_zeitraum("sechs", HEUTE) == (date(2026, 10, 26), date(2026, 12, 24))      # wie bisher
    von, bis = sk.fc_zeitraum("offen", HEUTE)
    assert (HEUTE - von).days == sk.FC_ZURUECK and bis == date(2026, 12, 24)
    assert sk.fc_zeitraum("woche", HEUTE) == sk.zeitraum("woche", HEUTE)
    assert sk.fc_zeitraum("eigen", HEUTE, date(2026, 12, 1), date(2026, 11, 1)) == (date(2026, 11, 1), date(2026, 12, 1))
    assert sk.fc_zeitraum("eigen", HEUTE) == sk.fc_zeitraum("sechs", HEUTE)                   # ohne Daten: Standard
    assert set(sk.FC_ZEITRAUM) == {"offen", "woche", "naechste", "sechs", "eigen"}


def test_druck_in_bildschirm_reihenfolge():
    cs = [eintragen.FacilityCheck("1|103", "Erfunden, A", "Kurs X", date(2026, 3, 1), date(2026, 11, 10)),
          eintragen.FacilityCheck("1|101", "Erfunden, B", "Kurs Y", date(2026, 2, 1), date(2026, 11, 12), haken=True),
          eintragen.FacilityCheck("1|102", "Erfunden, C", "Kurs Z", date(2026, 1, 1), date(2026, 11, 11))]
    reihe = [cs[1].schluessel, cs[2].schluessel, cs[0].schluessel]
    t = sk.facility_html(sk.in_reihenfolge(cs, reihe, sk.fc_schluessel), HEUTE, HEUTE, HEUTE, "Zimmer")
    assert t.index("Erfunden, B") < t.index("Erfunden, C") < t.index("Erfunden, A")
    assert "sortiert nach Zimmer" in t and "davon 2 offen" in t and "☑" in t


def test_oberflaeche():
    q = (MOD / "seiten.py").read_text(encoding="utf-8")
    assert "sk.FC_ZEITRAUM" in q and "_fc_drucken" in q and "attr(zeile, data_rg=c.schluessel)" in q
    assert "a.fc_filter" in q and "type=date" in q
