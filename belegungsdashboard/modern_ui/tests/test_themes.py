"""0.8: Designs – „original“ bleibt unberührt, alles Neue ist an body.pro / body.th-… gebunden."""

import re
from datetime import date, timedelta


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

    assert themes.klassen({}) == [] and themes.klassen({"layout": "original", "theme": "obsidian"}) == []
    k = themes.klassen({"layout": "canvas", "theme": "nordic"})
    assert {"pro", "lay-canvas", "th-nordic", "mod-hell", "hell", "nav-schmal"} <= set(k)
    erlaubt = (".m-prompt-zeile", ".m-topnav", ".m-navklapp", ".m-cv-start")   # nur „ausblenden“
    for sel in _selektoren(themes.CSS):
        if "m-tb" in sel or sel.startswith("from") or sel == "to":
            continue                                  # eigene Werkzeugleiste (neues Element) bzw. Keyframes
        assert ("body.pro" in sel or "body.lay-" in sel or "body.hell" in sel or "body.th-" in sel
                or "html:has(body." in sel or sel in erlaubt), sel


def test_fuenf_themes_drei_layouts_und_farben():
    from modern import themes
    from modern.stil import T

    assert list(themes.THEMES) == ["innternat", "original", "inn", "linear", "obsidian", "nordic"]
    assert list(themes.LAYOUTS) == ["original", "grid", "canvas", "showcase"]
    assert {k: v for k, v in themes.farben({}).items() if k in T} == dict(T)
    for t in ("innternat", "inn", "linear", "obsidian", "nordic"):
        assert set(themes.modi(t)) == {"hell", "dunkel"}
        assert themes.farben({"layout": "grid", "theme": t}) != themes.farben({})


def test_alter_stand_und_unbekanntes():
    from modern import themes

    d = themes.bereinigen({"theme": "corporate", "nav": "oben"})          # Stand 0.8
    assert (d["layout"], d["theme"], d["modus"]) == ("showcase", "inn", "hell")
    assert themes.bereinigen({"layout": "quer", "theme": "x"})["layout"] == "original"
    assert themes.bereinigen({"layout": "grid", "theme": "linear", "modus": "lila"})["modus"] == "dunkel"


def test_design_wird_gespeichert(tmp_path, monkeypatch):
    from modern import kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    d = kern.design_lesen()                   # 0.38: einmalig die neue INNternat-Darstellung …
    assert (d["layout"], d["theme"], d["modus"]) == ("grid", "innternat", "dunkel")
    kern.design_setzen({"layout": "original"})
    assert kern.design_lesen()["layout"] == "original"      # … „Original-Zustand“ bleibt danach erhalten
    kern.design_setzen({"layout": "showcase", "theme": "obsidian", "dichte": "kompakt", "notiz": "Rückruf"})
    d = kern.design_lesen()
    assert (d["layout"], d["theme"], d["modus"], d["dichte"], d["notiz"]) == ("showcase", "obsidian", "dunkel", "kompakt", "Rückruf")


def test_canvas_versteht_saetze():
    from modern import canvas_kern as ck

    h = date(2026, 10, 15)
    v = ck.verstehen("freie Doppelzimmer Haus 3,1 morgen", h)
    assert (v.status, v.haus, v.merkmale, v.von) == ("frei", "3.1", {"doppel"}, h + timedelta(days=1))
    assert v.zimmerfrage and not v.personenfrage
    v = ck.verstehen("EMR ohne Zimmer nächste Woche", h)
    assert v.gruppen == {"EMR"} and v.ohne and v.von == date(2026, 10, 19) and v.personenfrage
    v = ck.verstehen("Abreisen diese Woche", h)
    assert v.abreisen and v.bis == date(2026, 10, 18)
    assert ck.verstehen("2-301", h).zimmerfrage and ck.verstehen("Müller", h).rest == "müller"


def test_prognose_szenario_kernaussagen_jahresvergleich():
    from modern import auswertung_kern as ak

    zeilen = [ak.PZeile(date(2025, m, 1), "ist", 100.0 + m, 0, 0, 0, 0, None, 100.0 + m) for m in range(1, 13)]
    zeilen += [ak.PZeile(date(2026, m, 1), "prognose", 110.0 + m, 105.0 + m, 115.0 + m, 100.0 + m, 120.0 + m, 90.0, None)
               for m in range(1, 13)]
    pg = ak.Prognose(zeilen, 130, "M", "", 2.0, 4.0, .8, [], [])
    zs = ak.szenario(pg, 130, 0)
    assert zs[0].text.startswith("Reserve") and zs[-1].reserve == 130 - 122
    eng = ak.szenario(pg, 120, 10)                       # +10 % und weniger Plätze → Engpass
    assert all(z.text.startswith("Engpass") for z in eng if z.art != "ist")
    assert eng[0].erwartet == zs[0].erwartet              # Ist bleibt Ist
    k = ak.kernaussagen(pg, 130)
    assert k[0].startswith("Höchststand voraussichtlich Dez 2026") and any("Trefferquote" in x for x in k)
    jv = ak.jahresvergleich(pg)
    assert set(jv) == {2025, 2026} and jv[2025][0][0] == 101.0 and jv[2026][1][0] == 111.0
