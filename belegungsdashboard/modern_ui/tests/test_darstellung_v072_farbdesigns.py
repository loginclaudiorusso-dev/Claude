"""0.72: komplette Farbdesigns – Ton-Paletten aus einer Farbe, Helligkeit hell/gedämpft/dunkel, Färbung Akzent/ganz."""

import pytest

from modern import darstellung_kern as dk
from modern import themes


@pytest.mark.parametrize("farbe", [c for _n, c, _t in dk.FARBSCHEMATA.values()] + ["#FFB900", "#00CC6A", "#E3008C"])
@pytest.mark.parametrize("stufe", list(dk.HELLIGKEIT))
@pytest.mark.parametrize("staerke", [1.0, .25])
def test_lesbar_in_jeder_kombination(farbe, stufe, staerke):
    p = dk.ton_palette(farbe, stufe, staerke)
    assert dk.kontrast(p["text"], p["bg"]) >= (12 if stufe == "hell" else 7)
    assert dk.kontrast(p["text2"], p["bg"]) >= 6.5 and dk.kontrast(p["text3"], p["bg"]) >= 4.5
    assert dk.kontrast(p["akzent"], p["fl"]) >= 4.5
    assert dk.kontrast(p["akzent_text"], p["akzent"]) >= 4.5
    assert p["dunkel"] is (stufe != "hell")


def test_ganzes_design_toent_die_flaechen():
    hell = dk.ton_palette("#B4654A", "hell")
    neutral = dk.ton_palette("#B4654A", "hell", 0)
    assert hell["bg"] != neutral["bg"] and neutral["bg"] == "#FFFFFF"
    g = dk.ton_palette("#007F7F", "gedaempft")
    assert dk.leuchtdichte(g["bg"]) > dk.leuchtdichte(dk.ton_palette("#007F7F", "dunkel")["bg"])   # gedämpft heller als dunkel


def test_variablen_je_einstellung():
    std = dict(dk.STANDARD)
    assert dk.css_variablen(std, dunkel=False) == {}                                    # Standard: unverändert
    ganz = dk.css_variablen({**std, "faerbung": "ganz", "farbe": "rot"}, dunkel=False)
    assert {"--bg", "--fl", "--text", "--ob-band", "--ob-fl", "--s-ok-fg", "--ob-titel"} <= set(ganz)
    ged = dk.css_variablen({**std, "helligkeit": "gedaempft"}, dunkel=True)          # gedämpft auch mit „Nur Akzent“
    assert "--bg" in ged and dk.leuchtdichte(ged["--bg"]) < .1
    hell_titel = dk.css_variablen({**std, "faerbung": "ganz", "titelleiste": "hell"}, dunkel=False)
    assert hell_titel["--ob-titel"] == "#FFFFFF"


def test_helligkeit_und_modus_stimmig():
    alt = themes.bereinigen({"layout": "office", "theme": "innternat", "modus": "dunkel"})   # ältere Einstellung
    assert alt["helligkeit"] == "dunkel" and alt["modus"] == "dunkel"
    g = themes.bereinigen({"layout": "office", "theme": "innternat", "modus": "dunkel", "helligkeit": "gedaempft"})
    assert g["helligkeit"] == "gedaempft" and "mod-dunkel" in themes.klassen(g) and "--bg" in themes.stil(g)
    zurueck = themes.bereinigen({**g, "modus": "hell"})                                  # alter Schalter auf hell
    assert zurueck["helligkeit"] == "hell"
    assert [dk.naechste_helligkeit(h) for h in ("hell", "gedaempft", "dunkel")] == ["gedaempft", "dunkel", "hell"]
    assert dk.bereinigen({"faerbung": "bunt", "helligkeit": "grau"}) | {} and dk.bereinigen({})["faerbung"] == "akzent"
