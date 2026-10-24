"""6.28: Benachrichtigungen ohne Klick – wechselnde Leiste und Popup für neue dringende Meldungen."""

from datetime import date, datetime, timedelta

import pytest


@pytest.fixture
def daten(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    return tmp_path


def _v(id_, stufe, titel="T"):
    from belegung.vorgaenge import Vorgang

    return Vorgang(id_, stufe, titel, "Detail", "Aktion", id_)


def test_meldungen_aus_vorgaengen_und_neuigkeiten(daten):
    from belegung import newsflash as nf
    from belegung.neuigkeiten import Neuigkeit

    jetzt = datetime(2026, 10, 24, 12, 0)
    vorgaenge = [_v("info1", "info"), _v("bald1", "bald"), _v("dringend1", "dringend", "Reinigung vor Einzug")]
    neu = [Neuigkeit("n1", jetzt - timedelta(hours=2), "UWT zugeteilt", "ok", "zimmerplan"),
           Neuigkeit("n2", jetzt - timedelta(hours=30), "alt", "ok"),
           Neuigkeit("n3", jetzt - timedelta(hours=1), "Gebäudeplan wartet", "warnung", "zimmerplan")]
    ms = nf.meldungen(vorgaenge, neu, jetzt)
    assert [(m.id, m.stufe) for m in ms] == [("v:dringend1", "dringend"), ("n:n3", "dringend"),
                                             ("v:bald1", "bald"), ("n:n1", "neu")]   # „Zur Info“ und Altes fehlen
    assert ms[0].zeile == "Reinigung vor Einzug – Detail" and ms[0].vorgang is vorgaenge[2]


def test_popup_je_meldung_einmal_am_tag(daten):
    from belegung import newsflash as nf

    ms = nf.meldungen([_v("a", "dringend"), _v("b", "bald"), _v("c", "dringend")], [])
    heute = date(2026, 10, 24)
    assert [m.id for m in nf.neu_fuer_popup(ms, heute)] == ["v:a", "v:c"]
    nf.als_gesehen(nf.neu_fuer_popup(ms, heute), heute)
    assert nf.neu_fuer_popup(ms, heute) == []
    ms2 = nf.meldungen([_v("a", "dringend"), _v("d", "dringend")], [])
    assert [m.id for m in nf.neu_fuer_popup(ms2, heute)] == ["v:d"]            # nur das Neue
    assert [m.id for m in nf.neu_fuer_popup(ms, heute + timedelta(days=1))] == ["v:a", "v:c"]   # neuer Tag
