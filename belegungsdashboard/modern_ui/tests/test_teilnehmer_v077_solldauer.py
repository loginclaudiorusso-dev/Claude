"""0.77 – Solldauer aus der Zimmerbelegung je Kursfamilie, Gruppe „Ignoriert“, Obergrenze nur VW."""

from datetime import date, timedelta

from modern import bestand_kern as bk

H = date(2026, 3, 2)


def _e(massnahme, tage, quelle="Anmeldung", n=4):
    return [(massnahme, H + timedelta(days=7 * i), H + timedelta(days=7 * i + tage - 1), quelle) for i in range(n)]


def test_familie_und_messung():
    assert bk.familie("GS ASS PS 260909") == "GS ASS PS" and bk.familie("GS RVT 2601") == "GS RVT"
    g = bk.anmeldedauern(_e("GS ASS PS 260909", 28) + _e("GS EMR ASS 261109", 3) + _e("GS RVT 2601", 91)
                         + _e("GS ASPQ 2602", 42, "Gebäudeplan", 5) + _e("GS ASPQ 2603", 40, "Anmeldung", 2))
    assert g["GS ASS PS"].median == 28 and g["GS ASS PS"].quelle == "Anmeldung"
    assert g["GS EMR ASS"].median == 3 and g["GS RVT"].median == 91
    assert g["GS ASPQ"].quelle == "Gebäudeplan" and g["GS ASPQ"].n == 5      # < 3 Anmeldungen → Gebäudeplan
    assert bk.anmeldedauern([("", H, H, "Anmeldung"), ("GS X 2601", H, H - timedelta(days=1), "Anmeldung")]) == {}


def test_soll_je_kurs_aus_anmeldung():
    t = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
    g = bk.anmeldedauern(_e("GS ASS PS 260909", 28) + _e("GS ASS 2601", 42) + _e("GS EMR ASS 261109", 3))
    assert bk.soll_tage("GS ASS PS 261001", bk.zuordnen("GS ASS PS 261001", t), g) == (28, "Anmeldung, n = 4")
    assert bk.soll_tage("GS ASS 2611", bk.zuordnen("GS ASS 2611", t), g)[0] == 42
    assert bk.zuordnen("GS EMR ASS 261109", t)["art"] == "EMR-Assessment"           # EMR vor ASS
    assert bk.soll_tage("GS EMR ASS 261109", bk.zuordnen("GS EMR ASS 261109", t), g)[0] == 3
    assert bk.soll_tage("GS RVT 2601", bk.zuordnen("GS RVT 2601", t), {}) == (91, "Tabelle")   # ohne Messung: Tabelle
    assert bk.soll_tage("GS CNC 2601", bk.zuordnen("GS CNC 2601", t), g) == (730, "Tabelle")


def test_ignoriert_und_vw():
    t = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
    assert bk.zuordnen("GS JobTrain 20", t)["gruppe"] == "Ignoriert"
    vw = bk.zuordnen("GS VW 2506", t)
    assert vw["gruppe"] == "Hauptmaßnahme" and vw["max_plaetze"] == 24 and not vw["offen"]
    assert [e["muster"] for e in t if e["offen"]] == []
    a = [bk.Aufenthalt(1, "GS JobTrain 20", H, H + timedelta(days=90), 60, 0, 0),
         bk.Aufenthalt(2, "GS ASS PS 260302", H, H + timedelta(days=27), 28, 8, 0)]
    r = bk.bericht(a, {"bis": "2026-12-31"}, t, date(2026, 12, 31), bk.anmeldedauern(_e("GS ASS PS 260909", 28)))
    assert r.ignoriert == (1, 1) and [z.art for z in r.arten] == ["Assessment"]
    assert r.arten[0].soll_text == "28 Tage (Anmeldung, n = 4)" and not r.nicht_zugeordnet
    assert [m.familie for m in r.gemessen] == ["GS ASS PS"]


def test_startwerte_vollstaendig():
    for e in bk.tabelle({}):                                      # ohne eigene Tabelle: Startwerte, alle Felder da
        assert {"muster", "art", "gruppe", "soll_tage", "standort", "offen", "soll_quelle", "max_plaetze"} <= set(e)
