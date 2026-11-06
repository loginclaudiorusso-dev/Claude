"""0.73: Datei → Exportieren – Tabellen der Ansicht als Excel/Zwischenablage, fertige Exporte. Erfundene Werte."""

from datetime import date

from modern import export_kern as ek


ROH = [{"titel": "Anreisen · Zuteilen", "kopf": ["", "Name", "Gruppe", "Zimmer", "Hinweis"],
        "zeilen": [["", "Erfunden, Erika\nNEU", "RVL", "3.1-101", ""], ["", "Muster, Max", "RVL", "2-204", "Mängel: Heizung"],
                   ["", "", "", "", ""]]},
       {"titel": "Leer", "kopf": ["A"], "zeilen": []},
       {"titel": "Zahlen", "kopf": [], "zeilen": [["1.234,5", "17", "07.11.2026"]]}]


def test_bereinigen_und_werte():
    t = ek.bereinigen(ROH)
    assert [x["titel"] for x in t] == ["Anreisen · Zuteilen", "Zahlen"]          # leere Tabelle und Leerzeile weg
    assert t[0]["kopf"] == ["Name", "Gruppe", "Zimmer", "Hinweis"]                # leere Ampel-Spalte weg
    assert t[0]["zeilen"][0][0] == "Erfunden, Erika · NEU"
    assert t[1]["kopf"] == ["Spalte 1", "Spalte 2", "Spalte 3"]
    assert ek.wert("1.234,5") == 1234.5 and ek.wert("17") == 17 and ek.wert("07.11.2026") == "07.11.2026"
    assert ek.wert("2-204") == "2-204" and ek.wert("") == ""
    assert ek.tsv(t).splitlines()[0] == "Name\tGruppe\tZimmer\tHinweis"


def test_excel_datei(tmp_path):
    from openpyxl import load_workbook

    t = ek.bereinigen(ROH)
    pfad = tmp_path / ek.dateiname("Anreisen · Zuteilen", date(2026, 11, 7))
    assert pfad.name == "Anreisen_-_Zuteilen_2026-11-07.xlsx"
    assert ek.excel_schreiben(t, "Anreisen · Zuteilen", pfad) == 3
    wb = load_workbook(pfad)
    assert len(wb.sheetnames) == 2
    ws = wb[wb.sheetnames[0]]
    assert ws["A1"].value == "Name" and ws["A1"].font.bold and ws.freeze_panes == "A2" and ws.auto_filter.ref
    assert wb[wb.sheetnames[1]]["A2"].value == 1234.5


def test_fertige_exporte_und_datei_menue():
    from modern import menueband as mb

    assert [t for t, _k in ek.fertige("zimmer", "uebersicht")][0] == "Zimmer mit „frei bis“"
    assert ek.fertige("heute", None) == []
    assert ("aktion", "exportieren") in [p.ziel for p in mb.DATEI]
    assert ek.blattname("a/b:c*?", set()) == "abc"
