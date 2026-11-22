"""1.38 – Registerkarte Start aufgeräumt (Heute · Kommunikation · Termine · Assistenz), Mail an FM direkt senden."""

from modern import fm_mail_kern as fk
from modern import menueband as mb


def test_start_gruppen_und_jeder_befehl_einmal():
    start = {r.key: r for r in mb.reiter({})}["start"]
    assert [g.titel for g in start.gruppen] == ["Heute", "Kommunikation", "Termine", "Assistenz"]
    ziele = [repr(q.ziel) for g in start.gruppen for p in g.punkte for q in [p] + p.menue]
    assert len(ziele) == len(set(ziele))
    texte = [p.text for g in start.gruppen for p in g.punkte]
    assert "Mails auswerten" in texte and "Mails" not in texte              # keine Verwechslung mit dem Postfach
    assert sum(1 for g in start.gruppen for _p in g.punkte) <= 8


def test_senden_prueft_vorher_und_startet_outlook_nie():
    assert "FM-Adresse" in fk.senden("", "b", "t")
    assert "Betreff und Text" in fk.senden("fm@example.org", "", "t")
    assert fk.senden("fm@example.org", "b", "t")                           # ohne Outlook: Grund, kein Absturz
