"""1.65: Abreisen vollständig – auch laut Anreiseliste, wenn der Plan die Person noch länger führt (EMR)."""

from datetime import date
from types import SimpleNamespace as NS

from belegung import cockpit

from modern import abreise_kern as abk

H = date(2026, 11, 25)


def _p(schl, name, ab, internat=True, gruppe="EMR"):
    return NS(schluessel=schl, name=name, abreise=ab, internat=internat, gruppe=gruppe, massnahme="EMR ASS",
              anreise=date(2026, 11, 23))


LAGE = NS(belegungen={"GS-2-101": [NS(art="geplant", person="a", name="Beispiel, Erika", von=date(2026, 11, 22),
                                       bis=date(2026, 12, 28))]})


def test_emr_aus_anreiseliste_ergaenzt():
    plan = []                                            # Plan führt die Person noch bis 28.12.
    erg = abk.ergaenzen(plan, [_p("a", "Beispiel, Erika", H)], LAGE, H, H)
    assert len(erg) == 1 and erg[0].zimmer == "GS-2-101" and erg[0].art == abk.ART_LISTE
    assert abk.plan_bis(LAGE, "GS-2-101", "a", "Beispiel, Erika") == date(2026, 12, 28)


def test_keine_doppelten_und_nur_internat_im_zeitraum():
    plan = [cockpit.Abreise(H, "Erika Beispiel", "EMR", "GS-2-101", None, "geplant", None, "")]
    ps = [_p("a", "Beispiel, Erika", H), _p("b", "Musterhoff, Kim", H, internat=False),
          _p("c", "Probehaus, Alex", date(2026, 12, 1)), _p("d", "Kim Probe", None)]
    erg = abk.ergaenzen(plan, ps, LAGE, H, date(2026, 11, 30))
    assert [a.name for a in erg] == ["Erika Beispiel"]


def test_ohne_zimmer():
    erg = abk.ergaenzen([], [_p("x", "Probehaus, Alex", H)], NS(belegungen={}), H, H)
    assert erg[0].zimmer == "" and erg[0].art == abk.ART_LISTE
