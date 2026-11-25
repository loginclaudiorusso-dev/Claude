"""1.23 – Optionen im Menüband nur dort, wo sie wirken; Anteile getrennt wählbar; Datenbeschriftung auch bei
Diagrammen, die selbst „keine“ festlegen; 95-%-Band in jeder Darstellung schaltbar."""

from modern import diagramm_stil as ds
from modern import menueband as mb


def _alle(reiter):
    return {p.text: p for g in reiter.gruppen for p in g.punkte for p in [p] + p.menue}


def test_diagrammentwurf_nur_auf_seiten_mit_diagrammen():
    r = next(r for r in mb.reiter({}) if r.key == "diagramm")
    assert mb.sichtbar(r, "auswertung", "belegung") and mb.sichtbar(r, "steuerung", "finanzen")
    # 1.61: auf der Belegungsprognose stehen die Diagramm-Einstellungen in „Prognose“ (höchstens zwei Kontextkarten)
    assert not mb.sichtbar(r, "auswertung", "prognose")
    for s, a in (("auswertung", "zimmer"), ("steuerung", "vorhaben"), ("steuerung", "grundlagen"), ("heute", None)):
        assert not mb.sichtbar(r, s, a)


def test_optionen_je_seite():
    r = next(r for r in mb.reiter({}) if r.key == "diagramm")
    p = _alle(r)
    assert mb.punkt_sichtbar(p["Anteile"], "auswertung", "massnahmen")
    assert not mb.punkt_sichtbar(p["Anteile"], "auswertung", "prognose")
    assert not mb.punkt_sichtbar(p["Diagrammtyp"], "steuerung", "cockpit")
    prog = next(r for r in mb.reiter({}) if r.key == "prognose")     # 1.39: Band in der Karte „Prognose“
    assert "95-%-Band" in _alle(prog) and mb.sichtbar(prog, "auswertung", "prognose")
    assert not mb.sichtbar(prog, "auswertung", "belegung")
    assert not mb.punkt_sichtbar(p["Datenbeschriftungen"], "auswertung", "massnahmen")
    assert mb.punkt_sichtbar(p["Datenbeschriftungen"], "steuerung", "cockpit")
    assert not any(g.titel == "Darstellung" for g in r.gruppen)      # 1.39: Karte/Klassisch/Einfach → Konto › Optionen


def test_datenbeschriftung_auch_bei_ausdruecklich_keiner():
    o = {"xAxis": {"type": "category", "data": ["a", "b"]}, "yAxis": {"type": "value"},
         "series": [{"name": "Wert", "type": "bar", "data": [1, 2], "label": {"show": False}},
                    {"name": "fest", "type": "bar", "data": [1, 2], "label": {"show": False}, "m_fest": True}]}
    n = ds.anwenden(o, {"dg_werte": True})
    assert n["series"][0]["label"]["show"] is True and n["series"][1]["label"]["show"] is True     # auch feste Säulen


def test_punkte_und_glaetten_nur_wo_linien():
    assert not mb.linien_option_sichtbar("dg_punkte", "auswertung", "belegung", "auto")
    assert mb.linien_option_sichtbar("dg_punkte", "auswertung", "belegung", "linie")
    assert not mb.linien_option_sichtbar("dg_punkte", "steuerung", "cockpit", "linie")
    assert mb.linien_option_sichtbar("dg_punkte", "auswertung", "prognose", "auto")
    assert mb.linien_option_sichtbar("dg_glatt", "auswertung", "massnahmen", "auto")
