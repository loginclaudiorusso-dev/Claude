"""0.81 – Reinigungsliste drucken in der Reihenfolge, die auf dem Bildschirm eingestellt ist (z. B. nach Zimmer)."""

from datetime import date
from pathlib import Path

from belegung import reinigungsliste as rl
from belegung import zimmerplan as zp

from modern import seiten
from modern import seiten_kern as sk

MOD = Path(__file__).resolve().parent.parent / "modern"
HEUTE = date(2026, 11, 9)


def _r(nr: str, tag: int, anreise: int | None) -> zp.Reinigung:
    z = zp.Zimmer(id=f"9|{nr}", haus="9", etage="1", nr=nr, betten=2)
    return zp.Reinigung(date(2026, 11, tag), z, naechste_anreise=date(2026, 11, anreise) if anreise else None)


def _liste():
    return rl.sortiert([_r("103", 10, 11), _r("101", 12, 16), _r("102", 9, 13)], HEUTE, {})


def test_reihenfolge_vom_bildschirm():
    rs = _liste()
    nach_zimmer = sorted((rl.schluessel(r) for r in rs), key=lambda k: k.split("|")[1])
    assert [r.zimmer.nr for r in sk.in_reihenfolge(rs, nach_zimmer)] == ["101", "102", "103"]
    # Weggefiltertes folgt in der bisherigen Reihenfolge; ohne Angabe bleibt alles wie es war
    assert [r.zimmer.nr for r in sk.in_reihenfolge(rs, [rl.schluessel(rs[2])])][0] == rs[2].zimmer.nr
    assert sk.in_reihenfolge(rs, []) == rs


def test_druckbild_wie_bisher_und_ohne_neusortieren():
    rs = _liste()
    alt = rl.html_text(rs, HEUTE, HEUTE, False, "Stand x", heute=HEUTE, fertig={})
    assert sk.druck_html(rs, HEUTE, HEUTE, "Stand x", HEUTE, {}) == alt          # gleiche Reihenfolge → gleiches Bild
    umgedreht = sk.druck_html(rs[::-1], HEUTE, HEUTE, "Stand x", HEUTE, {}, "Zimmer")
    zeilen = [z for z in umgedreht.split("<tr") if "<td" in z]
    assert [z.split("<td>")[1].split("<")[0] for z in zeilen] == [r.zimmer.kurz for r in rs[::-1]]
    assert "sortiert nach Zimmer" in umgedreht


def test_oberflaeche_liest_reihenfolge():
    assert "data-rg" in seiten.RG_REIHENFOLGE_JS and "style.order" in seiten.RG_REIHENFOLGE_JS
    q = (MOD / "seiten.py").read_text(encoding="utf-8")
    assert "attr(zeile, data_rg=z.schluessel)" in q and "RG_REIHENFOLGE_JS, timeout=3" in q
