"""0.24: Tagesbriefing per Outlook-Termin oder E-Mail – ohne Personennamen. Erfundene Daten."""

from datetime import date, datetime, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _anreise(heute):
    from belegung import anreiseliste

    an = heute + timedelta(days=1)
    anreiseliste.speichern([anreiseliste.Person("Erfunden, Erna", "GS RVL", an, True, tn_id="801",
                                                abreise=an + timedelta(days=200), bemerkung="Allergiker"),
                            anreiseliste.Person("Beispiel, Bodo", "GS RVL", an, True, tn_id="802",
                                                abreise=an + timedelta(days=200))], {})


def test_briefing_ohne_namen(leer):
    from belegung import termine as tm
    from belegung import zimmerplan as zp
    from modern import briefing_kern as bk

    heute = date.today()
    _anreise(heute)
    tm.eigenen_speichern(tm.Termin("", heute, "Gespräch mit Geheim, Gerda", erinnern_am=heute))
    b = bk.erstellen(zp.laden(), heute)
    assert "Erinnerungen fällig" in b.text and "Gespräch" not in b.text
    assert "ANREISEN" in b.text and "morgen: 2 Personen" in b.text
    assert "ALLERGIKER: 1" in b.text
    for name in ("Erfunden", "Erna", "Beispiel", "Bodo", "Geheim", "Gerda"):
        assert name not in b.text and name not in b.betreff
    assert b.betreff.startswith("INNternat")


def test_briefing_faellig_einmal_am_tag(leer):
    from modern import briefing_kern as bk

    _anreise(date.today())
    jetzt = datetime.combine(date.today(), datetime.min.time()).replace(hour=8)
    assert not bk.faellig(jetzt)                                              # Standard: aus
    bk.einstellen("termin", "07:30")
    assert not bk.faellig(jetzt.replace(hour=7))                              # Uhrzeit noch nicht erreicht
    assert bk.faellig(jetzt)
    gesendet = []
    from belegung import zimmerplan as zp

    bk.senden(zp.laden(), jetzt, test=True, sender=lambda art, b, j: gesendet.append(art))
    assert gesendet == ["termin"] and bk.faellig(jetzt)                       # Test verbraucht den Tag nicht
    bk.senden(zp.laden(), jetzt, sender=lambda art, b, j: gesendet.append(art))
    assert not bk.faellig(jetzt) and bk.status()["ok"]
    assert bk.faellig(jetzt + timedelta(days=1))                              # morgen wieder


def test_briefing_fehler_kein_wiederholen(leer):
    from belegung import zimmerplan as zp
    from modern import briefing_kern as bk

    bk.einstellen("mail", "06:00")
    jetzt = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)

    def kaputt(art, b, j):
        raise OSError("Outlook nicht da")
    with pytest.raises(OSError):
        bk.senden(zp.laden(), jetzt, sender=kaputt)
    assert not bk.faellig(jetzt) and bk.status()["ok"] is False               # nicht alle 15 Minuten erneut
    with pytest.raises(ValueError):
        bk.einstellen("fax", "07:00")
    assert bk.einstellen("aus", "07:00") == "Tagesbriefing aus" and not bk.faellig(jetzt + timedelta(days=1))
