"""1.75: Rechte je Benutzer, Gruppe blockieren (Kontingent), Kurs-Abwesenheit, Feiertage, Ampel, Startansicht,
Berechnung in der Prognose, neue Symbole (erfundene Daten)."""

import re
from datetime import date, timedelta
from types import SimpleNamespace as NS

import pytest

import modern.kern  # noqa: F401
from belegung import konfig
from belegung import zimmerplan as zp
from belegung.gebaeudeplan import Belegung

from modern import benutzer_kern as bk
from modern import feiertage_kern as fk
from modern import haus_kern as hk
from modern import kontingent_kern as kk
from modern import menueband as mb
from modern import piktogramme as pk
from modern import rechte_kern as rk
from modern import symbole as sy

H = date(2026, 11, 27)


# ---- Rechte -----------------------------------------------------------------------------------------------------

def _konto(rolle="mitarbeiter", rechte=None):
    return bk.Konto("kim", "Kim Probehaus", rolle, ["GS"], rechte=rechte)


def test_rechte_vorlagen_und_konten():
    assert rk.von_konto(_konto("admin", [])) == set(rk.KEYS)                  # Administrator darf immer alles
    assert rk.von_konto(_konto()) == set(rk.vorlage("mitarbeiter"))           # Konten bis 1.74: wie bisher
    assert rk.von_konto(_konto(rechte=rk.vorlage("haustechnik"))) == {"reinigung", "maengel", "inventar"}
    assert rk.passende_vorlage(rk.vorlage("empfang")) == "empfang"
    assert rk.passende_vorlage(["reinigung"]) == ""
    lesen = _konto(rechte=[])
    assert not rk.darf("mieter", lesen) and rk.darf(None, lesen)
    with pytest.raises(ValueError, match="Mietverträge"):
        rk.pruefen("mieter", lesen)
    assert not rk.seite_erlaubt("auswertung", konto=lesen) and rk.seite_erlaubt("zimmer", konto=lesen)
    assert rk.seite_erlaubt("auswertung", konto=_konto(rechte=["auswertung"]))
    # gespeichert wird „wie Mitarbeiter/in“ als None – neue Rechte gelten dann künftig mit
    assert bk._rechte(rk.vorlage("mitarbeiter")) is None and bk._rechte(["mieter", "xyz"]) == ["mieter"]


def test_recht_fuer_aktionen():
    from modern import mieter_checkliste, seite_einstellungen, seiten_kern

    assert rk.recht_fuer(modern.kern.zuweisen) == "zuteilen"
    assert rk.recht_fuer(modern.kern.reinigung_einzeln) == "reinigung"
    assert rk.recht_fuer(seiten_kern.reinigung_setzen) == "reinigung"
    assert rk.recht_fuer(mieter_checkliste.setzen) == "mieter"
    assert rk.recht_fuer(kk.anlegen) == "blocken"
    assert rk.recht_fuer(hk.abw_sammel_anlegen) == "haus"
    assert rk.recht_fuer(seite_einstellungen.zahl_setzen) == "einstellungen"
    assert rk.recht_fuer(fk.schliesszeit_anlegen) == "einstellungen"

    def eigene():
        pass
    eigene.recht = "planung"
    assert rk.recht_fuer(eigene) == "planung"


def test_ohne_anmeldung_alles_erlaubt(monkeypatch):
    monkeypatch.setattr(bk, "aktuell", lambda: None)
    assert all(rk.darf(k) for k in rk.KEYS)
    monkeypatch.setattr(bk, "aktuell", lambda: _konto(rechte=["reinigung"]))
    assert rk.darf("reinigung") and not rk.darf("zuteilen")


# ---- Gruppe blockieren (Kontingent) -----------------------------------------------------------------------------

def _lage(*zimmer, belegungen=None):
    zs = {z.id: z for z in zimmer}
    return zp.Lage(zs, {z.id: list((belegungen or {}).get(z.id, [])) for z in zimmer})


def test_kontingent_blockiert_freie_betten():
    z1 = zp.Zimmer("GS-2-101", "2", "1", "101", betten=2)
    z2 = zp.Zimmer("GS-2-102", "2", "1", "102", betten=1)
    z3 = zp.Zimmer("GS-2-103", "2", "1", "103", betten=1)
    echt = Belegung("GS-2-101", date(2027, 3, 1), date(2027, 3, 20), "belegt", "Beispiel, Erika", "GS IK", "", "p1")
    sperre = Belegung("GS-2-103", date(2027, 1, 1), date(2027, 12, 31), "gesperrt", grund="Renovierung")
    lage = _lage(z1, z2, z3, belegungen={"GS-2-101": [echt], "GS-2-103": [sperre]})
    k = kk.Kontingent("k1", "Kurs Elektro", date(2027, 3, 3), date(2027, 3, 28), ["GS-2-101", "GS-2-102", "GS-2-103"])
    assert kk.anwenden(lage, [k]) == 2                    # 101: ein Bett schon namentlich, 102: ganz, 103: gesperrt
    b101 = [b for b in lage.belegungen["GS-2-101"] if kk.ist_kontingent(b)]
    assert len(b101) == 1 and b101[0].name == "Kontingent: Kurs Elektro"
    assert lage.freie_betten("GS-2-102", date(2027, 3, 10), date(2027, 3, 12)) == 0
    assert lage.freie_betten("GS-2-102", date(2027, 4, 2), date(2027, 4, 5)) == 1     # nach dem Kontingent frei


def test_kontingent_speichern(monkeypatch, tmp_path):
    from belegung import speicher

    daten = {}
    monkeypatch.setattr(speicher, "lesen", lambda d, s=None: daten.get(d, s))
    monkeypatch.setattr(speicher, "schreiben", lambda d, w: daten.__setitem__(d, w))
    monkeypatch.setattr("modern.kern._schritt", lambda t, fn, dateien: fn())
    with pytest.raises(ValueError):
        kk.anlegen("", date(2027, 3, 1), date(2027, 3, 5), ["GS-2-101"])
    with pytest.raises(ValueError):
        kk.anlegen("Kurs", date(2027, 3, 5), date(2027, 3, 1), ["GS-2-101"])
    kk.anlegen("Kurs Elektro", date(2027, 3, 1), date(2027, 3, 28), ["GS-2-101", "GS-2-102"])
    k = kk.laden()[0]
    assert k.zimmer == ["GS-2-101", "GS-2-102"]
    kk.zimmer_freigeben(k.id, "GS-2-101")
    assert kk.laden()[0].zimmer == ["GS-2-102"]
    kk.zimmer_freigeben(k.id, "GS-2-102")                   # letztes Zimmer → Kontingent weg
    assert kk.laden() == []


# ---- Kurs-Abwesenheit ---------------------------------------------------------------------------------------------

def test_kurse_und_sammel_abwesenheit(monkeypatch):
    bs = {"GS-2-101": [Belegung("GS-2-101", H - timedelta(days=10), H + timedelta(days=60), "belegt", "Beispiel, Erika",
                                "GS IK 2506", "", "p1"),
                       Belegung("GS-2-101", H, H + timedelta(days=20), "belegt", "Kontingent: Kurs", "Kontingent", "",
                                "kontingent:k1:1")],
          "GS-2-102": [Belegung("GS-2-102", H - timedelta(days=3), H + timedelta(days=30), "belegt", "Probehaus, Kim",
                                "GS IK 2506", "", "p2"),
                       Belegung("GS-2-102", H, H + timedelta(days=90), "geplant", "Musterhoff, Alex", "Mieter", "",
                                "mv:12")]}
    kurse = hk.kurse(NS(belegungen=bs), H, H + timedelta(days=6))
    assert kurse == {"GS IK 2506": [("Beispiel, Erika", "GS-2-101"), ("Probehaus, Kim", "GS-2-102")]}
    alle = [hk.Abwesenheit("x", "Erika Beispiel", "GS-2-101", H.isoformat(), (H + timedelta(days=2)).isoformat())]
    gespeichert = {}
    monkeypatch.setattr(hk, "abw_laden", lambda: list(alle))
    monkeypatch.setattr(hk, "_abw_speichern", lambda l: gespeichert.__setitem__("l", l))
    monkeypatch.setattr("modern.kern._schritt", lambda t, fn, dateien: fn())
    text = hk.abw_sammel_anlegen(kurse["GS IK 2506"], H, H + timedelta(days=6), "ferien", "", "GS IK 2506")
    assert "1 Abwesenheit" in text and "1 waren schon" in text
    neu = gespeichert["l"][-1]
    assert neu.name == "Probehaus, Kim" and neu.grund == "ferien" and "Kurs GS IK 2506" in neu.notiz
    html = hk.kursliste_html("GS IK 2506", [("Probehaus, Kim", "2-102")], "Kursliste", "x")
    assert "Probehaus, Kim" in html and "Unterschrift" in html


# ---- Feiertage ---------------------------------------------------------------------------------------------------

def test_feiertage_berechnet():
    assert fk.ostersonntag(2026) == date(2026, 4, 5) and fk.ostersonntag(2027) == date(2027, 3, 28)
    ni = fk.feiertage(2026, "NI")
    assert ni[date(2026, 4, 3)] == "Karfreitag" and ni[date(2026, 5, 25)] == "Pfingstmontag"
    assert ni[date(2026, 10, 31)] == "Reformationstag" and date(2026, 6, 4) not in ni
    assert fk.feiertage(2026, "BY")[date(2026, 6, 4)] == "Fronleichnam"
    assert fk.feiertage(2026, "SN")[date(2026, 11, 18)] == "Buß- und Bettag"
    assert len(ni) == 10


def test_schliesszeit_und_termine():
    sz = [fk.Schliesszeit("s1", "Weihnachtsschließung", "2026-12-23", "2026-12-31")]
    t = fk.tage(date(2026, 12, 20), date(2026, 12, 31), "NI", sz)
    assert t[date(2026, 12, 25)] == "1. Weihnachtstag · Schließzeit: Weihnachtsschließung"
    assert t[date(2026, 12, 23)] == "Schließzeit: Weihnachtsschließung" and date(2026, 12, 22) not in t
    treffer = fk.termine_im_zeitraum([(date(2026, 12, 24), "Anreise", "Kim"), (date(2026, 12, 21), "Abreise", "Alex")],
                                     date(2026, 12, 15), 14, "NI", sz)
    assert treffer == [(date(2026, 12, 24), "Schließzeit: Weihnachtsschließung", [("Anreise", "Kim")])]


# ---- Ampel, Startansicht, Berechnung, Symbole --------------------------------------------------------------------

def test_ampel_einstellbar():
    from modern.seite_einstellungen import ZAHLEN, ampel_anwenden

    alt = konfig.AMPEL_GELB, konfig.AMPEL_ROT
    try:
        assert ampel_anwenden({"ampel_gelb_prozent": 75, "ampel_rot_prozent": 90}) == (0.75, 0.90)
        assert konfig.ampel_stufe(0.8)[0] == "knapp" and konfig.ampel_stufe(0.92)[0] == "kritisch"
        assert ampel_anwenden({"ampel_gelb_prozent": 90, "ampel_rot_prozent": 80}) == (0.70, 0.85)   # unsinnig → Standard
        assert ZAHLEN["ampel_gelb_prozent"][1] == 70 and ZAHLEN["ampel_rot_prozent"][1] == 85
    finally:
        konfig.AMPEL_GELB, konfig.AMPEL_ROT = alt


def test_startansicht():
    assert "heute" in bk.STARTSEITEN and "auswertung/prognose" in bk.STARTSEITEN
    with pytest.raises(ValueError):
        bk.startseite_setzen("gibt_es_nicht")


def test_berechnung_im_menueband():
    prog = next(r for r in mb.reiter({}) if r.key == "prognose")
    ziele = [p.ziel[1] for g in prog.gruppen for p in g.punkte if p.ziel]
    assert "aw:aw_chart=rechnung" in ziele
    assert mb.symbol(next(p for g in prog.gruppen for p in g.punkte if p.ziel == mb.A("aw:aw_chart=rechnung")))[0] \
        == "p:a_berechnung"


def test_neue_symbole_in_beiden_fassungen():
    ids = set()
    for name in ("a_berechnung", "kontingent", "feiertage", "kurs_abwesend"):
        assert pk.vorhanden(name)
        for stufe in ("g", "k"):
            svg = sy.farbig("p:" + name, stufe)
            assert svg.startswith("<svg") and 'viewBox="0 0 32 32"' in svg
        neu = set(re.findall(r'id="([^"]+)"', sy.farbig("p:" + name)))
        assert neu and not (neu & ids)                     # Verlaufs-IDs eindeutig je Symbol
        ids |= neu
