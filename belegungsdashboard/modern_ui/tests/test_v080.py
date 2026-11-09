"""0.80 – halb belegte Doppelzimmer eindeutig (nicht mehr gestrichelt wie „geplant“), Reinigungsliste „Offen – auch
ältere“ (dieselbe Spanne wie der Besen) und Spalte „Heute“ (belegt oder frei)."""

from datetime import date
from pathlib import Path

from modern import seiten_kern as sk
from modern import themes

MOD = Path(__file__).resolve().parent.parent / "modern"


def test_zeitraum_offen_deckt_besen_ab():
    heute = date(2026, 11, 9)
    von, bis = sk.zeitraum("offen", heute)
    assert (heute - von).days == sk.OFFEN_ZURUECK == 14 and (bis - heute).days == 7
    assert sk.ZEITRAUM["offen"] == "Offen – auch ältere"
    assert "OFFEN_ZURUECK" in (MOD / "zimmer_kern.py").read_text(encoding="utf-8")


def test_rzeile_hat_zustand_heute():
    z = sk.RZeile("k", "101", "Haus 1", "Endreinigung", None, None, None, 1, "", False, heute="belegt")
    assert z.heute == "belegt"
    assert set(sk.ZUSTAND_HEUTE) == {"frei", "teilweise", "belegt", "geplant", "gesperrt"}
    q = (MOD / "seiten.py").read_text(encoding="utf-8")
    assert '"Heute", "Art"' in q and "badge(z.heute" in q


def test_teilweise_nicht_gestrichelt():
    css = themes.CSS if hasattr(themes, "CSS") else (MOD / "themes.py").read_text(encoding="utf-8")
    zeile = next(z for z in (MOD / "themes.py").read_text(encoding="utf-8").splitlines() if ".m-kachel.teilweise" in z)
    block = (MOD / "themes.py").read_text(encoding="utf-8").split(zeile, 1)[1].split("}", 1)[0]
    assert "dashed" not in zeile + block and "linear-gradient" in block and css
    assert "(gestrichelt)" not in (MOD / "seite_zimmer.py").read_text(encoding="utf-8")
