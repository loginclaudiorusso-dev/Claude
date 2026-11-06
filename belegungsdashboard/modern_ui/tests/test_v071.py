"""0.71: Befehlssuche in Strg+K – wie „Was möchten Sie tun?“ in Office."""

from modern import befehle_kern as bk
from modern import menueband as mb

ANS = {"anreisen": {"zuteilen": "Zuteilen", "personen": "Personen", "abreisen": "Abreisen", "eintragen": "Firmenprogramm"},
       "zimmer": {"uebersicht": "Übersicht", "zeitstrahl": "Zeitstrahl", "liste": "Liste", "karten": "Karten",
                  "maengel": "Defekte Zimmer", "aenderungen": "Änderungen"},
       "reinigung": {"liste": "Reinigungsliste", "last": "Vorschau 6 Wochen", "facility": "Facility-Checks"},
       "termine": {"liste": "Liste", "monat": "Monat"},
       "einstellungen": {"stammdaten": "Zimmer-Stammdaten", "sicherung": "Sicherung & Verlauf"}}
KAT = bk.katalog(ANS)


def _erstes(q):
    return bk.suchen(q, KAT)[0]


def test_katalog_aus_dem_menueband():
    ziele = {b.ziel[:3] if b.ziel[0] == "seite" else b.ziel for b in KAT}
    for r in mb.reiter(ANS):
        for g in r.gruppen:
            for p in g.punkte:
                for q in [p] + p.menue:
                    if q.ziel and q.ziel[0] == "seite" and q.ziel[1] != "heute":
                        assert q.ziel[:3] in ziele, q.text
    for p in mb.DATEI + mb.TITELLEISTE + mb.STATUSLEISTE:
        if p.ziel[0] == "aktion":
            assert p.ziel in ziele, p.text
    assert len({(b.titel, b.bereich) for b in KAT}) == len(KAT)           # nichts doppelt


def test_synonyme_und_rangfolge():
    assert _erstes("drucken").ziel == ("aktion", "drucken") and _erstes("pdf").ziel == ("aktion", "drucken")
    assert _erstes("abtippen").ziel[:3] == ("seite", "anreisen", "eintragen")
    assert _erstes("kaputt").ziel[:3] == ("seite", "zimmer", "maengel")
    assert _erstes("Mängel").ziel[:3] == ("seite", "zimmer", "maengel")    # Umlaute egal
    assert _erstes("neuer termin").ziel == ("panel", "termine", "liste", "termin_neu")
    assert _erstes("mietvertrag").ziel[0] == "panel"
    assert _erstes("dunkel").ziel == ("aktion", "modus") and _erstes("backup").ziel[:3] == ("seite", "einstellungen", "sicherung")
    assert bk.suchen("", KAT) == [] and bk.suchen("xyzqq", KAT) == []
    assert [b.titel for b in bk.vorschlaege(KAT)][:1] == ["Zuteilen"] and len(bk.vorschlaege(KAT)) >= 5


def test_zimmer_frage_auftrag():
    assert bk.zimmer_befehl("2-408 Mangel") == ("2-408", "Mangel melden")
    assert bk.zimmer_befehl("Zimmer 3.1-e05 sperren") == ("3.1-E05", "Sperre")
    assert bk.zimmer_befehl("2-408") is None                                 # ohne Stichwort: normale Zimmersuche
    assert bk.ist_frage("Wie viele Zimmer sind im Dezember frei?") and bk.ist_frage("welche Kurse starten im Mai")
    assert not bk.ist_frage("drucken") and not bk.ist_frage("Erfunden, Erika")
