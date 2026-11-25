"""1.53 – EMR-Zimmer: eine Sperre mit „EMR“ im Gebäudeplan ist eine Reservierung, keine Sperre – Zustand nach den
Bewohnern, Name aus dem Gebäudeplan-Text; echte Sperren bleiben „nicht nutzbar“ (rote Schrift). Erfundene Namen."""

from datetime import date
from types import SimpleNamespace

from belegung import zimmerplan as zp
from modern import zimmer_kern as zk

TAG = date(2026, 11, 24)


def _lage(bs, betten=1):
    z = SimpleNamespace(id="GS-2-105", betten=betten)
    belegungen = {z.id: bs}

    def status_am(zid, tag):
        heute = [b for b in belegungen[zid] if b.von <= tag <= b.bis]
        if any(b.art == "gesperrt" for b in heute):
            return "gesperrt", heute
        p = [b for b in heute if b.art in ("belegt", "geplant")]
        return ("frei" if not p else "teilweise" if len(p) < betten else "belegt"), heute
    return SimpleNamespace(zimmer={z.id: z}, status_am=status_am)


def _sperre(grund):
    return zp.Belegung("GS-2-105", date(2026, 11, 23), date(2026, 11, 26), "gesperrt", "", "", grund)


def test_emr_reservierung_mit_name_ist_belegt():
    st, bs, emr = zk.status_anzeige(_lage([_sperre("Reserviert: Beispiel, Erika (GS EMR 2611)")]), "GS-2-105", TAG)
    assert (st, emr) == ("belegt", True) and [b.name for b in bs] == ["Beispiel, Erika"]


def test_emr_reservierung_ohne_name_ist_frei():
    st, bs, emr = zk.status_anzeige(_lage([_sperre("Gesperrt: EMR")]), "GS-2-105", TAG)
    assert (st, emr) == ("frei", True)


def test_emr_mit_eigener_planung():
    geplant = zp.Belegung("GS-2-105", date(2026, 11, 23), date(2026, 11, 26), "geplant", "Musterhoff, Alex", "GS EMR",
                          person="name:x")
    st, bs, emr = zk.status_anzeige(_lage([_sperre("EMR-Zimmer"), geplant]), "GS-2-105", TAG)
    assert st == "geplant" and emr and [b.name for b in bs] == ["Musterhoff, Alex"]


def test_echte_sperre_bleibt():
    st, _bs, emr = zk.status_anzeige(_lage([_sperre("Reno offen: Malerarbeiten")]), "GS-2-105", TAG)
    assert (st, emr) == ("gesperrt", False)
    st, _bs, emr = zk.status_anzeige(_lage([_sperre("Gesperrt: EMR"), _sperre("Reno offen: Boden")]), "GS-2-105", TAG)
    assert st == "gesperrt"                               # Renovierung gewinnt


def test_legende_und_farben():
    from pathlib import Path

    from modern import seite_zimmer as sz

    assert any("EMR-Zimmer" in t for _k, _z, t in sz.LEGENDE)
    css = (Path(zk.__file__).parent / "themes.py").read_text(encoding="utf-8")
    # 1.64: geplante Sperre ruhig schiefergrau (kein Rot mehr); Rot nur für unbewohnbar (Mangel)
    assert "--zi-sperr-text: #4B5A5F" in css and "--zi-mangel-rand: #7A1A12" in css and ".m-kachel.emr" in css
