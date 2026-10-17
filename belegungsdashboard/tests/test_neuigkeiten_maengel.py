"""Neuigkeiten (Glocke/Leiste) und Mängel je Zimmer. Nur erfundene Daten."""

from datetime import date, datetime, timedelta

import pytest


@pytest.fixture
def daten(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    return tmp_path


def test_neuigkeiten_einmalig_gelesen_entfernen(daten):
    from belegung import neuigkeiten as nk

    a = nk.hinzufuegen("Gebäudeplan übernommen", "ok", "daten:Gebäudeplan & ZKL")
    assert nk.hinzufuegen("Erinnerung", "info", "termine", schluessel="t1:2026-10-17") is not None
    assert nk.hinzufuegen("Erinnerung", "info", "termine", schluessel="t1:2026-10-17") is None   # nicht doppelt
    assert nk.ungelesen() == 2 and nk.laden()[0].text == "Erinnerung"                       # neueste zuerst
    nk.gelesen_setzen(a.id)
    assert nk.ungelesen() == 1
    nk.gelesen_setzen()
    assert nk.ungelesen() == 0
    nk.entfernen(a.id)
    assert [n.text for n in nk.laden()] == ["Erinnerung"]
    nk.entfernen()
    assert nk.laden() == []


def test_neuigkeiten_hoechstens_max(daten):
    from belegung import neuigkeiten as nk

    start = datetime(2026, 10, 1, 8)
    for i in range(nk.MAX + 5):
        nk.hinzufuegen(f"Nr. {i}", jetzt=start + timedelta(minutes=i))
    alle = nk.laden()
    assert len(alle) == nk.MAX and alle[0].text == f"Nr. {nk.MAX + 4}"


def test_mangel_melden_und_beheben(daten):
    from belegung import maengel as mg
    from belegung import protokoll

    assert mg.setzen("GS-2-301", "boden_kaputt", True, date(2026, 10, 10))
    assert not mg.setzen("GS-2-301", "boden_kaputt", True, date(2026, 10, 11))    # schon offen: nichts doppelt
    mg.setzen("GS-2-301", "schimmel", True, date(2026, 10, 12))
    assert [m.art for m in mg.offen("GS-2-301")] == ["boden_kaputt", "schimmel"]
    assert mg.setzen("GS-2-301", "boden_kaputt", False, date(2026, 10, 15))
    assert [m.art for m in mg.offen()] == ["schimmel"]
    alt = next(m for m in mg.laden() if m.art == "boden_kaputt")
    assert alt.behoben == date(2026, 10, 15) and alt.seit == date(2026, 10, 10)        # Verlauf bleibt
    assert protokoll.laden(1)[0]["aktion"] == "Mangel behoben"
    text = mg.fm_text(mg.offen())
    assert "Zimmer 2-301: Schimmel/Feuchtigkeit (seit 12.10.)" in text
    assert "Mängelliste" in mg.fm_html(mg.offen())


def test_maengel_filtern_und_vorgang(daten):
    from belegung import maengel as mg
    from belegung import vorgaenge, zimmerliste as zl
    from belegung import zimmerplan as zp

    mg.setzen("GS-2-301", "boden_dreckig", True)
    mg.setzen("GS-2-302", "heizung", True)
    st = zp.laden()
    alle = {r.zimmer.id for r in zl.filtern(st, zl.Filter(maengel={"*"}))}
    assert alle == {"GS-2-301", "GS-2-302"}
    assert {r.zimmer.id for r in zl.filtern(st, zl.Filter(maengel={"heizung"}))} == {"GS-2-302"}
    assert {r.zimmer.id for r in zl.filtern(st, zl.Filter(haus="2", text="heizung"))} == {"GS-2-302"}
    v = next(x for x in vorgaenge.sammeln(st, date.today(), engpaesse=False) if x.id == "maengel")
    assert v.stufe == "info" and "2 Zimmer" in v.titel


def test_glocke_und_leiste(daten, qapp):
    from belegung import neuigkeiten as nk
    from belegung.ui.basis import Zustand
    from belegung.ui.hauptfenster import HauptFenster

    z = Zustand()
    w = HauptFenster(z)
    z.neuigkeit.emit("UWT automatisch zugeteilt: 3 Personen", "ok", "zimmerplan:Zuteilen", "")
    assert nk.ungelesen() == 1 and w.glocke.text().strip() == "1"
    sichtbar = w.leiste.isVisible()
    w._leiste_umschalten()
    assert w.leiste.isVisibleTo(w) != sichtbar
    nk.gelesen_setzen()
    w.leiste.aktualisieren()
    assert w.glocke.text() == ""
