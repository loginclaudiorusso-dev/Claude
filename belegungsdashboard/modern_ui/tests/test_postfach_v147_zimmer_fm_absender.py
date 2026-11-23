"""1.47 – Postfach im Cockpit: nur Mails mit Zimmerbezug; FM-Mail aus dem gemeinsamen Postfach. Erfundene Texte."""

from types import SimpleNamespace

import pytest

from modern import fm_mail_kern as fk
from modern import outlook_kern as ok


@pytest.mark.parametrize("betreff,text,erwartet", [
    ("Heizung in 2-101 rauscht", "", "Zimmer 2-101"),
    ("Frage", "Im Zimmer 3.204 tropft der Wasserhahn", "Zimmer 3.204"),
    ("Schlüssel für Herrn Musterhoff", "", "Schlüssel"),
    ("Hospitantin kommt morgen", "", "Anreise"),
    ("Vorzeitige Abreise Kim", "", "Abreise"),
    ("Bitte Bettwäsche wechseln", "", "Reinigung"),
    ("WC verstopft", "", "Defekt"),
    ("Allergiker-Zimmer gewünscht", "", "Belegung"),
    ("Mietvertrag Verlängerung", "", "Belegung"),
])
def test_zimmerbezug_erkennt(betreff, text, erwartet):
    assert ok.zimmerbezug(betreff, text) == erwartet


@pytest.mark.parametrize("betreff,text", [
    ("Teamsitzung Donnerstag", "Tagesordnung: Haushalt, Urlaubsplanung"),
    ("Newsletter November", "Neuigkeiten aus der Verwaltung"),
    ("Rechnung 2026-1123", "Betrag siehe Anhang"),
])
def test_zimmerbezug_laesst_anderes_weg(betreff, text):
    assert ok.zimmerbezug(betreff, text) == ""


class _Item:
    def __init__(self, betreff, text):
        self.Class, self.Subject, self.Body, self.SenderName, self.UnRead, self.EntryID = 43, betreff, text, "Alex", True, "e"
        self.ReceivedTime = SimpleNamespace(year=2026, month=11, day=23, hour=9, minute=5)


class _Items(list):
    def Sort(self, *a):
        pass

    def GetFirst(self):
        self._i = 0
        return self[0] if self else None

    def GetNext(self):
        self._i += 1
        return self[self._i] if self._i < len(self) else None


def test_lesen_filtert(monkeypatch):
    items = _Items([_Item("Teamsitzung", "Haushalt"), _Item("Frage", "Schlüssel liegt an der Pforte"),
                    _Item("Zimmer 1-105 Fenster", "")])
    ordner = SimpleNamespace(Items=items, StoreID="s")
    ol = SimpleNamespace(GetNamespace=lambda _n: "ns")
    monkeypatch.setattr(ok, "_outlook", lambda *a: (SimpleNamespace(CoUninitialize=lambda: None), ol))
    monkeypatch.setattr(ok, "_ordner_finden", lambda ns, p: ordner)
    alle = ok.lesen("Internatsdienst", 10)
    assert len(alle) == 3
    nur = ok.lesen("Internatsdienst", 10, filtern=True)
    assert [m.bezug for m in nur] == ["Schlüssel", "Zimmer 1-105"]


def test_fm_absender(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung import aenderungen

    aenderungen.verlauf_leeren()
    with pytest.raises(ValueError):
        fk.absender_setzen("Internatsdienst")              # braucht die Adresse
    assert "internatsdienst@example.org" in fk.absender_setzen("internatsdienst@example.org")
    assert fk.absender() == "internatsdienst@example.org"
    m = SimpleNamespace()
    gesendet = SimpleNamespace(Name="Gesendete Elemente")
    ns = SimpleNamespace(CreateRecipient=lambda a: SimpleNamespace(Resolve=lambda: None, Resolved=True),
                         GetSharedDefaultFolder=lambda r, n: gesendet if n == 5 else None)
    fk._als_postfach(SimpleNamespace(GetNamespace=lambda _n: ns), m, "internatsdienst@example.org")
    assert m.SentOnBehalfOfName == "internatsdienst@example.org" and m.SaveSentMessageFolder is gesendet
    leer = SimpleNamespace()
    fk._als_postfach(None, leer, "")
    assert not hasattr(leer, "SentOnBehalfOfName")
    assert fk.absender_setzen("") == "FM-Mails gehen aus dem eigenen Konto"
    aenderungen.verlauf_leeren()
