"""1.67: Gebäudeplan (RIOS, ohne TN-Nummer) ↔ Anreiseliste – „Ist das dieselbe Person?“ (erfundene Namen)."""

from datetime import date
from types import SimpleNamespace as NS

import pytest

from belegung.gebaeudeplan import Belegung

import modern.kern  # noqa: F401 – Einhängepunkte vor dem Ersetzen des Speichers
from modern import gleiche_person as gp

H = date(2026, 11, 25)


def _bedarf(schl, name, von, bis, gruppe="EMR", massnahme="GS EMR ASS 2611"):
    return NS(schluessel=schl, name=name, von=von, bis=bis, gruppe=gruppe, massnahme=massnahme)


def _stand(plan, bedarf, zuw=()):
    return NS(plan=NS(belegungen=plan), bedarf=bedarf, zuweisungen=list(zuw))


@pytest.fixture
def ablage(monkeypatch):
    daten = {}
    from belegung import protokoll, speicher

    monkeypatch.setattr(speicher, "lesen", lambda name, std=None, *a, **k: daten.get(name, std))
    monkeypatch.setattr(speicher, "schreiben", lambda name, wert, *a, **k: daten.__setitem__(name, wert))
    monkeypatch.setattr(protokoll, "eintragen", lambda *a, **k: None)
    import modern.kern as kern

    monkeypatch.setattr(kern, "_schritt", lambda titel, fn, dateien=None: fn())
    return daten


def test_woerter_ohne_umlaut_und_schreibweise():
    assert gp.woerter("Müller-Lüdenscheidt, Jörg") == gp.woerter("MUELLER Luedenscheidt Joerg")
    assert gp.aehnlich("Beispiel, Erika", "Beispiel, Erika Maria")[0] == 1.0
    assert gp.aehnlich("Beispiel, Erika", "Probehaus, Kim")[0] == 0.0


def test_vorschlag_bei_anderer_schreibweise_und_emr_zeitraum():
    # Gebäudeplan: Umlaut ausgeschrieben, Zimmer ab Vortag und 3 Wochen länger gebucht → Hauptprogramm verbindet nicht
    plan = [Belegung("GS-2-105", date(2026, 11, 22), date(2026, 12, 20), "belegt", "Mueller, Erika", "EMR")]
    b = _bedarf("id:900", "Müller, Erika", date(2026, 11, 23), date(2026, 11, 28))
    vs = gp.vorschlaege(_stand(plan, [b], [{"person": "id:900", "zimmer": "GS-2-110"}]), H, {"verbunden": [], "nein": []})
    assert len(vs) == 1
    v = vs[0]
    assert (v.person, v.zimmer, v.geplant, v.tage) == ("id:900", "GS-2-105", "GS-2-110", 0)
    assert "gleich" in v.grund


def test_kein_vorschlag_wenn_hauptprogramm_verbindet_oder_fremd():
    plan = [Belegung("GS-2-105", date(2026, 11, 22), date(2026, 11, 28), "belegt", "Beispiel, Erika", "EMR"),
            Belegung("GS-2-106", date(2026, 11, 22), date(2026, 11, 28), "belegt", "Probehaus, Kim", "RVT"),
            Belegung("GS-2-107", date(2026, 11, 22), date(2027, 3, 1), "belegt", "Mieter, Alex", "Miete")]
    bs = [_bedarf("id:1", "Beispiel, Erika", date(2026, 11, 23), date(2026, 11, 28)),   # streng gleich → kein Fall
          _bedarf("id:2", "Musterhoff, Alex", date(2026, 11, 23), date(2026, 11, 28)),  # anderer Name
          _bedarf("id:3", "Probehaus, Kim", date(2027, 2, 1), date(2027, 3, 1))]         # Zeitraum zu weit weg
    assert gp.vorschlaege(_stand(plan, bs), H, {"verbunden": [], "nein": []}) == []


def test_nein_wird_nicht_wieder_gefragt_und_ja_verbindet(ablage):
    plan = [Belegung("GS-2-105", date(2026, 11, 22), date(2026, 12, 20), "belegt", "Muehlhoff Erika Maria", "EMR")]
    b = _bedarf("id:900", "Mühlhoff, Erika", date(2026, 11, 23), date(2026, 11, 28))
    st = _stand(plan, [b], [{"person": "id:900", "name": "Mühlhoff, Erika", "zimmer": "GS-2-110", "von": "2026-11-23",
                             "bis": "2026-11-28"}])
    ablage["zimmer_zuweisungen.json"] = {"zuweisungen": list(st.zuweisungen)}
    v = gp.vorschlaege(st, H)[0]
    gp.ablehnen(v)
    assert gp.vorschlaege(st, H) == []
    ablage[gp.DATEI]["nein"] = []
    txt = gp.verbinden(gp.vorschlaege(st, H)[0])
    assert "entfällt" in txt
    zuw = ablage["zimmer_zuweisungen.json"]["zuweisungen"]
    eigen = [z for z in zuw if z["person"] == "id:900"]
    assert len(eigen) == 1 and eigen[0]["zimmer"] == "GS-2-105" and eigen[0]["vorrang"] == "plan"
    assert gp.vorschlaege(st, H) == []                     # verbunden → keine Frage mehr
    gp.loesen("id:900")
    assert gp.laden()["verbunden"] == []


def test_anwenden_setzt_person_und_entfernt_doppelte_planung():
    eintrag = Belegung("GS-2-105", date(2026, 11, 22), date(2026, 12, 20), "belegt", "Beispiel Erika Maria", "EMR")
    eigen_gleich = Belegung("GS-2-105", date(2026, 11, 23), date(2026, 11, 28), "geplant", "Beispiel, Erika", "EMR",
                            person="id:900")
    eigen_anders = Belegung("GS-2-110", date(2026, 11, 23), date(2026, 11, 28), "geplant", "Beispiel, Erika", "EMR",
                            person="id:900")
    lage = NS(belegungen={"GS-2-105": [eintrag, eigen_gleich], "GS-2-110": [eigen_anders]},
              abgleich=[NS(person="id:900"), NS(person="id:1")])
    n = gp.anwenden(lage, [{"person": "id:900", "gp_name": "Beispiel Erika Maria", "zimmer": "GS-2-105",
                            "von": "2026-11-22", "bis": "2026-12-20"}])
    assert n == 1
    assert lage.belegungen["GS-2-105"] == [eintrag] and eintrag.person == "id:900"
    assert lage.belegungen["GS-2-110"] == []
    assert [a.person for a in lage.abgleich] == ["id:1"]


def test_anwenden_ohne_eintrag_laesst_planung():
    eigen = Belegung("GS-2-110", date(2026, 11, 23), date(2026, 11, 28), "geplant", "Beispiel, Erika", "EMR", person="id:9")
    lage = NS(belegungen={"GS-2-110": [eigen]}, abgleich=[])
    assert gp.anwenden(lage, [{"person": "id:9", "gp_name": "Beispiel Erika", "zimmer": "GS-2-105",
                               "von": "2026-11-22", "bis": "2026-12-20"}]) == 0
    assert lage.belegungen["GS-2-110"] == [eigen]


def test_eingehaengt_und_menue():
    from belegung import zimmerplan as zp

    from modern import menueband, symbole

    assert gp._ORIG and zp.lage_bauen is not gp._ORIG["lage_bauen"]
    texte = [pk.text for r in menueband.reiter({}) if r.key == "anreisen" for g in r.gruppen for pk in g.punkte]
    assert "Gleiche Person?" in texte
    assert symbole.PIKTO_FARBIG["gleiche_person"] == "inn_gleiche_person"


# ---- 1.67: Mietverträge auch für die Rolle Mitarbeiter --------------------------------------------------------------

def test_mietunterlagen_ausweichordner(monkeypatch, tmp_path):
    from belegung import speicher

    from modern import export_ziel, mieter_kern as mk

    gesperrt, daten = tmp_path / "Leitung", tmp_path / "Daten"
    monkeypatch.setattr(speicher, "einstellungen", lambda: {"export_ordner": str(gesperrt)})
    monkeypatch.setattr(speicher, "pfad", lambda name: str(daten / name))
    monkeypatch.setattr(export_ziel, "_ordner_beschreibbar", lambda o: o != gesperrt)
    o = mk.ablage()
    assert o == daten / "Mietunterlagen"
    assert "nicht in" in mk.ablage_hinweis(o) and mk.ablage_hinweis(gesperrt) == ""


def test_mietvertrag_ohne_admin_pruefung():
    """Neuer Vertrag, Verlängern, Kündigen: keine Administrator-Prüfung (Mitarbeiter dürfen das)."""
    import inspect

    from modern import kuendigung_kern, mieter_kern

    for f in (mieter_kern.neuer_vertrag, mieter_kern.verlaengern, kuendigung_kern.kuendigen):
        assert "admin_pruefen" not in inspect.getsource(f)
