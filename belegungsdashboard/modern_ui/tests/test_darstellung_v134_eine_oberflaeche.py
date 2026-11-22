"""1.34 – nur noch eine Oberfläche (Menüband) mit zwei Symbol-Varianten: klar (zweifarbig) und farbig."""

from modern import darstellung_modell as dm
from modern import symbole as sy
from modern import themes


def test_alle_frueheren_layouts_werden_zum_menueband():
    for alt in ({}, {"layout": "original"}, {"layout": "grid", "theme": "obsidian"}, {"layout": "canvas"},
                {"layout": "showcase", "dock": ["heute"]}, {"layout": "office", "nav": "leiste"}):
        d = dm.bereinigen(alt)
        assert (d["layout"], d["theme"], d["nav"], d["dock"], d["schmal"]) == ("office", "innternat", "band", None, False)
        assert "lay-office" in themes.klassen(d) and "nav-leiste" not in themes.klassen(d)


def test_helligkeit_bleibt_waehlbar_und_wer_dunkel_hatte_bleibt_dunkel():
    assert dm.bereinigen({})["helligkeit"] == "hell"
    assert dm.bereinigen({"layout": "grid", "modus": "dunkel"})["helligkeit"] == "dunkel"
    for h in ("hell", "gedaempft", "dunkel"):
        d = dm.bereinigen({"helligkeit": h})
        assert d["helligkeit"] == h and d["modus"] == ("hell" if h == "hell" else "dunkel")
        assert dm.bereinigen(d) == d


def test_symbol_variante_wird_gemerkt():
    assert dm.STANDARD["symbole"] == "fluent" and set(dm.SYMBOLE) == {"fluent", "farbig"}
    assert dm.bereinigen({"symbole": "farbig"})["symbole"] == "farbig"
    assert dm.bereinigen({"symbole": "3d"})["symbole"] == "fluent"


def test_farbige_symbole_vorhanden_und_ersatz_greift():
    for name, ziel in sy.FARBIG_ERSATZ.items():
        assert (sy.FARBIG_ORDNER / f"{ziel}.g.svg").exists() and (sy.FARBIG_ORDNER / f"{ziel}.k.svg").exists(), name
    mit = [n for n in sy.alle() if sy.farbig(n)]
    assert len(mit) >= 100                                        # die meisten Menüband-Symbole gibt es farbig
    h = sy.html("calendar", sy.BLAU, True, variante="farbig")
    assert "farbig" in h and "linearGradient" in h and "m-sym-f" not in h
    assert "farbig" not in sy.html("calendar", sy.BLAU, True, variante="fluent")
    ohne = next(n for n in sy.alle() if not sy.farbig(n))
    assert "m-sym-k" in sy.html(ohne, sy.BLAU, True, variante="farbig")     # ohne farbiges Motiv: zweifarbig


def test_verlaufs_kennungen_kollidieren_nicht_zwischen_motiven():
    import re

    besitzer: dict[str, str] = {}                      # dieselbe Kennung darf nur bei demselben Motiv vorkommen
    for p in sy.FARBIG_ORDNER.glob("*.svg"):
        motiv = p.name.split(".")[0]
        for i in re.findall(r'id="([^"]+)"', p.read_text(encoding="utf-8")):
            assert besitzer.setdefault(i, motiv) == motiv, i


def test_leitstand_und_layoutwahl_sind_weg():
    from pathlib import Path

    from modern import menueband as mb

    ordner = Path(sy.__file__).parent
    assert not (ordner / "leitstand_ui.py").exists()
    assert all(p.ziel != ("aktion", "nav:leiste") for p in mb.DATEI)
    assert "leitstand_ui" not in (ordner / "oberflaeche.py").read_text(encoding="utf-8")
