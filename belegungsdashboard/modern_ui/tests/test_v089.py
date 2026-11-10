"""0.89 – Darstellung der Diagramme wählbar (Karte | Klassisch | Einfach), Leitungsaussage „Einfach“.
Erfundene Zahlen."""

from datetime import date
from pathlib import Path

from modern import blick_kern as bk
from modern import darstellung_kern as dk

MOD = Path(__file__).resolve().parent.parent / "modern"


def _reihe():
    ms = [date(2026, m, 1) for m in range(8, 13)] + [date(2027, m, 1) for m in range(1, 9)]
    ist = [True] * 3 + [False] * 10
    erw = [100, 104, 110, 118, 125, 131, 140, 150, 158, 160, 150, 140, 130]
    hi = [None] * 3 + [w + 12 for w in erw[3:]]
    lo = [None] * 3 + [w - 12 for w in erw[3:]]
    return ms, erw, ist, lo, hi


def test_leitung_eng_ab_monat():
    ms, erw, ist, lo, hi = _reihe()
    lg = bk.leitung("Haus A", ms, erw, ist, date(2026, 11, 10), 180, lo, hi)
    assert lg.titel.startswith("In Haus A wird es ab ") and "von 180 Plätzen möglich" in lg.titel
    namen = [z[0] for z in lg.zahlen]
    assert namen == ["Heute belegt", "Höchstwert erwartet", "Freie Plätze mindestens"]
    assert lg.zahlen[0][1] == "110"
    assert lg.balken[0][0] == "heute" and lg.balken[0][3] is True and len(lg.balken) == 7
    assert lg.unsicher.startswith("In 8 von 10 Fällen liegt die Belegung im ")


def test_leitung_genug_platz_und_ohne_zahlen():
    ms, erw, ist, lo, hi = _reihe()
    lg = bk.leitung("Haus B", ms, erw, ist, date(2026, 11, 10), 400, lo, hi)
    assert lg.titel.startswith("Haus B hat bis ") and lg.titel.endswith("genug freie Plätze.")
    assert bk.leitung("Haus C", [], [], [], date(2026, 11, 10), 100).titel == "Haus C: noch keine Zahlen."


def test_dg_modus_einstellung():
    assert dk.STANDARD["dg_modus"] == "karte" and set(dk.DG_MODI) == {"karte", "klassisch", "einfach"}
    assert dk.bereinigen({"dg_modus": "klassisch"})["dg_modus"] == "klassisch"
    assert dk.bereinigen({"dg_modus": "unsinn"})["dg_modus"] == "karte"


def test_modus_verdrahtet():
    prog = (MOD / "seite_prognose.py").read_text(encoding="utf-8")
    assert 'klassisch = praes or km == "klassisch"' in prog and "def _einfach(" in prog
    assert "diagramm_karte.modus_wahl(a)" in prog
    for datei in ("seite_massnahmen.py", "seite_auswertung.py"):
        t = (MOD / datei).read_text(encoding="utf-8")
        assert "diagramm_karte.modus()" in t or "modus()" in t
    assert '"dg_modus"' in (MOD / "oberflaeche.py").read_text(encoding="utf-8")
    assert ".m-einfach-titel" in (MOD / "diagramm_ui.py").read_text(encoding="utf-8")


def test_leitung_gesamt_und_spitze():
    ms, erw, ist, lo, hi = _reihe()
    lg = bk.leitung("Gesamt", ms, erw, ist, date(2026, 11, 10), 180, lo, hi)
    assert lg.titel.startswith("Insgesamt wird es ab ") and "bis zu 172 von 180" in lg.titel   # Spitze 160 + 12
    assert bk.leitung("Gesamt", ms, erw, ist, date(2026, 11, 10), 400, lo, hi).titel.startswith("Insgesamt gibt es bis ")


# ---- Notfallliste ---------------------------------------------------------------------------------------------------

def test_notfallliste_aus_dem_plan(tmp_path, monkeypatch):
    from datetime import timedelta

    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp
    from modern import notfall_kern as nk

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date.today()
    p = [anreiseliste.Person("Da, Dora", "GS RVL", heute - timedelta(days=5), True, tn_id="1", abreise=heute + timedelta(days=20)),
         anreiseliste.Person("Spaeter, Sam", "GS RVL", heute + timedelta(days=3), True, tn_id="2", abreise=heute + timedelta(days=30))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Da"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Spaeter"], st.lage.zimmer["GS-2-302"])])
    zs = nk.zeilen(zp.laden(), heute)
    namen = [z.name for z in zs]
    assert "Da, Dora" in namen and "Spaeter, Sam" not in namen          # nur wer HEUTE laut Plan da ist
    dora = next(z for z in zs if z.name == "Da, Dora")
    assert dora.zimmer == "2-301" and dora.haus == "2" and dora.art in ("geplant", "im_haus")
    aenderungen.verlauf_leeren()


def test_notfallliste_druck():
    from datetime import datetime

    from modern import notfall_kern as nk

    zs = [nk.NZeile("1", "EG", "1-101", "Muster, Max", "RVL", date(2026, 12, 4), "im_haus", "Rollator"),
          nk.NZeile("1", "EG", "1-102", "belegt, Name unbekannt", "", None, "unbekannt", ""),
          nk.NZeile("2", "1. OG", "2-110", "Probe, Pia", "EMR", date(2026, 11, 30), "geplant", "")]
    n = nk.zaehlen(zs)
    assert n["1"] == {"personen": 2, "geplant": 0, "zimmer": 2} and n["2"]["geplant"] == 1
    h = nk.druck_html(zs, datetime(2026, 11, 10, 14, 5), "Musterstadt")
    assert "Stand 10.11.2026, 14:05 Uhr" in h and "2 Personen im Haus · 1 geplant" in h
    assert "Haus 1 – 2 Personen in 2 Zimmern" in h and "Haus 2 – 0 Personen in 1 Zimmer (+1 geplant)" in h
    assert "Rollator" in h and "geplant – Anreise prüfen" in h and "Nicht enthalten:" in h
    assert "niemand im Haus" in nk.druck_html([], datetime(2026, 11, 10, 8, 0))


def test_notfallliste_erreichbar():
    t = (MOD / "seite_zimmer.py").read_text(encoding="utf-8")
    assert "async def notfall_drucken(a)" in t and '"emergency"' in t
    assert '"notfall"' in (MOD / "befehle_kern.py").read_text(encoding="utf-8")
    assert 'name == "notfall"' in (MOD / "suche_palette.py").read_text(encoding="utf-8")


# ---- Nichtanreise ---------------------------------------------------------------------------------------------------

def test_nichtanreise_gibt_zimmer_frei(tmp_path, monkeypatch):
    from datetime import timedelta

    import pytest

    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp
    from modern import zimmer_kern as zk

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date.today()
    p = [anreiseliste.Person("Fehlt, Finn", "GS RVL", heute, True, tn_id="7", abreise=heute + timedelta(days=20)),
         anreiseliste.Person("Kommt, Kim", "GS RVL", heute + timedelta(days=4), True, tn_id="8", abreise=heute + timedelta(days=30))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Fehlt"], st.lage.zimmer["GS-2-301"])])
    with pytest.raises(ValueError):
        zk.nichtanreise("id:8", heute)                       # Anreise liegt noch in der Zukunft
    text = zk.nichtanreise("id:7", heute)
    assert "nicht angereist" in text and "2-301 ist wieder frei" in text
    st = zp.laden()
    assert st.zugewiesen("id:7") is None and "id:7" not in {x.schluessel for x in st.bedarf}
    fehlt = next(x for x in anreiseliste.laden()[0] if x.tn_id == "7")
    assert fehlt.internat is False and "Nichtanreise" in fehlt.bemerkung
    aenderungen.verlauf_leeren()


def test_offene_reinigung_bleibt_laenger_und_bezug_erledigt():
    from types import SimpleNamespace as NS

    from modern import seiten_kern as sk
    from modern import zimmer_kern as zk

    assert sk.OFFEN_ZURUECK == 60
    st = NS(lage=NS(belegungen={"Z1": [NS(art="belegt", von=date(2026, 10, 5), bis=date(2026, 10, 20))]}))
    assert zk._seither_bezogen(st, "Z1", date(2026, 10, 1), date(2026, 11, 10))       # danach bezogen → erledigt
    assert not zk._seither_bezogen(st, "Z1", date(2026, 10, 25), date(2026, 11, 10))  # seither niemand eingezogen


def test_uebergabeprotokoll():
    from modern import notfall_kern as nk

    h = nk.uebergabe_html("2-301", "1. OG", "Muster, Max", "RVL", date(2026, 11, 2), date(2026, 12, 4), "auszug",
                          [("Lampe", 1), ("Stuhl", 2)], ["Fenster klemmt"], "Musterstadt")
    assert "Übergabeprotokoll – Auszug" in h and "Muster, Max" in h and "02.11.2026 – 04.12.2026" in h
    assert "<td>Stuhl</td><td>2</td>" in h and "Fenster klemmt" in h and "☐ zurück" in h
    assert "Unterschrift Internat" in h
    assert "☐ übergeben" in nk.uebergabe_html("2-301", "", "X, Y", "", None, None, "einzug", [], [])
    assert 'uebergabe_drucken(a, k, p, "einzug")' in (MOD / "seite_zimmer.py").read_text(encoding="utf-8")
