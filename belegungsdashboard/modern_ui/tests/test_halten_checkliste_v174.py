"""1.74: Zimmer bei Unterbrechung (Praktikum) gehalten, Checkliste je Mietvertrag (erfundene Daten)."""

from datetime import date, timedelta
from types import SimpleNamespace as NS

import pytest

import modern.kern  # noqa: F401
from belegung.gebaeudeplan import Belegung

from modern import mieter_checkliste as mc
from modern import zimmer_halten as zh

H = date(2026, 11, 27)


def _b(von, bis, name="Beispiel, Erika", person="", art="belegt", zimmer="GS-2-101"):
    return Belegung(zimmer, von, bis, art, name, "GS IK 2506", "", person)


def test_luecke_wird_gehalten():
    a = _b(date(2026, 1, 21), date(2026, 9, 30))
    b = _b(date(2027, 4, 1), date(2027, 6, 24), name="Erika Beispiel")       # gleicher Name, andere Reihenfolge
    neu = zh.luecken([a, b], 275)
    assert len(neu) == 1
    g = neu[0]
    assert (g.von, g.bis, g.art) == (date(2026, 10, 1), date(2027, 3, 31), "belegt") and zh.ist_gehalten(g)


def test_keine_luecke_bei_fremden_zu_lang_oder_aus():
    a = _b(date(2026, 1, 1), date(2026, 3, 31))
    fremd = _b(date(2026, 6, 1), date(2026, 8, 31), name="Probehaus, Kim")
    zu_lang = _b(date(2027, 6, 1), date(2027, 8, 31))
    anschluss = _b(date(2026, 4, 1), date(2026, 5, 31))                            # direkt anschließend: keine Lücke
    assert zh.luecken([a, fremd], 275) == []
    assert zh.luecken([a, zu_lang], 275) == []
    assert zh.luecken([a, anschluss], 275) == []
    assert zh.luecken([a, _b(date(2026, 6, 1), date(2026, 8, 31))], 0) == []          # Einstellung 0 = aus


def test_doppelzimmer_nur_ein_bett():
    lage = NS(belegungen={"GS-2-101": [_b(date(2026, 1, 1), date(2026, 10, 31)), _b(date(2027, 2, 1), date(2027, 4, 30)),
                                       _b(date(2026, 1, 1), date(2027, 6, 30), name="Probehaus, Kim")]})
    assert zh.anwenden(lage, 275) == 1
    am = [b for b in lage.belegungen["GS-2-101"] if b.von <= date(2026, 12, 15) <= b.bis]
    assert len(am) == 2                                          # Kim + gehaltenes Bett – kein „gesperrt“ fürs ganze Zimmer


def test_abreise_am_ende_der_luecke_entfaellt(monkeypatch):
    from belegung import cockpit

    from modern import abreise_kern as ak

    g = zh.luecken([_b(date(2026, 1, 1), date(2026, 11, 20)), _b(date(2026, 12, 1), date(2027, 3, 31))], 275)[0]
    stand = NS(lage=NS(belegungen={"GS-2-101": [g]}))
    falsch = cockpit.Abreise(g.bis, "Erika Beispiel", "", "GS-2-101", None, "belegt", None, "")
    echt = cockpit.Abreise(H, "Probehaus, Kim", "", "GS-2-102", None, "belegt", None, "")
    monkeypatch.setattr(cockpit, "abreiseliste", lambda st, v, b: [falsch, echt])
    assert [a.name for a in ak.abreisen(stand, H, H + timedelta(days=30), personen=[])] == ["Probehaus, Kim"]


@pytest.fixture
def ablage(monkeypatch):
    daten = {}
    from belegung import speicher

    monkeypatch.setattr(speicher, "lesen", lambda name, std=None, *a, **k: daten.get(name, std))
    monkeypatch.setattr(speicher, "schreiben", lambda name, wert, *a, **k: daten.__setitem__(name, wert))
    import modern.kern as kern

    monkeypatch.setattr(kern, "_schritt", lambda titel, fn, dateien=None: fn())
    return daten


def _mv(von=date(2026, 11, 1), bis=date(2027, 4, 30), kaution=False):
    return NS(nr="26-001", von=von, bis=bis, kaution=kaution, nachname="Beispiel", name="Erika Beispiel")


def test_checkliste_punkte_und_haken(ablage):
    mv = _mv()
    ps = mc.punkte(mv, H)
    assert [p.abschnitt for p in ps] == ["Einzug"] * 6                         # ohne Kaution, Auszug noch fern
    assert len(mc.punkte(_mv(kaution=True), H)) == 7
    assert any(p.abschnitt == "Auszug" for p in mc.punkte(mv, H, gekuendigt=True))
    mc.setzen("26-001", "vertrag", True)
    mc.eigener_punkt("26-001", "Kopie Ausweis")
    assert mc.stand(mv, H) == (1, 7)
    eigen = [p for p in mc.punkte(mv, H) if p.eigen][0]
    mc.setzen("26-001", eigen.id, True)
    assert mc.stand(mv, H) == (2, 7)
    mc.eigenen_entfernen("26-001", eigen.id)
    mc.setzen("26-001", "vertrag", False)
    assert mc.stand(mv, H) == (0, 6)
    with pytest.raises(ValueError):
        mc.eigener_punkt("26-001", "  ")


def test_cockpit_nach_14_tagen(ablage):
    alt, neu = _mv(von=H - timedelta(days=20)), _mv(von=H - timedelta(days=3))
    neu.nr = "26-002"
    assert [mv.nr for mv, _o in mc.offen_im_cockpit([alt, neu], H)] == ["26-001"]
    for pid, _t in mc.EINZUG:
        mc.setzen("26-001", pid, True)
    assert mc.offen_im_cockpit([alt], H) == []
