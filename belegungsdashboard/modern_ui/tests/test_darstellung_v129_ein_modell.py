"""1.29 – Ein Einstellungsmodell für die Darstellung (vorher themes.py + darstellung_kern.py getrennt)."""

from modern import darstellung_kern as dk
from modern import darstellung_modell as dm
from modern import themes


def test_eine_quelle_fuer_standard_und_pruefung():
    assert themes.STANDARD is dm.STANDARD and themes.bereinigen is dm.bereinigen
    assert dk.STANDARD is dm.FARB_STANDARD and dk.bereinigen is dm.farben_bereinigen
    assert set(dm.STANDARD) == set(dm.AUFBAU_FELDER) | set(dm.FARB_FELDER)
    assert not set(dm.AUFBAU_FELDER) & set(dm.FARB_FELDER)              # kein Feld doppelt
    assert dk.FARBSCHEMATA is dm.FARBSCHEMATA and themes.LAYOUTS is dm.LAYOUTS


def test_modi_passen_zu_den_paletten():
    for t in dm.THEMES:
        assert dm.modi(t) == themes.modi(t), t
    assert set(themes.P) == {(t, m) for t, ms in dm.MODI.items() for m in ms}
    for t, (_n, _b, erster) in dm.THEMES.items():
        assert erster in dm.MODI[t]


def test_pruefung_ist_stabil_und_startzustand_dokumentiert():
    start = dm.bereinigen({})
    assert dm.bereinigen(start) == start == dm.START                     # zweimal prüfen ändert nichts mehr
    # Startzustand (unverändert seit 1.0): Original-Layout, nur dunkel – die Helligkeit folgt dem Theme
    assert (start["layout"], start["theme"], start["modus"], start["helligkeit"], start["nav"]) == \
        ("original", "original", "dunkel", "dunkel", "band")


def test_beschaedigte_versionsangabe_stuerzt_nicht_ab():
    for v in (None, "x", [], 1.5):
        assert dm.bereinigen({"dg_typ": "linie", "dg_typ_v": v})["dg_typ"] in ("auto", "linie")
    assert dm.bereinigen({"dg_typ": "linie", "dg_typ_v": None})["dg_typ"] == "auto"      # wie fehlende Angabe
    assert dm.bereinigen({"dg_typ": "linie", "dg_typ_v": 2})["dg_typ"] == "linie"
