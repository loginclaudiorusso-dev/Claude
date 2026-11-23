"""0.69: Menüband nach zwei Reviews – Arbeitsbereiche als Registerkarten, sichtbare Ansichten, Statusleiste mit
Ansicht-Schaltern, Datei mit Import und Optionen, Leitung abschaltbar, Null-Werte leise."""

from modern import darstellung_kern as dk
from modern import menueband as mb


def test_arbeitsbereiche_als_reiter():
    rs = {r.key: r for r in mb.reiter({"anreisen": {"zuteilen": "Zuteilen", "abreisen": "Abreisen"}})}
    assert [k for k, r in rs.items() if not r.kontext] == ["uebersicht", "anreisen", "zimmer", "planung", "auswertung",
                                                         "ki", "verwaltung"]            # 1.39: Navigation 2.0
    planung = [q.text for g in rs["planung"].gruppen for p in g.punkte for q in [p] + p.menue]
    assert "Kalender" in planung and "Termine" not in planung             # 1.39: ein Name je Funktion
    anreisen = [p.ziel for g in rs["anreisen"].gruppen for p in g.punkte]
    assert ("seite", "anreisen", "abreisen", {}) in anreisen             # Abreisen sichtbar, nicht im Pfeil
    assert not any(p.menue for g in rs["anreisen"].gruppen for p in g.punkte)


def test_leitung_abschaltbar():
    def haus(leitung):
        r = {r.key: r for r in mb.reiter({}, leitung=leitung)}["planung"]
        return [p.text for g in r.gruppen if g.titel == "Haus" for p in g.punkte]
    assert "Renovierung & Budget" in haus(True) and "Renovierung & Budget" not in haus(False)   # 1.39
    assert dk.bereinigen({"leitung": False})["leitung"] is False and dk.STANDARD["leitung"] is True


def test_datei_wie_backstage():
    assert [p.text for p in mb.DATEI] == ["Drucken … (Strg+P)", "Exportieren …", "Informationen & Sicherung",
                                          "Konto"]   # 1.39: Importieren → Verwaltung › Daten einlesen; Optionen → Konto
    assert ("seite", "daten", None, {}) not in [p.ziel for p in mb.DATEI]


def test_auswertung_umbenannt():
    from modern import seite_auswertung as sa

    assert sa.ANSICHTEN["lage"] == "Kennzahlen" and sa.ANSICHTEN["zimmer"] == "Zimmer-Engpässe"   # 1.39
