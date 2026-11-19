"""1.00 – Wächter gegen „lokaler Import verdeckt Modulnamen“: In 0.97–0.99 brach das Belegungs-Diagramm ab, weil
eine Funktion ``_ds`` benutzte und weiter unten ``from . import diagramm_stil as _ds`` stand (UnboundLocalError).
pyflakes erkennt das nicht – darum prüft dieser Test alle Module selbst."""

import ast
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent / "modern"


def frueh_benutzt(quelltext: str) -> list[str]:
    baum = ast.parse(quelltext)
    out = []
    for fn in ast.walk(baum):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        lokal: dict[str, int] = {}
        for n in ast.walk(fn):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    name = a.asname or a.name.split(".")[0]
                    lokal[name] = min(lokal.get(name, n.lineno), n.lineno)
        for name, erste in lokal.items():
            if any(isinstance(n, ast.Name) and n.id == name and n.lineno < erste for n in ast.walk(fn)):
                out.append(f"{fn.name}:{name}")
    return out


def test_wachter_erkennt_den_fehler_aus_0_97():
    alt = ("from . import diagramm_stil as _ds\n"
           "def f():\n    farben = _ds.kategorien({})\n    from . import diagramm_stil as _ds\n    return farben\n")
    assert frueh_benutzt(alt) == ["f:_ds"]


def test_kein_modul_benutzt_einen_namen_vor_seinem_lokalen_import():
    fehler = {p.name: f for p in sorted(MOD.glob("*.py")) if (f := frueh_benutzt(p.read_text(encoding="utf-8")))}
    assert fehler == {}


# ---- Fluent-Symbole, Bausteine, Zeitstrahl-Filter ------------------------------------------------------------------
def test_symbole_lizenz_und_beide_ebenen():
    from modern import symbole

    assert (symbole.ORDNER / "LIZENZ.txt").read_text(encoding="utf-8").count("MIT License") == 1
    for n in symbole.alle():
        assert symbole.svg(n, "g", "r").startswith("<svg") and 'fill="currentColor"' in symbole.svg(n, "g", "r")
        assert symbole.svg(n, "k", "r"), n


def test_symbol_html_gross_zweifarbig_klein_einfarbig():
    from modern import symbole

    g = symbole.html("gauge", "blau")
    assert "m-sym gross" in g and "m-sym-f" in g and "#0284c7" in g and g.count("<svg") == 2
    k = symbole.html("gauge", "blau", gross=False)
    assert "m-sym klein" in k and "m-sym-f" not in k and k.count("<svg") == 1
    assert symbole.html("gauge").count("<svg") == 1                    # ohne Farbe: nur Kontur


def test_zeitstrahl_filter():
    from dataclasses import dataclass, field

    from modern import seiten_kern as sk

    @dataclass
    class B:
        art: str

    @dataclass
    class Z:
        zimmer: str
        balken: list = field(default_factory=list)

    zs = [Z("1", [B("belegt")]), Z("2", [B("geplant"), B("konflikt")]), Z("3", []), Z("4", [B("gesperrt")])]
    assert [z.zimmer for z in sk.zeitstrahl_filtern(zs, ())] == ["1", "2", "3", "4"]
    assert [z.zimmer for z in sk.zeitstrahl_filtern(zs, {"konflikt"})] == ["2"]
    assert [z.zimmer for z in sk.zeitstrahl_filtern(zs, {"belegt", "gesperrt"})] == ["1", "4"]
    assert sk.zeitstrahl_zaehlen(zs) == {"belegt": 1, "geplant": 1, "gesperrt": 1, "konflikt": 1}
