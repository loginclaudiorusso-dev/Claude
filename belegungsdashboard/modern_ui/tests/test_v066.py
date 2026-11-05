"""0.66: Darstellungs-Optionen wie in Office – Farben, eigene Akzentfarbe, Zoom, Schrift, Diagrammtyp. Erfundene Werte."""

from modern import darstellung_kern as dk
from modern import diagramm_stil as ds


def test_bereinigen_und_zoom():
    d = dk.bereinigen({"farbe": "lila?", "farbe_eigen": "zzz", "zoom": 900, "schrift": "comic", "dg_typ": "torte",
                       "dg_gitter": False})
    assert d["farbe"] == "petrol" and d["farbe_eigen"] == "#007F7F" and d["zoom"] == dk.ZOOM_MAX
    assert d["schrift"] == "standard" and d["dg_typ"] == "linie" and d["dg_gitter"] is False
    assert dk.bereinigen({"farbe": "eigen", "farbe_eigen": "ffb900"})["farbe_eigen"] == "#FFB900"
    assert dk.zoom_schritt(100, 1) == 110 and dk.zoom_schritt(100, -1) == 90
    assert dk.zoom_schritt(200, 1) == 200 and dk.zoom_schritt(50, -1) == 50
    assert dk.zoom_schritt(105, 1) == 110 and dk.zoom_schritt(105, -1) == 100


def test_eigene_farbe_wird_lesbar():
    gelb = "#FFB900"
    assert dk.kontrast(gelb, "#FFFFFF") < 4.5
    lesbar = dk.lesbar(gelb, "#FFFFFF")
    assert dk.kontrast(lesbar, "#FFFFFF") >= 4.5
    v = dk.css_variablen({"farbe": "eigen", "farbe_eigen": gelb}, dunkel=False)
    assert dk.kontrast(v["--akzent"], "#FFFFFF") >= 4.5
    assert dk.kontrast(v["--ob-titel-text"], v["--ob-titel"]) >= 4.5
    dunkel = dk.css_variablen({"farbe": "eigen", "farbe_eigen": "#2B4C7E"}, dunkel=True)
    assert dk.kontrast(dunkel["--akzent"], "#141B1B") >= 4.5           # dunkles Blau wird im Dunkelmodus aufgehellt


def test_standard_ohne_ueberschreibung():
    assert dk.css_variablen(dict(dk.STANDARD), dunkel=False) == {}
    v = dk.css_variablen({**dk.STANDARD, "schrift": "verdana", "zoom": 125}, dunkel=False)
    assert "Verdana" in v["--schrift"] and v["--m-zoom"] == "1.25" and "--akzent" not in v
    hell = dk.css_variablen({**dk.STANDARD, "titelleiste": "hell"}, dunkel=False)
    assert hell["--ob-titel"] == "#FFFFFF"


def test_themes_stil_und_klassen():
    from modern import themes

    d = themes.bereinigen({"layout": "office", "theme": "innternat", "modus": "hell", "farbe": "violett",
                           "band_gross": True})
    assert "--akzent: #6B3FA0" in themes.stil(d) and "band-gross" in themes.klassen(d)
    assert themes.farben(d)["akzent"] != themes.farben({**d, "farbe": "petrol"})["akzent"]
    original = themes.bereinigen({"layout": "original", "farbe": "rot", "zoom": 90})
    assert themes.stil(original) == "--m-zoom: 0.90;"                    # Original: nur der Zoom


def _opt():
    return {"xAxis": {"type": "category", "boundaryGap": False, "data": ["a", "b", "c"]}, "yAxis": {"type": "value"},
            "legend": {"top": 0}, "grid": {"bottom": 30},
            "series": [
                {"name": "u", "type": "line", "stack": "band", "data": [1, 2, 3], "lineStyle": {"opacity": 0}},
                {"name": "80 %-Spanne", "type": "line", "stack": "band", "data": [1, 1, 1], "areaStyle": {}},
                {"name": "Ist", "type": "line", "data": [5, 6, 7], "lineStyle": {"color": "#111111"}},
                {"name": "Prognose", "type": "line", "data": [7, 8, 9], "lineStyle": {"color": "#222222", "type": "dashed"}},
                {"name": "Erfunden konstant", "type": "line", "data": [8, 8, 8], "lineStyle": {"color": "#333333"}},
                {"name": "Kapazität", "type": "line", "data": [10, 10, 10], "lineStyle": {"type": "dotted"}},
                {"name": "Rückwärtstest", "type": "line", "data": [6, 7, 6], "lineStyle": {"type": "dotted"}}]}


def test_standard_aendert_nichts():
    o = _opt()
    assert ds.anwenden(o, dict(dk.STANDARD)) is o


def test_saeulen_nur_fuer_datenreihen():
    o = _opt()
    n = ds.anwenden(o, {**dk.STANDARD, "dg_typ": "saeule"})
    typ = {s["name"]: s["type"] for s in n["series"]}
    assert typ["Ist"] == "bar" and typ["Prognose"] == "bar" and typ["Erfunden konstant"] == "bar"
    assert typ["u"] == typ["80 %-Spanne"] == typ["Kapazität"] == typ["Rückwärtstest"] == "line"
    prog = next(s for s in n["series"] if s["name"] == "Prognose")
    assert prog["itemStyle"]["color"] == "#222222" and prog["itemStyle"]["opacity"] < 1
    assert n["xAxis"]["boundaryGap"] is True
    assert o["series"][2]["type"] == "line"                              # Original unverändert (Kopie)


def test_flaeche_gitter_legende_animation():
    n = ds.anwenden(_opt(), {**dk.STANDARD, "dg_typ": "flaeche", "dg_gitter": False, "dg_legende": "unten",
                             "dg_anim": False, "dg_glatt": True, "dg_werte": True})
    ist = next(s for s in n["series"] if s["name"] == "Ist")
    assert "areaStyle" in ist and ist["smooth"] and ist["label"]["show"]
    assert "areaStyle" not in next(s for s in n["series"] if s["name"] == "Kapazität")
    assert n["yAxis"]["splitLine"]["show"] is False and n["legend"]["bottom"] == 0 and "top" not in n["legend"]
    assert n["grid"]["bottom"] == 54 and n["animation"] is False
    aus = ds.anwenden(_opt(), {**dk.STANDARD, "dg_legende": "aus"})
    assert aus["legend"]["show"] is False


def test_menueband_ansicht_und_optionen():
    from modern import menueband as mb

    r = next(x for x in mb.reiter({}) if x.key == "ansicht")
    ziele = {q.ziel for g in r.gruppen for p in g.punkte for q in (p.menue or [p]) if q.ziel and q.ziel[0] == "aktion"}
    assert {("aktion", "zoom:+"), ("aktion", "zoom:-"), ("aktion", "zoom:100"), ("aktion", "optionen:farben"),
            ("aktion", "farbe:violett"), ("aktion", "dg_typ:saeule")} <= ziele
    assert ("aktion", "optionen:farben") in [p.ziel for p in mb.DATEI]
    farben = next(p for g in r.gruppen for p in g.punkte if p.text == "Farben")
    assert all(q.farbe for q in farben.menue[:-1])                       # Farbmuster im Menü
