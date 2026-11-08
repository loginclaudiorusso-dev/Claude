"""0.76 – Bestandsmodell Schritt 1: Aufenthalte je Person (nur Nummern), Kursnamen lesen, Zuordnungstabelle,
Prüfbericht (Wochenenden, künftige Tage, auffällige Fälle, nicht zugeordnete Kurse). Alles mit erfundenen Daten."""

import json
from datetime import date, timedelta

from modern import bestand_kern as bk
from modern import massnahmen_kern as mk


def test_kurs_info():
    assert bk.kurs_info("GS EMR ASS 261109") == bk.KursInfo("GS", date(2026, 11, 9), True)
    assert bk.kurs_info("GS CNC 2001") == bk.KursInfo("GS", date(2020, 1, 1), False)
    assert bk.kurs_info("GS BFS 190227").start == date(2019, 2, 27)
    assert bk.kurs_info("GS JobTrain 20").start is None
    assert bk.kurs_info("GS XY 991399").start is None                 # Monat 13 → nicht lesbar
    assert bk.kurs_info("Zerspanungsmechaniker/-in EG Drehmaschinensysteme") == bk.KursInfo(None, None, False)


def test_muster_und_zuordnung():
    t = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
    assert bk.zuordnen("GS EMR ASS 261109", t)["gruppe"] == "Assessment"
    assert bk.zuordnen("GS ASS PS 260527", t)["art"] == "Assessment"
    assert bk.zuordnen("GS KLASSE 2001", t) is None                  # „ASS“ nur als ganzes Kürzel
    assert bk.zuordnen("Bauhelfer/-in für Flüchtlinge und Migranten", t)["art"] == "Bauhelfer"   # Teiltext ab 5 Zeichen
    assert bk.zuordnen("GS M-GA 1909", t)["gruppe"] == "Hauptmaßnahme"
    assert bk.passt("re:^GS IB", "GS IBTZ 1901") and not bk.passt("re:[", "x")
    eigen = bk.tabelle_bereinigen([{"muster": "CNC", "art": "CNC Bad", "gruppe": "Hauptmaßnahme", "soll_tage": "700",
                                    "standort": "bp"}] + t)
    assert bk.zuordnen("BP CNC 2001", eigen)["art"] == "CNC Bad" and bk.zuordnen("GS CNC 2001", eigen)["art"] != "CNC Bad"
    assert eigen[0]["soll_tage"] == 700 and eigen[0]["standort"] == "BP"
    assert bk.tabelle_bereinigen([{"muster": ""}, "quatsch", {"muster": "X", "gruppe": "falsch"}])[0]["gruppe"] == "Sonstige"


def test_sammler_personen_teilsummen_langnamen():
    von = date(2026, 1, 1)
    s = bk.Sammler(von, date(2026, 3, 1))
    s.zeile("Erfunden, Anna", [], False)                  # Person ohne Werte
    s.zeile("GS ASS PS 260105", list(range(4, 46)), False)
    s.zeile("GS RVL 2603", list(range(60, 70)), False)    # 2 Tage nach dem Stichtag (Index 59 = 01.03.)
    s.zeile("Erfunden, Ben", [3, 4], False)               # Person MIT Teilsumme – danach folgt ein Kurs
    s.zeile("GS CNC 2601", [3, 4], False)
    s.zeile("Erfunden, Cem", [], False)
    s.zeile("Zerspanungsmechaniker/-in EG", [0, 1, 2, 40], False)   # alter Langname mit Werten = Kurs
    s.ende()
    a = s.aufenthalte
    assert [(x.person, x.kurs) for x in a] == [(1, "GS ASS PS 260105"), (1, "GS RVL 2603"), (2, "GS CNC 2601"),
                                               (3, "Zerspanungsmechaniker/-in EG")]
    assert s.teilsummen == 1 and s.langnamen == 1
    assert a[0].ein == date(2026, 1, 5) and a[0].kalendertage == 42 and a[0].anwesend == 42
    assert a[3].luecke == 37
    assert s.kuenftig_tage == 10 and s.kuenftig_personen == {1}
    assert bk.Aufenthalt.aus_liste(a[0].als_liste()) == a[0]


def _pivot(mit_we: bool) -> list:
    """Erfundener Pivot wie aus Excel: Kopf, Personen- und Kurszeilen, Tagesspalten als Text."""
    von = date(2025, 1, 1)
    tage = [von + timedelta(days=i) for i in range(800)]
    kopf = ("Zeilenbeschriftungen", *[d.strftime("%d.%m.%Y") for d in tage], "Gesamtergebnis")
    zeilen = [("Summe von Anwesend",), kopf]

    def kurs(name, a, b):
        return (name, *[1 if a <= i <= b and (mit_we or tage[i].weekday() < 5) else None for i in range(len(tage))], 1)
    for p in range(6):
        zeilen.append((f"Erfunden, Person{p}",) + (None,) * (len(tage) + 1))
        zeilen.append(kurs("GS CNC 2501", 0, 729 if p < 4 else 200))   # 4 regulär, 2 vorzeitig
    zeilen.append(("Erfunden, Person9",) + (None,) * (len(tage) + 1))
    zeilen.append(kurs("GS UNBEKANNT 2502", 31, 90))
    zeilen.append(("Gesamtergebnis",))
    return zeilen


def test_pivot_bildet_aufenthalte_ohne_namen():
    erg = mk.pivot_aus_zeilen(iter(_pivot(True)), stichtag=date(2027, 1, 31))
    b = erg.bestand
    assert len(b["aufenthalte"]) == 7
    assert "Erfunden" not in json.dumps(b)                            # keine Namen gespeichert
    assert b["meta"]["kuenftig_spalten"] == 39 and b["meta"]["kuenftig_tage"] == 0
    assert erg.kurse                                                  # bisherige Zählwerte bleiben unverändert erhalten


def test_bericht_wochenenden_und_zuordnung():
    t = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
    for mit_we, erwart in ((True, "mitgezählt"), (False, "nicht gezählt")):
        erg = mk.pivot_aus_zeilen(iter(_pivot(mit_we)), stichtag=date(2027, 1, 31))
        auf = [bk.Aufenthalt.aus_liste(x) for x in erg.bestand["aufenthalte"]]
        r = bk.bericht(auf, erg.bestand["meta"], t, date(2027, 1, 31))
        assert erwart in r.wochenende_text
        assert r.personen == 7 and r.kurse == 2 and r.aufenthalte == 7
        assert [k for k, *_ in r.nicht_zugeordnet] == ["GS UNBEKANNT 2502"]
        cnc = next(z for z in r.arten if z.art == "Hauptmaßnahme CNC")
        assert cnc.n == 6 and cnc.laufend == 0 and cnc.p10 is not None
        assert r.anwesend_basis == 4                                  # 4 regulär beendete (±30 Tage um Soll-Ende)
        assert any("RVT" == m for m, *_ in r.offene_regeln)


def test_bericht_auffaellig():
    t = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
    a = [bk.Aufenthalt(1, "GS ASS 250101", date(2025, 1, 1), date(2025, 6, 1), 100, 0, 0),
         bk.Aufenthalt(2, "GS CNC 2501", date(2025, 1, 1), date(2027, 9, 1), 900, 0, 45)]
    r = bk.bericht(a, {"bis": "2027-12-31"}, t, date(2027, 12, 31))
    n = {text.split(" (")[0]: anz for text, anz, _b in r.auffaellig}
    assert n["Hauptmaßnahme länger als 30 Monate"] == 1 and n["Assessment länger als 3 Monate"] == 1
    assert n["Unterbrechung länger als 30 Tage"] == 1
