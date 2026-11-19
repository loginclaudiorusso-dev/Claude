"""0.69: Menüband nach zwei Reviews – Arbeitsbereiche als Registerkarten, sichtbare Ansichten, Statusleiste mit
Ansicht-Schaltern, Datei mit Import und Optionen, Leitung abschaltbar, Null-Werte leise."""

from modern import darstellung_kern as dk
from modern import menueband as mb


def test_arbeitsbereiche_als_reiter():
    rs = {r.key: r for r in mb.reiter({"anreisen": {"zuteilen": "Zuteilen", "abreisen": "Abreisen"}})}
    assert list(rs) == ["start", "anreisen", "zimmer", "auswertung", "verwalten", "diagramm"]
    start = [p.text for g in rs["start"].gruppen for p in g.punkte]
    assert {"Termine", "Kalender"} <= set(start)                          # „Termine & Post“ ist in Start aufgegangen
    anreisen = [p.ziel for g in rs["anreisen"].gruppen for p in g.punkte]
    assert ("seite", "anreisen", "abreisen", {}) in anreisen             # Abreisen sichtbar, nicht im Pfeil
    assert not any(p.menue for g in rs["anreisen"].gruppen for p in g.punkte)


def test_leitung_abschaltbar():
    mit = {r.key: r for r in mb.reiter({})}["auswertung"]
    ohne = {r.key: r for r in mb.reiter({}, leitung=False)}["auswertung"]
    assert [g.titel for g in mit.gruppen] == ["Berichte", "Leitung"] and [g.titel for g in ohne.gruppen] == ["Berichte"]
    assert dk.bereinigen({"leitung": False})["leitung"] is False and dk.STANDARD["leitung"] is True


def test_datei_wie_backstage():
    assert [p.text for p in mb.DATEI] == ["Drucken … (Strg+P)", "Exportieren …", "Importieren", "Informationen & Sicherung",
                                          "Seitenleiste statt Menüband", "Optionen"]
    assert ("seite", "daten", None, {}) in [p.ziel for p in mb.DATEI]


def test_auswertung_umbenannt():
    from modern import seite_auswertung as sa

    assert sa.ANSICHTEN["lage"] == "Überblick" and sa.ANSICHTEN["zimmer"] == "Engpässe"
