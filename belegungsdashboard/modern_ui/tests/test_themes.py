"""0.8: Designs – „original“ bleibt unberührt, alles Neue ist an body.pro / body.th-… gebunden."""

import re


def _selektoren(css: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    erg, tiefe, puffer = [], 0, ""
    for z in css:
        if z == "{":
            if tiefe == 0 or not puffer.strip().startswith("@"):
                if not puffer.strip().startswith("@"):
                    erg.extend(s.strip() for s in puffer.split(","))
            tiefe += 1
            puffer = ""
        elif z == "}":
            tiefe -= 1
            puffer = ""
        else:
            puffer += z
    return [s for s in erg if s]


def test_original_ohne_klassen_und_alles_gebunden():
    from modern import themes

    assert themes.klassen("original", "oben") == []
    assert "pro" in themes.klassen("linear", "schmal") and "nav-schmal" in themes.klassen("linear", "schmal")
    assert "hell" in themes.klassen("corporate", "seite")
    erlaubt = (".m-topnav", ".m-navklapp")            # nur „ausblenden“ – im Original ohnehin unsichtbar
    for sel in _selektoren(themes.CSS):
        assert ("body.pro" in sel or "body.th-" in sel or "body.hell" in sel or sel in erlaubt), sel
    assert re.search(r"\.m-topnav, \.m-navklapp \{ display: none; \}", themes.CSS)


def test_fuenf_designs_und_diagrammfarben():
    from modern import themes
    from modern.stil import T

    assert list(themes.THEMES) == ["original", "corporate", "linear", "bento", "editorial"]
    assert themes.farben("original") == dict(T)
    for t in ("corporate", "linear", "bento", "editorial"):
        f = themes.farben(t)
        assert {"text", "akzent", "rot", "gruen"} <= set(f) and f != themes.farben("original")


def test_design_wird_gespeichert(tmp_path, monkeypatch):
    from modern import kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    assert kern.design_lesen() == ("original", "seite")
    kern.design_setzen("bento", "oben")
    assert kern.design_lesen() == ("bento", "oben")
    kern.design_setzen("gibt-es-nicht", "quer")
    assert kern.design_lesen() == ("original", "seite")      # Unbekanntes → sicher zurück aufs Original
