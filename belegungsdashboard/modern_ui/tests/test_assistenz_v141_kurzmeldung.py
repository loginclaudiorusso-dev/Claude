"""1.41 – Kurzmeldungen der Pforte verstehen („Schlüssel für Herrn X, reist heute an“), KI-Einschätzung nur wenn
eingeschaltet, „Kennzahlen“ in „Belegung“ aufgegangen. Alle Namen und Mails erfunden."""

from datetime import date
from types import SimpleNamespace

from belegung import mails

from modern import mail_kern as mk

HEUTE = date(2026, 11, 23)                 # ein Montag
MAIL = """Hallo, ein Schlüssel für Herrn Musterhoff bekommen wir noch, der reist ja heute an

Freundliche Grüße

i. A. Erika Beispiel
Internatsdienst / Pforte
"""


def test_anreisetag_aus_kurzmeldung():
    assert mk.anreise_tag("der reist ja heute an", HEUTE) == HEUTE
    assert mk.anreise_tag("Frau Probe kommt morgen gegen 10 Uhr", HEUTE) == date(2026, 11, 24)
    assert mk.anreise_tag("Anreise am Mittwoch", HEUTE) == date(2026, 11, 25)
    assert mk.anreise_tag("Er reist am 27.11. an", HEUTE) == date(2026, 11, 27)
    assert mk.anreise_tag("Heute ist schönes Wetter.", HEUTE) is None          # ohne Anreise kein Tag


def test_schluessel_heute_wird_gast_mit_zimmer():
    e = mk.erkennen("", MAIL, HEUTE)
    assert e.art == "gast" and e.name == "Musterhoff" and e.von == HEUTE and e.bis == date(2026, 11, 24)
    assert e.zusammenfassung == "Anreise heute (Montag, 23.11.2026) – braucht Zimmer und Schlüssel"
    assert any("eine Nacht angenommen" in u for u in e.unsicher)
    assert e.anliegen.schluessel


def test_rolle_wird_genannt_und_abreise_uebernommen():
    e = mk.erkennen("Hospitant", "Herr Probe (Hospitant) reist morgen an und braucht einen Schlüssel.\n", HEUTE)
    assert e.art == "gast" and e.anliegen.rolle == "Hospitant" and "Hospitant" in e.zusammenfassung
    al = mk.anliegen("", "Der Gast reist heute an.", HEUTE)
    assert al is None                                              # weder Schlüssel noch Zimmer erbeten


def test_normale_mails_bleiben_wie_sie_sind():
    e = mk.erkennen("Storno", "Frau Beispiel sagt ab, Anreise heute entfällt.", HEUTE)
    assert e.art == "storno"
    e = mk.erkennen("", "Bitte an Herrn Probe denken: Schlüssel liegt bei der Pforte.", HEUTE)
    assert e.art != "gast"                                         # ohne Anreisetag kein Zimmer


def test_vorschlag_mit_schluessel_schritt(monkeypatch):
    e = mk.erkennen("", MAIL, HEUTE)
    monkeypatch.setattr(mails, "vorschlag", lambda *a, **k: [mails.Schritt("zimmer", "Zimmer reservieren: 1-101 (Gästezimmer)",
                                                                         daten={"zimmer": "GS-1-101"})])
    s = mk.vorschlag(e, None, None, HEUTE)
    assert s[-1].art == "aufgabe" and s[-1].text == "Schlüssel bereitlegen für Musterhoff – Zimmer 1-101, Anreise Mo 23.11."
    t = SimpleNamespace(name="Musterhoff, Max", zimmer="GS-2-204", schluessel="k1")
    assert "Zimmer 2-204" in mk.vorschlag(e, t, None, HEUTE)[-1].text


def test_ki_nur_wenn_eingeschaltet(monkeypatch):
    from belegung import speicher

    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki": {"backend": "aus"}})
    assert not mk.ki_an() and mk.ki_einschaetzung("", MAIL, HEUTE) == ""
    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki": {"backend": "lokal"}})
    assert mk.ki_an()


def test_kennzahlen_in_belegung():
    from modern import menueband as mb
    from modern import menueband_ui as mbu
    from modern import seite_auswertung as sa

    assert "lage" not in sa.ANSICHTEN
    assert sa._ansicht(SimpleNamespace(ansicht_von=lambda s, d: "lage")) == "belegung"
    aus = {r.key: r for r in mb.reiter(mbu._ansichten())}["auswertung"]
    assert [p.text.replace("­", "") for g in aus.gruppen for p in g.punkte] == [
        "Belegung", "Belegungsprognose", "Maßnahmen", "Zimmer-Engpässe"]   # 1.58; 1.74 ohne „Maßnahme ansehen“
