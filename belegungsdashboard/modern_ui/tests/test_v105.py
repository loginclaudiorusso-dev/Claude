"""1.05 – Neuanmeldungen je Monat; Austauschdatei zwischen altem und neuem Programm. Nur erfundene Daten."""

from __future__ import annotations

from datetime import date

import pytest

from modern import massnahmen_kern as mk


def _roh(kurse: dict, von=date(2021, 1, 1), bis=date(2027, 12, 31)) -> dict:
    return {"pivot": {"von": von.isoformat(), "bis": bis.isoformat(),
                      "kurse": {k: {"von": s.isoformat(), "werte": mk._rle(w)} for k, (s, w) in kurse.items()}}}


def _kurs(n: int) -> list[int]:
    return [n] * 730


def _vw(starts: dict) -> dict:
    return {f"GS VW {j % 100}{m:02d}": (date(j, m, 2), _kurs(n)) for (j, m), n in starts.items()}


def test_monate_ergeben_genau_die_welle():
    starts = {(j, m): 12 for j in range(2021, 2026) for m in (1, 7)}
    kurse = _vw(starts)
    kurse["GS VW 2601"] = (date(2026, 1, 5), _kurs(5))                # erst 5 gebucht
    roh = _roh(kurse)
    heute = date(2025, 11, 5)
    r = mk.neuanmeldungen(roh, heute, ["GS VW"], 4, 4, "mittel3")
    m = mk.monatlich(roh, heute, r, monate_zurueck=36)["GS VW"]
    for w in (z for z in r["GS VW"].zeilen if z.art != "ist"):
        a = mk.hj_start(w.hj)
        teile = [z for z in m.zeilen if (z.hj[0], z.hj[1]) in
                 {(mk._monat_plus(a, i).year, mk._monat_plus(a, i).month) for i in range(6)}]
        assert sum(z.erwartet for z in teile) == pytest.approx(w.erwartet)
        assert sum(z.klein for z in teile) == pytest.approx(max(w.klein, sum(z.ist + z.gebucht for z in teile)))
    jan = next(z for z in m.zeilen if z.hj[:2] == (2026, 1))
    assert jan.gebucht == 5 and jan.erwartet >= 5                      # gebucht steht im Startmonat
    assert next(z for z in m.zeilen if z.hj[:2] == (2025, 7)).art == "ist"
    assert next(z for z in m.zeilen if z.hj[:2] == (2025, 7)).erwartet == 12


def test_startmuster_aus_frueheren_wellen():
    starts = {(j, m): 10 for j in range(2022, 2025) for m in (1, 7)}
    eigene = [k for k in mk.kurse(_roh(_vw(starts)))]
    w = mk.startmuster(eigene, 1, date(2025, 11, 1))
    assert w[2] == pytest.approx(1.0) and sum(w) == pytest.approx(1.0)  # Winter: alles im Januar (3. Monat ab Nov)
    assert mk.startmuster([], 2, date(2025, 1, 1)) == [pytest.approx(1 / 6)] * 6


def test_monat_beschriftung():
    assert mk.hj_kurz((2027, 3, "m")) == "Mär 27" and mk.hj_text((2027, 3, "m")) == "März 2027"
    assert mk.hj_kurz((2027, 1)) == "W 27"


# ---- Austauschdatei ---------------------------------------------------------------------------------------------------
import copy  # noqa: E402
import json  # noqa: E402
from datetime import datetime  # noqa: E402

from modern import austausch_kern as ak  # noqa: E402


class Ablage:
    """Erfundener Datenordner im Arbeitsspeicher (wie speicher.lesen/schreiben)."""

    def __init__(self, dateien: dict | None = None):
        self.d = copy.deepcopy(dateien or {})

    def lesen(self, name, standard):
        return copy.deepcopy(self.d.get(name, standard))

    def schreiben(self, name, daten):
        self.d[name] = copy.deepcopy(daten)


def _person(name, tn, an, ab=None, **x):
    return {"name": name, "massnahme": "GS RVT 2611", "anreise": an, "internat": True, "gruppe": "RVT", "tn_id": tn,
            "abreise": ab, "liste": "manuell", "erinnerung_tage": None, "erinnerung_kanal": "", "erinnerung_id": "",
            "erledigt": False, "geschlecht": "", "tier": False, "bemerkung": "", "abreise_quelle": "", **x}


START = {"importe/anreisen_goslar.json": {"personen": [_person("Muster, Max", "900001", "2026-11-16"),
                                                        _person("Probe, Paula", "900002", "2026-11-16")],
                                           "listen": {"a": {"datei": "x"}}},
         "zimmer_zuweisungen.json": {"zuweisungen": [{"person": "id:900001", "name": "Muster, Max", "zimmer": "GS-2-101",
                                                      "von": "2026-11-16", "bis": "2027-02-15"}]}}


def _export(ab: Ablage, programm: str) -> dict:
    st = ak.stand(ab.lesen)
    inhalt = ak.datei_bauen(ak.aenderungen(st, ak.basis_lesen(ab.lesen)), programm, "Test",
                            datetime(2026, 11, 13, 10, 0))
    ak.basis_schreiben(ab.schreiben, ak.pruefwerte(st))
    return json.loads(json.dumps(inhalt))               # wie über eine Datei


def _import(ab: Ablage, inhalt: dict, konflikte_uebernehmen: bool = False):
    punkte = ak.abgleichen(ak.datei_pruefen(inhalt), ak.stand(ab.lesen))
    for p in punkte:
        if p.status == "konflikt":
            p.uebernehmen = konflikte_uebernehmen
    ak.anwenden(punkte, ab.lesen, ab.schreiben)
    ak.basis_schreiben(ab.schreiben, ak.basis_nach_import(ak.basis_lesen(ab.lesen), punkte))
    return punkte


def _gleich(a: Ablage, b: Ablage) -> bool:
    return ak.pruefwerte(ak.stand(a.lesen)) == ak.pruefwerte(ak.stand(b.lesen))


def test_erster_austausch_ganzer_stand_dann_nur_aenderungen():
    neu, alt = Ablage(START), Ablage()
    f = _export(neu, "neu")
    assert f["art"] == "stand" and len(f["aenderungen"]) == 3
    _import(alt, f)
    assert _gleich(neu, alt)
    # Kollegin (altes Programm) setzt eine Abreise und plant ein Zimmer
    d = alt.lesen("importe/anreisen_goslar.json", {})
    d["personen"][1]["abreise"] = "2027-01-31"
    alt.schreiben("importe/anreisen_goslar.json", d)
    z = alt.lesen("zimmer_zuweisungen.json", {})
    z["zuweisungen"].append({"person": "id:900002", "name": "Probe, Paula", "zimmer": "GS-2-103", "von": "2026-11-16",
                             "bis": "2027-01-31"})
    alt.schreiben("zimmer_zuweisungen.json", z)
    f2 = _export(alt, "alt")                             # nur, was die Kollegin seit dem Einlesen geändert hat
    assert sorted(x["art"] for x in f2["aenderungen"]) == ["geaendert", "neu"]
    punkte = _import(neu, f2)
    assert all(p.status == "uebernehmen" for p in punkte)
    assert _gleich(neu, alt)


def test_oertliche_felder_bleiben_und_listen_bleiben():
    neu = Ablage(START)
    alt = Ablage(START)
    d = alt.lesen("importe/anreisen_goslar.json", {})
    d["personen"][0]["erinnerung_id"] = "OUTLOOK-ALT"
    alt.schreiben("importe/anreisen_goslar.json", d)
    ak.basis_schreiben(alt.schreiben, ak.pruefwerte(ak.stand(alt.lesen)))
    ak.basis_schreiben(neu.schreiben, ak.pruefwerte(ak.stand(neu.lesen)))
    d = neu.lesen("importe/anreisen_goslar.json", {})
    d["personen"][0]["abreise"] = "2027-03-01"
    d["personen"][0]["erinnerung_id"] = "OUTLOOK-NEU"
    neu.schreiben("importe/anreisen_goslar.json", d)
    _import(alt, _export(neu, "neu"))
    p = alt.lesen("importe/anreisen_goslar.json", {})
    assert p["personen"][0]["abreise"] == "2027-03-01" and p["personen"][0]["erinnerung_id"] == "OUTLOOK-ALT"
    assert p["listen"] == {"a": {"datei": "x"}}


def test_konflikt_wird_nicht_still_ueberschrieben_und_eigener_stand_geht_zurueck():
    neu, alt = Ablage(START), Ablage(START)
    for ab in (neu, alt):
        ak.basis_schreiben(ab.schreiben, ak.pruefwerte(ak.stand(ab.lesen)))
    for ab, zimmer in ((neu, "GS-2-105"), (alt, "GS-2-107")):
        z = ab.lesen("zimmer_zuweisungen.json", {})
        z["zuweisungen"][0]["zimmer"] = zimmer
        ab.schreiben("zimmer_zuweisungen.json", z)
    punkte = _import(alt, _export(neu, "neu"))           # Kollegin behält ihr Zimmer
    assert [p.status for p in punkte] == ["konflikt"]
    assert alt.lesen("zimmer_zuweisungen.json", {})["zuweisungen"][0]["zimmer"] == "GS-2-107"
    _import(neu, _export(alt, "alt"))                    # ihr Stand geht zurück und gilt dann auf beiden Seiten
    assert _gleich(neu, alt)


def test_entfernen_wird_uebertragen():
    neu, alt = Ablage(START), Ablage(START)
    for ab in (neu, alt):
        ak.basis_schreiben(ab.schreiben, ak.pruefwerte(ak.stand(ab.lesen)))
    neu.schreiben("zimmer_zuweisungen.json", {"zuweisungen": []})
    _import(alt, _export(neu, "neu"))
    assert alt.lesen("zimmer_zuweisungen.json", {}) == {"zuweisungen": []}


def test_pruefwerte_schuetzen_vor_veraenderten_dateien():
    f = _export(Ablage(START), "neu")
    kaputt = copy.deepcopy(f)
    kaputt["aenderungen"][0]["eintrag"]["abreise"] = "2030-01-01"
    with pytest.raises(ak.AustauschFehler, match="Prüfwert"):
        ak.datei_pruefen(kaputt)
    with pytest.raises(ak.AustauschFehler, match="keine INNternat"):
        ak.datei_pruefen({"format": "x"})
    assert len(ak.datei_pruefen(f)) == 3


def test_beschreibung_lesbar():
    t = ak.beschreibung("zuweisungen", START["zimmer_zuweisungen.json"]["zuweisungen"][0])
    assert t == "Muster, Max → Zimmer 2-101 · 16.11.2026 – 15.02.2027"
    assert "Abreise offen" in ak.beschreibung("personen", _person("Muster, Max", "900001", "2026-11-16"))


# ---- Werkzeug für das alte Programm (eigener Datenordner, Sicherung vorher) -----------------------------------------
def _ordner(tmp_path, name: str, dateien: dict):
    from belegung import speicher

    o = tmp_path / name
    for datei, inhalt in dateien.items():
        speicher.schreiben(datei, inhalt, o)
    return o


def test_werkzeug_alt_und_dienst_neu_tauschen_ueber_echte_dateien(tmp_path, monkeypatch):
    from austausch import werkzeug as wz
    from belegung import speicher as sp

    alt = _ordner(tmp_path, "alt", START)
    neu = _ordner(tmp_path, "neu", {})
    roh, name, n, st = wz.export(alt)
    assert n == 3 and name.startswith("INNternat-Austausch_alt_") and name.endswith(".json")
    wz.export_gemerkt(alt, st)
    # neues Programm: Dienst schreibt über speicher in den (umgelenkten) Datenordner
    monkeypatch.setattr(sp, "datenordner", lambda: neu)
    from modern import austausch_dienst as ad

    punkte, meta = ad.lesen(roh)
    assert meta["programm"] == "alt" and all(p.status == "uebernehmen" for p in punkte)
    monkeypatch.setattr("modern.kern._schritt", lambda titel, aktion, dateien=None: aktion())
    assert "3 neu" in ad.uebernehmen(punkte)
    # das neue Programm ändert eine Abreise und exportiert
    from belegung import speicher

    d = speicher.lesen("importe/anreisen_goslar.json", {}, neu)
    d["personen"][0]["abreise"] = "2027-04-30"
    speicher.schreiben("importe/anreisen_goslar.json", d, neu)
    roh2, _n, n2, st2 = ad.export()
    assert n2 == 1
    ad.export_gemerkt(st2)
    punkte2, _m = wz.pruefen(alt, roh2)
    zahl, sicherung = wz.uebernehmen(alt, punkte2, datetime(2026, 11, 13, 12, 0))
    assert zahl["geaendert"] == 1 and (sicherung / "importe/anreisen_goslar.json").exists()
    assert speicher.lesen("importe/anreisen_goslar.json", {}, alt)["personen"][0]["abreise"] == "2027-04-30"
    assert speicher.lesen("importe/anreisen_goslar.json", {}, sicherung)["personen"][0]["abreise"] is None


def test_werkzeug_fenster_oeffnet(tmp_path, monkeypatch):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from austausch import austausch_alt as fenster

    wz = fenster.wz
    alt = _ordner(tmp_path, "alt", START)
    monkeypatch.setattr(wz, "datenordner", lambda: alt)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    f = fenster.Fenster()
    assert f.ordner == alt
    roh, _n, _z, _st = wz.export(alt)
    punkte, meta = wz.pruefen(_ordner(tmp_path, "leer", {}), roh)
    v = fenster.Vorschau(punkte, meta)
    assert v.baum.topLevelItemCount() == 2               # Anreisen/Abreisen und Zimmerplanung
    v.close()
    f.close()
    assert app is not None


def test_blick_je_monat():
    from modern import blick_kern as bk

    namen = [f"M{i}" for i in range(26)]
    werte = [1.0] * 24 + [2.0, 3.0]
    b = bk.wellen(namen, werte, [i < 24 for i in range(26)], date(2026, 11, 13), naechstes_jahr=20, je_monat=True)
    texte = " ".join(s.text for s in b.saetze)
    assert "Letzter Monat M23" in texte and "Nächster Monat M24" in texte and "(12)" in texte
