"""Neue Oberfläche: Zeilen, Filter, 1-Klick-Lösungen und Rückgängig – nur erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leute(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date(2026, 10, 15)
    p = [anreiseliste.Person(n, "GS ASS", heute + timedelta(days=2), True, tn_id=str(i),
                             abreise=heute + timedelta(days=30))
         for i, n in enumerate(["Anders, Anna", "Berger, Bea", "Clever, Clara"], 1)]
    anreiseliste.speichern(p, {})
    yield heute
    aenderungen.verlauf_leeren()


def _kennung(heute):
    return (heute + timedelta(days=2)).isoformat()


def test_zeilen_ohne_zimmer_mit_vorschlag(leute):
    from belegung import zimmerplan as zp
    from modern import kern

    st = zp.laden()
    a = kern.anreisen(st, leute)
    assert a and kern.erste_offene(a) == _kennung(leute)
    zs = kern.zeilen(st, _kennung(leute), leute)
    assert len(zs) == 3 and all(z.status == "ohne" and z.vorschlag for z in zs)
    assert all(z.optionen[0].art == "vorschlag" and z.optionen[0].text.endswith("passt") for z in zs)
    assert kern.zaehlen(zs) == {"alle": 3, "handeln": 0, "maengel": 0, "ohne": 3}
    k = kern.kennzahlen(st, leute)
    assert k["frei"] > 0 and set(k) == {"frei", "belegt", "gesperrt"}


def test_vorschlaege_uebernehmen_und_rueckgaengig(leute):
    from belegung import zimmerplan as zp
    from modern import kern

    text = kern.vorschlaege_uebernehmen(_kennung(leute))
    assert "3 Zimmer" in text and len(zp.zuweisungen_laden()) == 3
    zs = kern.zeilen(zp.laden(), _kennung(leute), leute)
    assert all(z.status == "ok" and z.gespeichert for z in zs)
    ok, _ = kern.rueckgaengig()
    assert ok and zp.zuweisungen_laden() == []


def test_zuweisen_nur_angebotene_zimmer(leute):
    from belegung import zimmerplan as zp
    from modern import kern

    zs = kern.zeilen(zp.laden(), _kennung(leute), leute)
    erste, zweite = zs[0], zs[1]
    kern.zuweisen(erste.schluessel, erste.vorschlag)
    with pytest.raises(ValueError):                         # Einzelzimmer ist jetzt belegt
        if zp.laden().lage.zimmer[erste.vorschlag].betten == 1:
            kern.zuweisen(zweite.schluessel, erste.vorschlag)
        else:
            raise ValueError
    with pytest.raises(ValueError):
        kern.zuweisen("gibt-es-nicht", erste.vorschlag)


def test_konflikt_bekommt_gruenen_ausweichvorschlag(leute):
    from belegung import maengel as mg
    from belegung import zimmerplan as zp
    from modern import kern

    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zid = "GS-2-301"
    zp.zuweisungen_speichern([zp.Zuteilung(b["Anders"], st.lage.zimmer[zid])])
    mg.setzen(zid, "schimmel", True, leute)                # danach unbewohnbar → Planung passt nicht mehr
    z = next(x for x in kern.zeilen(zp.laden(), _kennung(leute), leute) if x.name.startswith("Anders"))
    assert z.status == "handeln" and z.stufe == "krit" and z.gespeichert == zid
    assert z.vorschlag and z.vorschlag != zid and z.optionen[0].zimmer == z.vorschlag
    assert z.optionen[1].art == "aktuell"
    karte = next(k for k in kern.karten(zp.laden(), leute) if k.id == "unbewohnbar")
    assert karte.stufe == "dringend" and karte.aktion.schluessel == "konflikte" and "Schimmel" in karte.detail
    kern.ausfuehren("konflikte", leute)
    neu = {x["person"]: x["zimmer"] for x in zp.zuweisungen_laden()}
    assert neu[b["Anders"].schluessel] == z.vorschlag
    assert "unbewohnbar" not in {k.id for k in kern.karten(zp.laden(), leute)}


def test_karten_spaeter_und_automatisch_oeffnen(leute):
    from belegung import zimmerplan as zp
    from modern import kern

    ks = kern.karten(zp.laden(), leute)
    anr = next(k for k in ks if k.id.startswith("anreise:"))
    assert anr.stufe == "dringend" and anr.aktion.schluessel == f"vorschlaege:{_kennung(leute)}"
    assert all(k.aktion or k.zweite or k.hinweis.startswith(kern.HAUPTPROGRAMM) for k in ks)
    assert kern.automatisch_oeffnen(ks, leute) and not kern.automatisch_oeffnen(ks, leute)   # einmal am Tag
    kern.spaeter_setzen(anr.id, heute=leute)
    assert anr.id not in {k.id for k in kern.karten(zp.laden(), leute)}
    assert anr.id in {k.id for k in kern.karten(zp.laden(), leute + timedelta(days=1))}
    kern.ausfuehren(anr.aktion.schluessel, leute)
    assert not any(k.id.startswith("anreise:") for k in kern.karten(zp.laden(), leute + timedelta(days=1)))


def test_symbol_je_aufgabentyp_und_willkommen(tmp_path, monkeypatch):
    from modern import kern

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))     # nie in den echten Datenordner schreiben

    assert kern.symbol("anreise:2026-10-26") == "flight_land"
    assert kern.symbol("reinigung_dringend") == "cleaning_services"
    assert kern.symbol("engpass_emr") == "trending_down"
    assert kern.symbol("unbekannt") == "task_alt"
    assert kern.willkommen_zeigen()
    kern.willkommen_weg()
    assert not kern.willkommen_zeigen()
