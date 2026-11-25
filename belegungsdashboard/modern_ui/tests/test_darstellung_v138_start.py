"""1.38 – Start aufgeräumt (1.39: Übersicht), Mail an FM direkt senden."""

from modern import fm_mail_kern as fk
from modern import menueband as mb


def test_kommunikation_in_der_uebersicht():
    """1.39: Start heißt Übersicht; Termine → Planung › Kalender, Assistenz → KI-Assistent."""
    ueb = {r.key: r for r in mb.reiter({})}["uebersicht"]
    assert [g.titel for g in ueb.gruppen] == ["Cockpit", "Kommunikation", "Im Haus"]       # 1.63: Im Haus
    ziele = [repr(q.ziel) for g in ueb.gruppen for p in g.punkte for q in [p] + p.menue]
    assert len(ziele) == len(set(ziele))
    texte = [p.text for g in ueb.gruppen for p in g.punkte]
    assert texte == ["Cockpit", "Nachrichten", "Neue Nachricht", "Mail an FM", "Aktuell im Haus", "Abwesen\xadheiten",
                     "Schlüssel"]                                                 # 1.63: Gruppe „Im Haus“


def test_senden_prueft_vorher_und_startet_outlook_nie():
    assert "FM-Adresse" in fk.senden("", "b", "t")
    assert "Betreff und Text" in fk.senden("fm@example.org", "", "t")
    assert fk.senden("fm@example.org", "b", "t")                           # ohne Outlook: Grund, kein Absturz
