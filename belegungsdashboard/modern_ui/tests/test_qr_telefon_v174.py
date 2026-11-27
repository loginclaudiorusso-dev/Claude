"""1.74: Pforten-Nummer (immer erreichbar) auf QR-Etiketten und Aushängen."""

import pytest

from modern import hausordnung_kern as hk
from modern import qr_meldungen_kern as qm


@pytest.fixture
def leer(monkeypatch):
    daten = {}
    monkeypatch.setattr(qm, "_lesen", lambda: dict(daten))
    monkeypatch.setattr(qm, "_schreiben", lambda d: (daten.clear(), daten.update(d)))
    monkeypatch.setattr("modern.kern._schritt", lambda titel, fn, dateien: fn())
    return daten


def test_setzen_und_text(leer):
    assert qm.telefon() == "" and qm.telefon_text() == ""
    qm.telefon_setzen(" 01234/567-0 ")
    assert qm.telefon() == "01234/567-0"
    assert qm.telefon_text() == "Dringend? Pforte – immer erreichbar: 01234/567-0"
    with pytest.raises(ValueError):
        qm.telefon_setzen("Ruf an!")
    qm.telefon_setzen("")
    assert qm.telefon() == ""


def test_etiketten_und_aushaenge(leer):
    link = "https://forms.example/x?z=ZIMMER"
    html = qm.etiketten_html(link, [("GS-101", "101")], telefon="01234/567-0")
    assert "immer erreichbar: 01234/567-0" in html
    assert "immer erreichbar" not in qm.etiketten_html(link, [("GS-101", "101")])
    qm.telefon_setzen("01234/567-0")
    assert "01234/567-0" in qm.etiketten_html(link, [("GS-101", "101")])
    links = {"hausordnung": "https://example.org/ho", "internatsordnung": ""}
    assert "01234/567-0" in hk.aushang_html(links)
    assert "01234/567-0" in hk.zimmer_aushang_html(link, [("GS-101", "101")], links)
