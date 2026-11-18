"""1.26 – Lesen, Prüfen und Speichern unter EINER Schreibsperre (Mehrplatz). Erfundene Daten."""

import ast
import contextlib
import pathlib
from datetime import date
from types import SimpleNamespace as NS

MODERN = pathlib.Path(__file__).resolve().parents[1] / "modern"


def _ungeschuetzt() -> list[str]:
    """Funktionen, die den Stand (zp.laden) direkt laden UND über _schritt speichern, ohne @unter_sperre."""
    erg = []
    for p in sorted(MODERN.glob("*.py")):
        for fn in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if {getattr(d, "id", getattr(d, "attr", "")) for d in fn.decorator_list} & {"unter_sperre", "_unter_sperre"}:
                continue

            def direkt(k):
                for x in ast.iter_child_nodes(k):
                    if not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        yield x
                        yield from direkt(x)
            namen = []
            for x in direkt(fn):
                if isinstance(x, ast.Call):
                    f = x.func
                    namen.append(f"{f.value.id}.{f.attr}" if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                                 else getattr(f, "id", ""))
            if any(n in ("zp.laden", "zimmerplan.laden") for n in namen) and any(n.endswith("_schritt") for n in namen):
                erg.append(f"{p.name}:{fn.lineno} {fn.name}")
    return erg


def test_keine_schreibfunktion_laedt_ausserhalb_der_sperre():
    assert _ungeschuetzt() == []


def test_optimierung_uebernimmt_nur_noch_gueltige_vorschlaege(monkeypatch):
    from belegung import optimierung
    from modern import anreisen_kern as ak
    from modern import netz_kern

    def v(p, nach):
        return NS(art="umziehen", personen=[p], von_zimmer=["GS-2-101"], nach_zimmer=[nach])
    gespeichert = {}
    monkeypatch.setattr(netz_kern, "sperre", lambda *a, **k: contextlib.nullcontext())
    monkeypatch.setattr(ak.zp, "laden", lambda: NS())
    monkeypatch.setattr(optimierung, "vorschlaege", lambda stand, heute: [v("a", "GS-2-201")])     # frisch: nur noch a
    monkeypatch.setattr(optimierung, "umsetzen", lambda stand, auswahl, heute: gespeichert.setdefault("x", auswahl) and (1, 0, 0))
    monkeypatch.setattr(ak, "_schritt", lambda titel, fn, dateien=None: fn())
    text = ak.optimieren_umsetzen([v("a", "GS-2-201"), v("b", "GS-2-202")], date(2026, 11, 18))
    assert [x.personen for x in gespeichert["x"]] == [["a"]]
    assert "1 Vorschlag/Vorschläge übersprungen" in text
