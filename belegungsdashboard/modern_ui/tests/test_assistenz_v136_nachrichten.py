"""1.36 – Nachrichten im Programm (ohne Outlook), Mail an FM als Entwurf, „Was ist zu tun?“ je Aufgabe."""

import pytest

from modern import fm_mail_kern as fk
from modern import kern
from modern import nachrichten_kern as nk


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    from modern import benutzer_kern, standort_kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    standort_kern.waehlen("GS", merken_=False)
    benutzer_kern.abmelden()
    yield tmp_path
    benutzer_kern.abmelden()


def _als(name):
    from modern import benutzer_kern as bk

    bk.setzen(bk.Konto(name.lower(), name, "admin"))


def test_schreiben_lesen_antworten_erledigen(ordner):
    _als("Alex")
    nk.schreiben("Schlüssel 2-408", "Bitte Ersatzschlüssel bei FM abholen.")
    n = nk.offene()[0]
    assert n.von == "Alex" and n.betreff == "Schlüssel 2-408" and not n.ungelesen_fuer("Alex")
    assert nk.ungelesen("Bo") == 1
    _als("Bo")
    nk.gelesen(n.id)
    assert nk.ungelesen("Bo") == 0
    nk.antworten(n.id, "Erledigt, liegt im Büro.")
    n = nk.offene()[0]
    assert [a.von for a in n.antworten] == ["Bo"] and n.ungelesen_fuer("Alex")      # Antwort → für Alex wieder neu
    nk.erledigen(n.id)
    assert nk.offene() == [] and len(nk._lesen()) == 1                               # Archiv
    with pytest.raises(ValueError, match="Text"):
        nk.schreiben("", "   ")


def test_fm_adresse_und_vorlage(ordner):
    with pytest.raises(ValueError, match="gültige"):
        fk.adresse_setzen("hausmeister")
    assert "gespeichert" in fk.adresse_setzen("fm@example.org; technik@example.org")
    assert fk.adresse() == "fm@example.org; technik@example.org"
    betreff, text = fk.vorlage("2-408", "Heizung", "Seit gestern kalt.", "Alex")
    assert betreff == "FM-Auftrag: Zimmer 2-408 – Heizung" and "Seit gestern kalt." in text and text.endswith("Alex\n")
    assert fk.mailto("a@b.de", "Hallo Welt", "x y").startswith("mailto:a@b.de?subject=Hallo%20Welt&body=x%20y")
    assert "FM-Adresse" in fk.entwurf("", "b", "t")


def test_jede_aufgabe_hat_eine_anleitung():
    for kid in ("anreise:2026-11-24", "konflikte", "unbewohnbar", "fm", "strittig", "allergie", "qr", "eintragen",
                "reinigung_dringend", "abreisen", "facility", "maengel", "engpass_kw48", "termin:x", "mail:1",
                "mieterende:x", "gebaeudeplan", "umzug:x"):
        assert len(kern.anleitung(kid)) > 30, kid
