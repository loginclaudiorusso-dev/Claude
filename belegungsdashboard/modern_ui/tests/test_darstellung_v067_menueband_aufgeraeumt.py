"""0.67: Menüband aufgeräumt – jeder Befehl an einer Stelle, Split-Buttons, Kontext-Registerkarte „Diagramm“."""

from collections import Counter

from modern import menueband as mb

ANS = {"anreisen": {"zuteilen": "Zuteilen", "personen": "Personen", "abreisen": "Abreisen", "eintragen": "Firmenprogramm"},
       "zimmer": {"uebersicht": "Übersicht", "karten": "Karten", "zeitstrahl": "Zeitstrahl", "liste": "Liste",
                  "maengel": "Defekte Zimmer", "aenderungen": "Änderungen"},
       "reinigung": {"liste": "Reinigungsliste", "last": "Vorschau 6 Wochen", "facility": "Facility-Checks"},
       "termine": {"liste": "Liste", "monat": "Monat"},
       "assistenz": {"auftraege": "Aufträge", "mails": "Mails", "fragen": "Fragen & Zahlen"},
       "auswertung": {"lage": "Lage", "belegung": "Belegung", "prognose": "Prognose", "massnahmen": "Maßnahmen",
                      "zimmer": "Zimmer & Engpässe"},
       "steuerung": {"cockpit": "Cockpit", "vorhaben": "Vorhaben", "zeitplan": "Zeitplan", "finanzen": "Finanzen",
                     "grundlagen": "Grundlagen"},
       "inventar": {"gegenstaende": "Gegenstände", "zimmer": "Zimmer", "haeuser": "Häuser"},
       "einstellungen": {"allgemein": "Allgemein", "stammdaten": "Zimmer-Stammdaten", "sicherung": "Sicherung & Verlauf"}}


def _schluessel(z):
    return (z[1], z[2], tuple(sorted(z[3].items())))


def test_jede_ansicht_erreichbar():
    ziele = mb.alle_ziele(ANS)
    erreicht = {(z[1], z[2]) for z in ziele} | {("einstellungen", "allgemein")}   # über Datei → Optionen → Programm
    for seite, views in ANS.items():
        for k in views:
            assert (seite, k) in erreicht or (seite, None) in erreicht and k == next(iter(views)), (seite, k)
    assert {("mieter", None), ("daten", None)} <= erreicht


def test_jeder_befehl_nur_einmal():
    """Je Schaltfläche zählt ein Ziel einmal (der Split-Button nennt seine Standardansicht auch im Pfeil-Menü)."""
    je_knopf = [{_schluessel(q.ziel) for q in [p] + p.menue if q.ziel and q.ziel[0] == "seite"}
                for r in mb.reiter(ANS) for g in r.gruppen for p in g.punkte]
    je_knopf += [{_schluessel(p.ziel)} for p in mb.DATEI if p.ziel and p.ziel[0] == "seite"]
    doppelt = [k for k, n in Counter(z for menge in je_knopf for z in menge).items() if n > 1]
    assert doppelt == []
    aktionen = Counter(q.ziel[1] for r in mb.reiter(ANS) for g in r.gruppen for p in g.punkte
                       for q in [p] + p.menue if q.ziel and q.ziel[0] == "aktion")
    aktionen.update(p.ziel[1] for p in mb.DATEI + mb.TITELLEISTE + mb.STATUSLEISTE if p.ziel and p.ziel[0] == "aktion")
    assert [k for k, n in aktionen.items() if n > 1] == []


def test_aufgeraeumt_hoechstens_acht():
    for r in mb.reiter(ANS):
        n = sum(len(g.punkte) for g in r.gruppen)
        # 0.96: Die Kontext-Registerkarte „Diagrammentwurf“ ist wie in Excel dichter (Filter der Diagramme stehen dort);
        # auf Seiten ohne Prognose zeigt sie nur drei Gruppen.
        assert n <= (18 if r.kontext else 8), (r.titel, n)
        assert len(r.gruppen) <= 5, r.titel


def test_kontext_diagramm():
    d = next(r for r in mb.reiter(ANS) if r.key == "diagramm")
    assert mb.sichtbar(d, "auswertung") and mb.sichtbar(d, "steuerung") and not mb.sichtbar(d, "heute")
    assert all(mb.sichtbar(r, "heute") for r in mb.reiter(ANS) if r.key != "diagramm")
    assert mb.reiter_von("auswertung", ANS, "prognose") == "auswertung"          # Kontext-Karte ist nie Ziel
