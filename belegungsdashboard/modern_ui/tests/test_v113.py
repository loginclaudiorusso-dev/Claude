"""1.13 – Symbole aus einem Guss: jedes verwendete Fluent-Symbol liegt vollständig vor (groß/klein, Kontur/Fläche),
und Knöpfe mit verschiedener Bedeutung teilen sich im selben Menüband kein Symbol mehr."""

import ast
from pathlib import Path

from modern import menueband as mb
from modern import symbole as sy

MODERN = Path(sy.__file__).resolve().parent


def _vollstaendig(name: str) -> bool:
    return all((sy.ORDNER / f"{name}.{st}.{art}.svg").exists() for st in ("g", "k") for art in ("r", "f"))


def test_alle_zuordnungen_haben_dateien():
    namen = {v[0] for tab in (sy.MATERIAL, sy.ZUSTAND, sy.TON) for v in tab.values()}
    namen |= {z[0] for _w, z in sy.TEXT}
    namen |= {v[0] for tab in (mb.SYMBOLE, mb.AKTION_SYMBOLE, mb.TEXT_SYMBOLE) for v in tab.values()}
    fehlt = sorted(n for n in namen if not _vollstaendig(n))
    assert not fehlt, fehlt


def test_symbole_im_code_gibt_es():
    """Jeder Band-Knopf mit festem Symbolnamen (gross/klein) zeigt ein echtes Fluent-Symbol – nichts erfunden."""
    fehlt = []
    for f in MODERN.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("gross", "klein")
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
                n = node.args[1].value
                if n and not sy.vorhanden(n) and sy.aus_material(n, ("?", ""))[0] == "?":
                    fehlt.append(f"{f.name}: {n}")
    assert not fehlt, fehlt


def test_dopplungen_aufgeloest():
    assert sy.ZUSTAND["ohne"][0] != "bed" and sy.ZUSTAND["mit"][0] != "checkmark_circle"
    assert sy.ZUSTAND["offen"][0] != sy.ZUSTAND["geplant"][0]                      # „offen“ ≠ „geplant“
    assert mb.SYMBOLE[("termine", "liste")][0] != sy.ZUSTAND["geplant"][0]          # Termine ≠ geplant
    assert sy.aus_material("emergency")[0] != sy.ZUSTAND["handeln"][0]              # Notfallliste ≠ Handlungsbedarf
    assert len({sy.aus_material(m)[0] for m in ("tune", "request_quote", "straighten")}) == 3
    assert sy.aus_material("handyman")[0] != sy.ZUSTAND["maengel"][0]               # Mangelart ≠ mit Mangel
    assert sy.aus_text("Letzter Monat")[0] != sy.aus_text("Dieser Monat")[0]
    assert sy.aus_text("Letzte Woche")[0] != sy.aus_text("Diese Woche")[0]
    assert sy.aus_text("Nächste 3 Monate")[0] != sy.aus_text("Dieser Monat")[0]


def test_drei_menuebaender_wie_vorgegeben():
    """Belegungsprognose / Diagrammentwurf / Liste: Tacho, Regler, Klemmbrett, Personengruppe, Export, Präsentation;
    Linie ≠ Trend ≠ Klassisch, Einfach ≠ Dashboard, Elemente ≠ Legende."""
    a = mb.AKTION_SYMBOLE
    assert len({a["dg_typ:linie"][0], a["aw:aw_chart=trend"][0], a["dg_modus:klassisch"][0]}) == 3
    assert a["dg_modus:einfach"][0] != "gauge"
    assert mb.TEXT_SYMBOLE["Elemente"][0] != mb.TEXT_SYMBOLE["Legende"][0]
    assert a["aw:aw_chart=reserve"][0].startswith("battery")
