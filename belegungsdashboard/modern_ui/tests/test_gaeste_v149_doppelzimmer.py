"""1.49 – Gäste & Mieter: Gast mit Doppelzimmer (allein oder mit Begleitperson). Erfundene Namen."""

from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


VON, BIS = date(2027, 5, 3), date(2027, 5, 7)


def test_zu_zweit_nur_doppelzimmer_mit_zwei_freien_betten(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    dz = gk.zimmer_frei(VON, BIS, zu_zweit=True)
    stand = zp.laden()
    assert dz and all(stand.lage.zimmer[z].betten > 1 for z in dz)
    alle = gk.zimmer_frei(VON, BIS, doppelzimmer=True)
    assert len(alle) >= len(dz) and stand.lage.zimmer[next(iter(alle))].betten > 1      # Doppelzimmer zuerst


def test_gast_mit_begleitung_teilt_sich_das_doppelzimmer(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    zid = next(iter(gk.zimmer_frei(VON, BIS, zu_zweit=True)))
    text = gk.anlegen("Beispiel, Erika", VON, BIS, "w", "Hospitation", True, "Musterhoff, Alex", "m", zid)
    assert "Erika" in text and "Alex" in text
    stand = zp.laden()
    im = [b.name for b in stand.lage.belegungen[zid] if b.art in ("belegt", "geplant")]
    assert sorted(im) == ["Beispiel, Erika", "Musterhoff, Alex"]
    zeilen = {g.name: g for g in gk.liste(stand, VON)}
    assert zeilen["Beispiel, Erika"].begleitung == "Musterhoff, Alex" and zeilen["Beispiel, Erika"].zimmer == zid
    # ein fremder Gast darf nicht dazu
    fremd = zp.Bedarf("x", "Fremd, Kim", "Gast", "Gast", VON, BIS, "w")
    assert zp.passt(stand.lage, stand.lage.zimmer[zid], fremd) is not None


def test_gast_ohne_paar_wohnt_allein(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    zid = next(iter(gk.zimmer_frei(VON, BIS, zu_zweit=True)))
    gk.anlegen("Allein, Kim", VON, BIS, "", "", True, "", "", zid)
    stand = zp.laden()
    zweiter = zp.Bedarf("y", "Noch, Einer", "Gast", "Gast", VON, BIS, "")
    assert zp.passt(stand.lage, stand.lage.zimmer[zid], zweiter) is not None
    assert gk.liste(stand, VON)[0].dz_wunsch
    with pytest.raises(ValueError):
        gk.anlegen("Ohne, Haken", VON, BIS, "", "", False, "Begleitung, Eine")


def test_bereich_gaeste_und_mieter():
    from modern import register

    assert register.TITEL["mieter"] == "Gäste & Mieter"
    q = (Path(__file__).parents[1] / "modern" / "seiten.py").read_text(encoding="utf-8")
    assert "def gast_neu_panel" in q and "Begleitperson" in q
