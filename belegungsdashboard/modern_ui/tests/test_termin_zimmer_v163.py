"""1.63: Zimmer zu An-/Abreise-Terminen (Tooltip und Menü im Cockpit und unter Termine)."""

from datetime import date
from types import SimpleNamespace as NS

from modern import termin_zimmer as tz


def _p(schl, name, an, ab, gruppe="Gast", internat=True):
    return NS(schluessel=schl, name=name, anreise=an, abreise=ab, gruppe=gruppe, massnahme="", internat=internat,
              erinnerung_am=None)


def _b(person, name, von, bis, art="belegt"):
    return NS(person=person, name=name, von=von, bis=bis, art=art)


PS = [_p("a", "Beispiel, Erika", date(2026, 11, 25), date(2026, 12, 1)),
      _p("b", "Musterhoff, Kim", date(2026, 11, 25), date(2026, 12, 1)),
      _p("c", "Probehaus, Alex", date(2026, 11, 30), date(2026, 12, 6), gruppe="EMR")]
LAGE = NS(belegungen={"GS-2-101": [_b("a", "Beispiel, Erika", date(2026, 11, 25), date(2026, 12, 1))],
                      "GS-2-103": [_b("", "Musterhoff, Kim", date(2026, 11, 25), date(2026, 12, 1), "geplant"),
                                   _b("x", "Probehaus, Alex", date(2026, 1, 1), date(2026, 2, 1))],
                      "GS-3.1-E05": [_b("", "", date(2026, 1, 1), date(2099, 1, 1), "gesperrt")]})


def kurz(z):
    return z.removeprefix("GS-")


def test_abreisetag_mit_zimmern():
    zs = tz.zeilen("abreisetag:2026-12-01:andere", PS, LAGE, kurz)
    assert zs == [("Beispiel, Erika", "2-101", "GS-2-101"), ("Musterhoff, Kim", "2-103", "GS-2-103")]
    assert tz.kurztext(zs) == "Zimmer 2-101, 2-103"
    assert "Beispiel, Erika – 2-101" in tz.tooltip(zs)


def test_cockpit_karte_und_anreise():
    assert len(tz.zeilen("termin:anreise:2026-11-25", PS, LAGE, kurz)) == 2
    zs = tz.zeilen("anreise:2026-11-29", PS, LAGE, kurz)        # EMR: Ankunft einen Tag vor dem Listendatum
    assert [n for n, *_ in zs] == ["Probehaus, Alex"]
    assert zs[0][1] == "2-103"                                 # über den Namen, zeitlich nächste Belegung


def test_ohne_zimmer_und_unbekannt():
    lage = NS(belegungen={})
    zs = tz.zeilen("abreise:a", PS, lage, kurz)
    assert zs == [("Beispiel, Erika", "ohne Zimmer", "")]
    assert tz.kurztext(zs) == "noch ohne Zimmer"
    assert tz.zeilen("uwt:X:2026-01-01:an", PS, lage) == [] and tz.zeilen("", PS, lage) == []


def test_viele_zimmer_gekuerzt():
    zs = [(f"N{i}", f"2-1{i:02d}", f"GS-2-1{i:02d}") for i in range(7)]
    assert tz.kurztext(zs).endswith("+3")
    assert "weitere" in tz.tooltip(zs, max_zeilen=5)
