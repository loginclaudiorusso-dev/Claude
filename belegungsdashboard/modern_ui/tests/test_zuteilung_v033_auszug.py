"""0.33: Abbruch / vorzeitiger Auszug in der Zimmerkarte – das Zimmer wird wirklich frei. Erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def bewohner(tmp_path, monkeypatch):
    """Wie im gemeldeten Fall: Person aus der Anreiseliste, im Gebäudeplan im selben Zimmer, Planung „fest“."""
    from belegung import aenderungen, anreiseliste, gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    h = date.today()
    an, ab = h - timedelta(days=9), h + timedelta(days=80)
    anreiseliste.speichern([anreiseliste.Person("Abbruch, Alma", "GS RVL", an, True, tn_id="995", abreise=ab,
                                                bemerkung="Rollator")], {})
    p = zp.laden().bedarf[0]
    kern.zuweisen(p.schluessel, "GS-3.1-104")
    zp.status_setzen(p.schluessel, True)
    gebaeudeplan.speichern(gebaeudeplan.Gebaeudeplan("Plan.docx", h - timedelta(days=1), zp.mitgelieferte_zimmer(), [
        gebaeudeplan.Belegung("GS-3.1-104", an, ab, "belegt", "Abbruch, Alma", "GS RVL 2610"),
        gebaeudeplan.Belegung("GS-3.1-105", an, ab, "belegt", "Nurplan, Nils", "GS RVL 2610")]), {"pfad": "Plan.docx"})
    aenderungen.verlauf_leeren()
    yield h, p.schluessel
    aenderungen.verlauf_leeren()


def test_abbruch_macht_zimmer_frei(bewohner):
    from belegung import anreiseliste
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp
    from modern import historie_kern as hk
    from modern import kern
    from modern import zimmer_kern as zk

    h, person = bewohner
    st = zp.laden()
    hk.erfassen(st, h)
    assert st.lage.status_am("GS-3.1-104", h + timedelta(days=10))[0] != "frei"
    text = zk.auszug("GS-3.1-104", person, h, "Abbruch")
    assert "ist ab dem" in text and "Belegungssystem" in text
    st = zp.laden()
    assert st.lage.status_am("GS-3.1-104", h + timedelta(days=2))[0] == "frei"
    p = next(x for x in anreiseliste.laden()[0] if x.name == "Abbruch, Alma")
    assert p.abreise == h and p.bemerkung == f"Rollator · Abbruch am {h:%d.%m.%Y}"
    assert gebaeudeplan.laden()[1]["quelle"] == {"pfad": "Plan.docx"}           # kein neuer Import ausgelöst
    hk.erfassen(st, h)
    assert next(a for a in hk.alle() if a.name == "Abbruch, Alma").bis == h.isoformat()   # Historie: neues Ende
    kern.rueckgaengig()
    assert zp.laden().lage.status_am("GS-3.1-104", h + timedelta(days=10))[0] != "frei"


def test_abbruch_nur_gebaeudeplan_und_pruefungen(bewohner):
    from belegung import zimmerplan as zp
    from modern import zimmer_kern as zk

    h, person = bewohner
    nils = next(b for b in zp.bewohner_im_zimmer(zp.laden(), "GS-3.1-105", h))
    zk.auszug("GS-3.1-105", nils.schluessel, h + timedelta(days=3), "Vorzeitiger Auszug")
    assert zp.laden().lage.status_am("GS-3.1-105", h + timedelta(days=5))[0] == "frei"
    with pytest.raises(ValueError, match="vor der bisherigen Abreise"):
        zk.auszug("GS-3.1-104", person, h + timedelta(days=200))
    with pytest.raises(ValueError, match="vor dem Einzug"):
        zk.auszug("GS-3.1-104", person, h - timedelta(days=30))
    with pytest.raises(ValueError, match="wohnt"):
        zk.auszug("GS-3.1-106", person, h)
