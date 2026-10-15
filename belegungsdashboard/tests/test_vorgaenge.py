"""„Heute“: Vorgänge nach Dringlichkeit, je eine Aktion – und der eine Ablauf für „Zimmer wechseln“. Nur erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leute(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date(2026, 10, 15)
    p = [anreiseliste.Person("Anders, Anna", "GS ASS", heute + timedelta(days=2), True, tn_id="1",
                             abreise=heute + timedelta(days=30)),
         anreiseliste.Person("Berger, Bea", "GS ASS", heute + timedelta(days=2), True, tn_id="2",
                             abreise=heute + timedelta(days=30)),
         anreiseliste.Person("Clever, Clara", "GS ASS", heute + timedelta(days=10), True, tn_id="3",
                             abreise=heute + timedelta(days=40))]
    anreiseliste.speichern(p, {})
    yield heute
    aenderungen.verlauf_leeren()


def test_anreisen_ohne_zimmer_nach_naehe(leute):
    from belegung import vorgaenge
    from belegung import zimmerplan as zp

    v = vorgaenge.sammeln(zp.laden(), leute, engpaesse=False)
    anr = {x.id: x for x in v if x.id.startswith("anreise:")}
    nah, fern = anr[f"anreise:{leute + timedelta(days=2)}"], anr[f"anreise:{leute + timedelta(days=10)}"]
    assert nah.stufe == "dringend" and "2 Personen ohne Zimmer" in nah.titel and nah.aktion == "Zuteilen"
    assert fern.stufe == "bald"
    assert v.index(nah) < v.index(fern)                       # dringend zuerst


def test_mit_zimmer_kein_vorgang_aber_eintragen(leute):
    from belegung import vorgaenge
    from belegung import zimmerplan as zp

    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Anders"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Berger"], st.lage.zimmer["GS-2-302"])])
    v = vorgaenge.sammeln(zp.laden(), leute, engpaesse=False)
    assert f"anreise:{leute + timedelta(days=2)}" not in {x.id for x in v}
    ein = next(x for x in v if x.id == "eintragen")
    assert ein.titel.startswith("2 Buchungen") and ein.stufe == "dringend"   # Anreise in 2 Tagen


def test_erinnerungen_nach_arbeit_und_erledigbar(leute):
    from belegung import termine as tm
    from belegung import vorgaenge

    t = tm.Termin("t1", leute - timedelta(days=5), "Rückruf Kostenträger", erinnern_am=leute - timedelta(days=5))
    v = vorgaenge.sammeln(None, leute, termine=[t])
    assert v[0].erledigen == "t1" and "seit 5 Tagen" in v[0].detail
    andere = vorgaenge.Vorgang("anreise:x", "bald", "Anreise", "", "Zuteilen", "anreise:x")
    assert sorted([v[0], andere], key=lambda x: x.sortierung)[0] is andere      # Arbeit vor Erinnerung


def test_zimmer_wechseln_geplant_nur_die_person(leute, qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from belegung import zimmerplan as zp
    from belegung.ui import aenderung_ui
    from belegung.ui.basis import Zustand

    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Anders"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Berger"], st.lage.zimmer["GS-2-302"])])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    warnungen = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnungen.append(a[2]))
    z = Zustand()
    vorher = {x["person"]: x["zimmer"] for x in zp.zuweisungen_laden()}
    assert not aenderung_ui.zimmer_wechseln_geplant(None, z, zp.laden(), b["Anders"].schluessel, "GS-2-302")
    assert warnungen and "belegt" in warnungen[0]                          # Bea wohnt dort: abgelehnt
    assert {x["person"]: x["zimmer"] for x in zp.zuweisungen_laden()} == vorher
    assert aenderung_ui.zimmer_wechseln_geplant(None, z, zp.laden(), b["Anders"].schluessel, "GS-2-303")
    nachher = {x["person"]: x["zimmer"] for x in zp.zuweisungen_laden()}
    assert nachher == {**vorher, b["Anders"].schluessel: "GS-2-303"}          # nur Anna geändert


def test_daten_reiter_alte_nummern():
    from belegung.ui.seiten import daten

    assert all(n in daten.REITER for n in daten.REITER_VOR_614)
    assert "Gebäudeplan & ZKL" in daten.REITER
