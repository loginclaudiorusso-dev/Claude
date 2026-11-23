"""1.43 – Chat im Programm: Kanäle „Alle Standorte“ und je Standort, gelesen je Person, Hinweis bei Neuem.
Nur erfundene Namen; die Chatdatei liegt in einem Testordner."""

import inspect
from datetime import datetime
from types import SimpleNamespace

import pytest

from modern import chat_kern as ck
from modern import menueband as mb


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    import contextlib

    from modern import netz_kern, standort_kern

    monkeypatch.setattr(netz_kern, "basis", lambda: tmp_path)
    monkeypatch.setattr(netz_kern, "sperre", contextlib.nullcontext)
    monkeypatch.setattr(standort_kern, "aktiv", lambda: SimpleNamespace(kurz="GS", name="Erfundenstadt"))
    gemerkt = {}
    monkeypatch.setattr(netz_kern, "persoenlich", lambda name, standard=None, **k: gemerkt.get(name, standard))
    monkeypatch.setattr(netz_kern, "persoenlich_setzen", lambda name, wert, **k: gemerkt.__setitem__(name, wert))
    return tmp_path


def test_senden_lesen_und_kanaele(ordner):
    assert ck.kanaele() == {"alle": "Alle Standorte", "GS": "Erfundenstadt"}
    t = datetime(2026, 11, 23, 9, 0)
    ck.senden("alle", "  Wer hat den Schlüssel?  ", von="Alex", jetzt=t)
    ck.senden("GS", "Nur für hier", von="Kim", jetzt=t.replace(minute=5))
    ck.senden("alle", "An der Pforte", von="Kim", jetzt=t.replace(minute=7))
    alle = ck.beitraege("alle")
    assert [(b.von, b.text) for b in alle] == [("Alex", "Wer hat den Schlüssel?"), ("Kim", "An der Pforte")]
    assert alle[0].uhr == "09:00" and ck.stempel() > 0
    with pytest.raises(ValueError):
        ck.senden("alle", "   ", von="Alex")
    assert len(ck.senden("alle", "x" * 5000, von="Alex", jetzt=t.replace(minute=9)).text) == ck.MAX_TEXT


def test_ungelesen_je_person(ordner):
    t = datetime(2026, 11, 23, 9, 0)
    ck.senden("alle", "Frage", von="Alex", jetzt=t)
    ck.senden("alle", "Antwort", von="Kim", jetzt=t.replace(minute=1))
    ck.senden("GS", "Hier", von="Kim", jetzt=t.replace(minute=2))
    neu = ck.ungelesen("Alex")
    assert {k: [b.text for b in v] for k, v in neu.items()} == {"alle": ["Antwort"], "GS": ["Hier"]}
    ck.gelesen("alle", "2026-11-23T09:01:00")
    assert list(ck.ungelesen("Alex")) == ["GS"]                    # eigene Beiträge zählen nie


def test_alte_beitraege_fallen_weg(ordner):
    ck.senden("alle", "uralt", von="Alex", jetzt=datetime(2026, 8, 1, 9))
    ck.senden("alle", "neu", von="Alex", jetzt=datetime(2026, 11, 23, 9))
    assert [b.text for b in ck.beitraege("alle")] == ["neu"]


def test_tagestrenner():
    bs = [ck.Beitrag("1", "2026-11-22T10:00:00", "A", "alle", "x"), ck.Beitrag("2", "2026-11-23T08:00:00", "B", "alle", "y"),
          ck.Beitrag("3", "2026-11-23T09:00:00", "A", "alle", "z")]
    zeilen = ck.tagestrenner(bs, "2026-11-23")
    assert [t for t, b in zeilen if b is None] == ["So 22.11.", "Heute"] and len(zeilen) == 5


def test_chat_immer_erreichbar_und_gemeldet():
    assert mb.TITELLEISTE[0].ziel == mb.A("chat")
    from modern import chat_ui, menueband_ui, oberflaeche

    assert "chat_ui.einrichten(self)" in inspect.getsource(oberflaeche)
    assert 'elif name == "chat":' in inspect.getsource(menueband_ui.ausfuehren)
    z = inspect.getsource(chat_ui.zaehlen)
    assert "melder.windows_zeigen" in z and "Chat öffnen" in z
    from modern import netz_kern

    assert "chat_gelesen" in netz_kern.JE_PERSON
