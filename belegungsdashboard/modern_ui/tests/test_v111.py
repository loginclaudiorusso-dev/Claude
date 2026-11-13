"""1.11 – Zimmerfilter in der Übersicht (Einzel-/Doppelzimmer, Tier …), Einzelzimmer als neuer Filter."""

import inspect
from types import SimpleNamespace as NS

from modern import zimmer_kern as zk


def test_einzelzimmer_filter():
    f = zk.filter_bauen("", "", {"einzel"}, "", {})
    assert f.einzel and "einzel" not in f.merkmale
    stand = NS(lage=NS(unbewohnbar=set()))
    ez, dz = NS(zimmer=NS(id="A", betten=1), status="frei"), NS(zimmer=NS(id="B", betten=2), status="frei")
    assert zk._zustand_passt(stand, f, ez) and not zk._zustand_passt(stand, f, dz)
    assert zk._zustand_passt(stand, zk.filter_bauen("", "", set(), "", {}), dz)
    assert list(zk.MERKMALE)[:3] == ["einzel", "doppel", "tiere"]


def test_uebersicht_ohne_zimmerfilter_unveraendert():
    assert zk.uebersicht_passend(None, set(), {"maengel": ["stufe:3"]}, None) is None   # Mangelart regelt die Übersicht


def test_uebersicht_hat_filterknopf():
    from modern import seite_zimmer as sz

    q = inspect.getsource(sz._uebersicht)
    assert "_filter_menue_inhalt(a)" in q and "uebersicht_passend" in q and "k.zimmer in pf" in q


def test_gewaehlter_tag_fuer_neue_person():
    from datetime import date

    from modern import seite_zimmer as sz

    heute, spaeter = date(2026, 11, 13), date(2026, 12, 10)

    class A:
        def __init__(self, seite, ansicht, tag):
            self.heute, self.seite, self.ansicht, self.zu_tag = heute, seite, {"zimmer": ansicht}, tag

        def ansicht_von(self, s, std):
            return self.ansicht.get(s, std)

    assert sz.gewaehlter_tag(A("zimmer", "uebersicht", spaeter)) == spaeter          # in die Zukunft geblättert
    assert sz.gewaehlter_tag(A("zimmer", "uebersicht", date(2026, 11, 1))) == heute   # Vergangenheit → heute
    assert sz.gewaehlter_tag(A("zimmer", "liste", spaeter)) == heute                  # andere Ansicht → heute
    q = inspect.getsource(sz.person_hinzu_panel)
    assert 'value=ab.isoformat()' in q and "a.heute.isoformat()" not in q
