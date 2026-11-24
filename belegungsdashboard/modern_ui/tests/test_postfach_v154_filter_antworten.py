"""1.54 – Postfach: Filter kennt Zimmernummern und Namen des Standorts, Absender-Regeln; Mail im Programm lesen,
beantworten und weiterleiten (Outlook nachgebaut). Erfundene Namen."""

from types import SimpleNamespace

import pytest

from modern import outlook_kern as ok

K = ok.kontext_bauen(["2-101", "6-1005", "3.2-105", "6-301"], ["Musterhoff", "Beispiel", "Kim"])


@pytest.mark.parametrize("betreff,text,erwartet", [
    ("Frage", "Bei 6-1005 klemmt etwas", "Zimmer 6-1005"),
    ("Frage", "Gilt das für 3.2 105?", "Zimmer 3.2 105"),
    ("AW: Termin", "Herr Musterhoff kommt am Montag", "Bewohner: Musterhoff"),
    ("Wochenplan", "Zimmer 1005 bitte prüfen", "Zimmer 1005"),
    ("Abmeldung Teilnehmer", "", "Abreise"),
    ("Matratze austauschen", "", "Defekt"),
])
def test_filter_mit_kontext(betreff, text, erwartet):
    assert ok.zimmerbezug(betreff, text, K) == erwartet


def test_kurze_namen_und_fremde_nummern_nicht():
    assert ok.zimmerbezug("Kim schreibt", "", K) == ""                  # Namen unter 4 Zeichen zählen nicht
    assert ok.zimmerbezug("Rechnung 2026-1123", "Betrag siehe Anhang", K) == ""


def test_absender_regeln(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    assert ok.absender_regeln() == {"immer": [], "nie": []}
    ok.absender_setzen("FM@Example.org", "immer")
    ok.absender_setzen("news@example.org", "nie")
    r = ok.absender_regeln()
    assert ok._regel("fm@example.org", r) == "immer" and ok._regel("news@example.org", r) == "nie"
    ok.absender_setzen("news@example.org", None)
    assert ok._regel("news@example.org", ok.absender_regeln()) is None
    with pytest.raises(ValueError):
        ok.absender_setzen("", "immer")


def test_text_davor():
    html = "<html><body lang=de><p>Alt</p></body></html>"
    neu = ok.text_davor(html, "Hallo,\nerledigt.")
    assert neu.index("Hallo,<br>erledigt.") < neu.index("<p>Alt</p>") and "<body lang=de>" in neu
    assert ok.text_davor(html, "  ") == html
    assert ok.text_davor("", "<b>x</b>").startswith("<div") and "&lt;b&gt;" in ok.text_davor("", "<b>x</b>")


class _Neu(SimpleNamespace):
    def Send(self):
        self.gesendet = True

    def Display(self, _modal=False):
        self.angezeigt = True


def test_antworten_und_weiterleiten(monkeypatch):
    erzeugt = []

    def neu():
        n = _Neu(To="", HTMLBody="<body><p>Zitat</p></body>")
        erzeugt.append(n)
        return n
    mail = SimpleNamespace(Reply=neu, ReplyAll=neu, Forward=neu)
    ns = SimpleNamespace(GetItemFromID=lambda *a: mail)
    ol = SimpleNamespace(GetNamespace=lambda _n: ns)
    monkeypatch.setattr(ok, "_outlook", lambda *a: (SimpleNamespace(CoUninitialize=lambda: None), ol))
    from modern import fm_mail_kern as fk

    monkeypatch.setattr(fk, "_als_postfach", lambda ol_, m, von: setattr(m, "von", von))
    assert ok._antwort("id", "", "antworten", "Danke!", senden=True, von="internat@example.org") == ""
    assert erzeugt[-1].gesendet and "Danke!" in erzeugt[-1].HTMLBody and erzeugt[-1].von == "internat@example.org"
    assert "Adresse" in ok._antwort("id", "", "weiterleiten", "x")
    assert ok._antwort("id", "", "weiterleiten", "Bitte erledigen", an="fm@example.org") == ""
    assert erzeugt[-1].To == "fm@example.org" and erzeugt[-1].angezeigt
