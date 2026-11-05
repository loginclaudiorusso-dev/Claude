"""0.68: Glocke und Hilfe in der Titelleiste, Drucken und Hilfe unter Datei, F1-Hilfe je Seite."""

from modern import hilfe_kern as hk
from modern import menueband as mb
from modern import register


def test_hilfe_fuer_jede_seite():
    for k, _t, _i, _g in register.NAV:
        titel, text, punkte = hk.fuer(k, None)
        assert titel and text and punkte, k
    t, _x, p = hk.fuer("anreisen", "eintragen")
    assert t == "Anreisen" and "Abtipp" in p[0]                       # Ansicht zuerst, dann die Seite
    assert hk.fuer("unbekannt", None)[0] == "Hilfe"
    assert {"F1", "Strg+P", "Strg+K", "Strg+Z"} <= {t for t, _w in hk.TASTEN}


def test_druckausgaben_bekannt():
    bekannt = {"anreise", "schluessel", "schilder", "abreise", "reinigung", "wochenblatt", "zimmer_liste", "zimmer_ohne", "fm"}
    for liste in hk.DRUCK.values():
        assert liste and {k for _t, k in liste} <= bekannt
    assert hk.druckausgaben("heute", None) == []
    assert [t for t, _k in hk.druckausgaben("anreisen", "zuteilen")] == ["Anreiseliste", "Schlüsselliste", "Zimmerschilder"]


def test_glocke_hilfe_drucken_an_einer_stelle():
    datei = [p.ziel for p in mb.DATEI]
    assert ("aktion", "drucken") in datei and ("aktion", "hilfe") in datei and datei[-1] == ("aktion", "optionen")
    titel = [p.ziel for p in mb.TITELLEISTE]
    assert ("aktion", "neuigkeiten") in titel and ("aktion", "hilfe") in titel
    im_band = {q.ziel for r in mb.reiter({}) for g in r.gruppen for p in g.punkte for q in [p] + p.menue
               if q.ziel and q.ziel[0] == "aktion"}
    assert ("aktion", "neuigkeiten") not in im_band and ("aktion", "drucken") not in im_band
