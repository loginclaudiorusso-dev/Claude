"""Zimmer finden: eine Filterlogik für Übersicht, Karten und Liste (Status am Tag, Böden, Renovierung, Gruppen).
Nur erfundene Namen."""

from datetime import date

import pytest


@pytest.fixture
def stand(tmp_path, monkeypatch):
    from belegung import anreiseliste, zimmerliste as zl
    from belegung import zimmerplan as zp

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    anreiseliste.speichern([anreiseliste.Person("Anders, Anna", "GS ASS", date(2026, 10, 19), True, tn_id="1",
                                                abreise=date(2026, 11, 13))], {})
    st = zp.laden()
    eintraege, _f = zl.renovierungen_lesen("2\t301\t\t\t03.06.2024\n2\t302\t\tTeppich\tja\n", {z.id for z in st.zimmer})
    zl.renovierungen_anwenden(st, eintraege, "Vinyl", True)
    st = zp.laden()
    b = st.bedarf[0]
    zp.zuweisungen_speichern([zp.Zuteilung(b, st.lage.zimmer["GS-2-301"])])
    return zp.laden()


def _ids(zeilen):
    return {r.zimmer.id for r in zeilen}


def test_boeden_oder_verknuepft(stand):
    from belegung import zimmerliste as zl

    tag = date(2026, 10, 25)
    assert _ids(zl.filtern(stand, zl.Filter(haus="2", boeden={"Vinyl"}), tag)) == {"GS-2-301"}
    assert _ids(zl.filtern(stand, zl.Filter(haus="2", boeden={"Vinyl", "Teppich"}), tag)) == {"GS-2-301", "GS-2-302"}
    assert "GS-2-301" not in _ids(zl.filtern(stand, zl.Filter(haus="2", boeden={"unbekannt"}), tag))


def test_status_am_tag_und_renoviert(stand):
    from belegung import zimmerliste as zl

    reno = zl.Filter(haus="2", renoviert="ja")
    assert _ids(zl.filtern(stand, reno, date(2026, 10, 25))) == {"GS-2-301", "GS-2-302"}
    belegt = zl.filtern(stand, zl.Filter(haus="2", renoviert="ja", status="geplant"), date(2026, 10, 25))
    assert _ids(belegt) == {"GS-2-301"} and belegt[0].belegungen[0].name == "Anders, Anna"
    frei = zl.filtern(stand, zl.Filter(haus="2", renoviert="ja", status="frei"), date(2026, 10, 25))
    assert _ids(frei) == {"GS-2-302"}
    # an einem Tag nach der Abreise ist 301 wieder frei
    assert "GS-2-301" in _ids(zl.filtern(stand, zl.Filter(haus="2", status="frei"), date(2026, 12, 20)))


def test_gruppen_wohnt_und_darf(stand):
    from belegung import zimmerliste as zl
    from belegung import zimmerplan as zp

    tag = date(2026, 10, 25)
    wohnt = zl.filtern(stand, zl.Filter(gruppen={"Reha"}), tag)
    assert all("Reha" in zp.gruppen_am(stand.lage, r.zimmer.id, tag) for r in wohnt)
    darf = zl.filtern(stand, zl.Filter(gruppen={"EMR"}, gruppen_modus="darf"), tag)
    assert darf and all(zp.erlaubt(r.zimmer, "EMR") for r in darf)


def test_beschreibung_fuer_druck(stand):
    from belegung import zimmerliste as zl

    f = zl.Filter(haus="2", status="frei", boeden={"Vinyl"}, renoviert="ja")
    assert f.aktiv and "frei" in f.beschreibung() and "Vinyl" in f.beschreibung()
    assert not zl.Filter(haus="2").aktiv


def test_reiter_umbenannt():
    from belegung.ui.seiten import zimmerplan as seite

    assert "Häuser" not in seite.TABS and seite.WEGGEFALLEN["Häuser"] == "Zimmer"
    assert "Stammdaten" in seite.TABS


def test_alle_reiter_und_ansichten_oeffnen(stand, qapp):
    """Rauchtest: jeder Zimmerplan-Reiter und jede Finder-Ansicht baut sich ohne Fehler auf."""
    from belegung.ui.basis import Zustand
    from belegung.ui.seiten.zimmerplan import TABS, ZimmerplanSeite

    z = Zustand()
    fehler = []
    z.meldung.connect(lambda t, a: fehler.append(t) if a == "fehler" else None)
    s = ZimmerplanSeite(z, nebenfenster=True)
    s.neu_laden()
    for i, _t in enumerate(TABS):
        s.tabs.setzen(i)
        s._tab_anzeigen(i)
        s._tab_inhalt(i)
    for a in ("uebersicht", "karten", "liste"):
        s.finder._ansicht_setzen(a)
        s.finder.schnell["Vinyl"].setChecked(True)
        s.finder._status_setzen("frei")
        s.finder._zuruecksetzen()
    assert not fehler
    assert not s.scroll.isAncestorOf(s.tabs) and s.isAncestorOf(s.tabs)      # Reiter angeheftet, scrollen nicht mit
