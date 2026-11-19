"""1.26 – Kleinigkeiten aus dem Prüfbericht. Erfundene Daten."""

import os
import pathlib
from datetime import date

MODERN = pathlib.Path(__file__).resolve().parents[1] / "modern"


def test_wochenblatt_kw_mit_iso_jahr():
    s = (MODERN / "seiten.py").read_text(encoding="utf-8")
    assert "isocalendar()[0]" in s and "_{mo:%Y}\"" not in s
    mo = date(2026, 12, 28)                         # Montag der KW 53/2026; 29.12.2025 ist KW 1/2026
    assert date(2025, 12, 29).isocalendar()[:2] == (2026, 1) and mo.isocalendar()[:2] == (2026, 53)


def test_druckdateien_aelter_als_24_stunden_werden_geloescht(tmp_path, monkeypatch):
    import tempfile

    from modern import seiten
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    o = seiten.druck_ordner()
    alt, neu = o / "Alt.html", o / "Neu.html"
    alt.write_text("x"), neu.write_text("y")
    os.utime(alt, (1_000_000, 1_000_000))
    seiten.druck_ordner()
    assert not alt.exists() and neu.exists() and o.name == "INNternat_Druck"


def test_freies_zimmer_mit_zimmersymbol():
    from modern import suche_palette as sp
    assert sp.symbol({"karte": "GS-2-101", "sym": "meeting_room"}) == "meeting_room"
    assert sp.symbol({"karte": "GS-2-101"}) == "person" and sp.symbol({}) == "person"


def test_heute_titel_nennt_die_gezeigten_wochen():
    s = (MODERN / "seite_heute.py").read_text(encoding="utf-8")
    assert 'nächste {len(wochen)} Wochen' in s and 'ui.label("12 Wochen")' not in s


def test_protokoll_rotiert():
    s = (MODERN.parent / "app.py").read_text(encoding="utf-8")
    assert "RotatingFileHandler(PROTOKOLL" in s and "filename=PROTOKOLL" not in s
