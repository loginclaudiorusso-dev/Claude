"""Symbole (1.00): Microsoft Fluent 2 – „Fluent UI System Icons“ (MIT, siehe ``symbole/LIZENZ.txt``), offline als SVG.

Ein Symbol ist zweifarbig wie in Microsoft 365 (Duotone):
* unten dieselbe Form **gefüllt** in einer Bedeutungsfarbe, zart (Deckung per CSS ``--sym-deckung``),
* darüber die feine **Kontur** in Schiefergrau (``--sym-basis``; im Dunkeln hell).
Kompakte Knöpfe (18 px) zeigen nur die Kontur – in der Bedeutungsfarbe, wie die 16-px-Symbole in Office.

Rein bis auf das Lesen der Dateien: liefert HTML-Text, die Oberfläche setzt ihn mit ``ui.html`` ein.
"""

from __future__ import annotations

import html as _html
from functools import lru_cache
from pathlib import Path

ORDNER = Path(__file__).resolve().parent / "symbole"

BASIS = ""                      # keine Bedeutungsfarbe → nur Schiefergrau
BLAU, TEAL, GRUEN, AMBER, VIOLETT, ROT = "#0284c7", "#0f766e", "#10b981", "#f59e0b", "#8b5cf6", "#e11d48"
FARBEN = {"blau": BLAU, "teal": TEAL, "gruen": GRUEN, "amber": AMBER, "violett": VIOLETT, "rot": ROT}


@lru_cache(maxsize=None)
def svg(name: str, stufe: str = "g", art: str = "r") -> str:
    """SVG-Text: ``stufe`` g (groß, 24–32er Zeichnung) | k (kompakt, 20er), ``art`` r (Kontur) | f (gefüllt)."""
    p = ORDNER / f"{name}.{stufe}.{art}.svg"
    if not p.exists() and stufe == "k":
        p = ORDNER / f"{name}.g.{art}.svg"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def vorhanden(name: str) -> bool:
    return bool(svg(name, "g", "r"))


def alle() -> list[str]:
    return sorted({p.name.split(".")[0] for p in ORDNER.glob("*.svg")})


def html(name: str, farbe: str = BASIS, gross: bool = True, klasse: str = "") -> str:
    """Duotone-Symbol als HTML. ``farbe``: Bedeutungsfarbe (Hex) oder leer."""
    farbe = FARBEN.get(farbe, farbe)
    if gross:
        flaeche = (f'<span class="m-sym-f" style="color:{_html.escape(farbe)}">{svg(name, "g", "f")}</span>'
                   if farbe else "")
        inhalt = f'{flaeche}<span class="m-sym-k">{svg(name, "g", "r")}</span>'
        return f'<span class="m-sym gross {klasse}" aria-hidden="true">{inhalt}</span>'
    stil = f' style="color:{_html.escape(farbe)}"' if farbe else ""
    return f'<span class="m-sym klein {klasse}" aria-hidden="true"><span class="m-sym-k"{stil}>{svg(name, "k", "r")}</span></span>'


CSS = """
:root { --sym-basis: #334155; --sym-deckung: .45; }
body:not(.hell) { --sym-basis: #CBD5E1; --sym-deckung: .55; }
.m-sym { position: relative; display: inline-block; flex: none; line-height: 0; }
.m-sym.gross { width: 32px; height: 32px; }
.m-sym.klein { width: 18px; height: 18px; }
.m-sym > span { position: absolute; inset: 0; display: block; }
.m-sym svg { width: 100%; height: 100%; display: block; }
.m-sym .m-sym-k { color: var(--sym-basis); }
.m-sym .m-sym-f { opacity: var(--sym-deckung); }
"""
