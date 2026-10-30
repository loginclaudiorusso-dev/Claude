"""0.29: Zimmerhistorie, kontrastreichere Zimmerfarben, flexible Mietverträge – erfundene Daten."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _stand(*belegungen):
    from belegung import gebaeudeplan
    from belegung import zimmerplan as zp

    st = zp.laden()
    for zid, name, von, bis, art, person in belegungen:
        st.lage.belegungen.setdefault(zid, []).append(gebaeudeplan.Belegung(zid, von, bis, art, name, "GS RVL", person=person))
    return st


def test_historie_haelt_ehemalige_fest(leer):
    from modern import historie_kern as hk

    h = date(2030, 3, 1)
    st = _stand(("GS-3.1-122", "Ehemalig, Erik", h - timedelta(days=90), h + timedelta(days=5), "belegt", ""))
    hk.erfassen(st, h)
    hk.erfassen(_stand(), h + timedelta(days=30))              # neuer Gebäudeplan: Erik steht nicht mehr drin
    assert [a.name for a in hk.im_zimmer("GS-3.1-122", h + timedelta(days=30))] == ["Ehemalig, Erik"]
    t = hk.suchen("erik ehemalig", h + timedelta(days=30))
    assert t and t[0].kurz == "3.1-122" and t[0].zeitraum.endswith(f"{h + timedelta(days=5):%d.%m.%Y}")
    assert not hk.suchen("niemand", h)


def test_historie_umplanung_und_streichung(leer):
    from modern import historie_kern as hk

    h = date(2030, 3, 1)
    an = h + timedelta(days=10)
    hk.erfassen(_stand(("GS-3.2-101", "Geplant, Gina", an, an + timedelta(days=60), "geplant", "id:1"),
                       ("GS-3.2-102", "Weg, Willi", an, an + timedelta(days=60), "geplant", "id:2")), h)
    hk.erfassen(_stand(("GS-3.2-105", "Geplant, Gina", an, an + timedelta(days=60), "geplant", "id:1")), h)  # umgeplant, Willi gestrichen
    spaeter = an + timedelta(days=90)
    assert [a.kurz for a in hk.suchen("Gina", spaeter)] == ["3.2-105"]
    assert not hk.suchen("Willi", spaeter)                      # nie angereist → keine Historie
    # wie geplant eingezogen: im Gebäudeplan „belegt“ – nur einmal in der Historie
    hk.erfassen(_stand(("GS-3.2-105", "Geplant, Gina", an, an + timedelta(days=60), "belegt", "")), an + timedelta(days=2))
    assert len(hk.im_zimmer("GS-3.2-105", spaeter)) == 1 and hk.im_zimmer("GS-3.2-105", spaeter)[0].art == "belegt"


def test_historie_aus_sicherungen_und_aufraeumen(leer):
    import json

    from belegung import gebaeudeplan
    from modern import historie_kern as hk

    alt = leer / "Sicherungen" / "2030-01-05_120000_v6.28.0_Start" / "importe"
    alt.mkdir(parents=True)
    b = gebaeudeplan.Belegung("GS-6-101", date(2029, 9, 1), date(2029, 12, 20), "belegt", "Frueher, Frida", "GS FIAE")
    (alt / "gebaeudeplan.json").write_text(json.dumps({"belegungen": [b.zu_dict()]}), encoding="utf-8")
    hk.erfassen(_stand(), date(2030, 3, 1))
    assert [a.name for a in hk.im_zimmer("GS-6-101", date(2030, 3, 1))] == ["Frueher, Frida"]
    hk.erfassen(_stand(), date(2029 + hk.AUFBEWAHREN_JAHRE + 1, 1, 1))   # nach der Aufbewahrungsfrist gelöscht
    assert not hk.alle()


def test_zimmerkarte_zeigt_historie(leer):
    from belegung import zimmerplan as zp
    from modern import historie_kern as hk
    from modern import zimmer_kern as zk

    h = date.today()
    hk.erfassen(_stand(("GS-3.1-122", "Ehemalig, Erik", h - timedelta(days=200), h - timedelta(days=20), "belegt", "")), h)
    k = zk.karte(zp.laden(), "GS-3.1-122", h)
    assert [x.name for x in k.historie] == ["Ehemalig, Erik"]


def test_zimmerfarben_klar_unterscheidbar():
    """frei, belegt und geplant waren fast gleich dunkel (ΔE belegt/geplant 1,5) – jetzt klar getrennt."""
    from modern import stil

    assert "--frei: #2E7556" in stil.CSS and "--belegt: #4459A0" in stil.CSS
    assert ".m-kachel.geplant, .m-legende i.geplant { background: var(--fl); border: 1.5px dashed" in stil.CSS


VORLAGE = """=Mietvertrag
==§ 1 Mietzeit
?!flexibel Das Mietverhältnis beginnt am {von} und endet am {bis}.
?flexibel Das Mietverhältnis beginnt am {von}; es kann mit einer Frist von zwei Wochen beendet werden.
==§ 2 Miete
Die Miete beträgt {miete}.
"""


def test_flexibler_vertrag_nur_auf_wunsch(leer):
    from belegung import mieter as mt
    from modern import mieter_kern as mk

    mv = mt.Mietvertrag("30-001", "Frau", "Mia", "Muster", "GS-6-101", date(2030, 1, 1), date(2030, 6, 30))
    ueblich = mt.vertrag_html(mv, mk.vorlage_fuer(VORLAGE, False))
    flex = mt.vertrag_html(mv, mk.vorlage_fuer(VORLAGE, True))
    assert "endet am" in ueblich and "zwei Wochen" not in ueblich      # wie bisher (auch im Hauptprogramm)
    assert "zwei Wochen" in flex and "endet am" not in flex
    assert mt.vertrag_html(mv, VORLAGE) == ueblich                      # Hauptprogramm: immer der übliche Vertrag
    with pytest.raises(ValueError, match="flexibel"):
        mk.vorlage_fuer("==§ 1 Mietzeit\nText", True)                  # ohne Textstellen kein „flexibler“ Vertrag
    mk._flex_setzen("30-001", True)
    assert mk.flexible() == {"30-001"}
    mk._flex_setzen("30-001", False)
    assert mk.flexible() == set()


def test_unbewohnbar_erst_pruefen_dann_nur_angehakte(leer):
    """0.30: Planungen in unbewohnbaren Zimmern werden aufgelistet; umgeplant wird nur die Auswahl."""
    from belegung import anreiseliste, maengel
    from belegung import zimmerplan as zp
    from modern import kern

    h = date.today()
    an = h + timedelta(days=5)
    anreiseliste.speichern([anreiseliste.Person(n, "GS RVL", an, True, tn_id=str(950 + i), abreise=an + timedelta(days=60))
                            for i, n in enumerate(["Erste, Ella", "Zweite, Zoe"])], {})
    kern.vorschlaege_uebernehmen(an.isoformat(), "alle")
    st = zp.laden()
    zimmer = {b.name: st.zugewiesen(b.schluessel)["zimmer"] for b in st.bedarf}
    for z in set(zimmer.values()):
        maengel.setzen(z, "schimmel", True, h)                  # beide Zimmer werden unbewohnbar
    fs = kern.faelle(zp.laden(), h, nur_unbewohnbar=True)
    assert {f.name for f in fs} == {"Erste, Ella", "Zweite, Zoe"} and all(f.vorschlag and not f.wohnt for f in fs)
    assert all(f.grund.startswith("Schimmel") for f in fs)
    assert len({f.vorschlag for f in fs}) == 2                 # gemeinsam verteilt: nie zweimal dasselbe Zimmer
    ella = next(f for f in fs if f.name == "Erste, Ella")
    assert kern.ausweich_uebernehmen([ella.schluessel], h) == "1 Ausweichzimmer zugewiesen"
    st = zp.laden()
    neu = {b.name: st.zugewiesen(b.schluessel)["zimmer"] for b in st.bedarf}
    assert neu["Erste, Ella"] == ella.vorschlag and neu["Zweite, Zoe"] == zimmer["Zweite, Zoe"]   # Zoe unverändert
    with pytest.raises(ValueError):
        kern.ausweich_uebernehmen([], h)
    # wer schon eingezogen ist, bekommt keinen Vorschlag (das wäre ein Umzug)
    spaeter = [f for f in kern.faelle(zp.laden(), an + timedelta(days=3), nur_unbewohnbar=True) if f.name == "Zweite, Zoe"]
    assert spaeter and spaeter[0].wohnt and spaeter[0].vorschlag is None


def test_sammelknopf_ohne_doppelbelegung(leer):
    from belegung import anreiseliste, maengel
    from belegung import zimmerplan as zp
    from modern import kern

    h = date.today()
    an = h + timedelta(days=6)
    anreiseliste.speichern([anreiseliste.Person(f"Sammel, Sam{i}", "GS RVL", an, True, tn_id=str(960 + i),
                                                abreise=an + timedelta(days=40)) for i in range(5)], {})
    kern.vorschlaege_uebernehmen(an.isoformat(), "alle")
    st = zp.laden()
    for b in st.bedarf:
        maengel.setzen(st.zugewiesen(b.schluessel)["zimmer"], "schimmel", True, h)
    kern.konflikte_loesen(h)
    st = zp.laden()
    neu = [st.zugewiesen(b.schluessel)["zimmer"] for b in st.bedarf]
    assert len(set(neu)) == 5 and not set(neu) & set(st.lage.unbewohnbar)
