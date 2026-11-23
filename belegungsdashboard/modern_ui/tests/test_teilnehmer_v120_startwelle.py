"""1.20 – Teilnehmer-Prognose: Zugänge in Hauptmaßnahmen kommen zum Starttermin (Januar/Juli), nicht verteilt übers Jahr;
Zählwerte je Monat bleiben Säulen (kein Umstellen, kein Glätten)."""

import inspect
from datetime import date, timedelta


from modern import bestand_kern as bk
from modern import bestand_prognose as bp

L = date(2026, 11, 16)
T = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)
VW, ASS = "Hauptmaßnahme VW", "Assessment"


def _faelle():
    fs, p = [], 0
    for j in (2024, 2025, 2026):
        for m, tag in ((1, 5), (7, 1)):
            for _ in range(8):                                        # Hauptmaßnahme: nur Januar- und Juli-Start
                ein = date(j, m, tag)
                if ein > L:
                    continue
                fs.append(bp.Fall(p, "GS VW", VW, "Hauptmaßnahme", ein, min(ein + timedelta(days=700), L),
                                  ein + timedelta(days=700) > L, 700))
                p += 1
        for m in range(1, 13):                                        # Assessment jeden Monat, die Hälfte wechselt
            for k in range(4):
                ein = date(j, m, 10)
                if ein > L:
                    continue
                fs.append(bp.Fall(p, "GS ASS", ASS, ASS, ein, min(ein + timedelta(days=20), L), ein + timedelta(days=20) > L, 21))
                if k < 2:                                             # Wechsler starten zur nächsten Welle
                    nach = bp.naechster_start(ein + timedelta(days=30), {1: 5, 7: 1})
                    if nach <= L:
                        fs.append(bp.Fall(p, "GS VW", VW, "Hauptmaßnahme", nach, min(nach + timedelta(days=700), L),
                                          nach + timedelta(days=700) > L, 700))
                p += 1
    return fs


def test_startmonate_erkannt():
    sm = bp.startmonate(_faelle(), L)
    assert sm[VW] == {1: 5, 7: 1}
    assert ASS not in sm                                              # Assessment beginnt jeden Monat: flexibel
    assert bp.naechster_start(date(2027, 3, 20), {1: 5, 7: 1}) == date(2027, 7, 1)
    assert bp.naechster_start(date(2027, 9, 2), {1: 5, 7: 1}) == date(2028, 1, 5)
    assert bp.naechster_start(date(2027, 7, 20), {1: 5, 7: 1}) == date(2027, 7, 20)      # im Startmonat: bleibt


def test_zugaenge_kommen_zum_starttermin():
    md = bp.modell(_faelle(), L, T)
    assert md.startmonate.get(VW) == {1: 5, 7: 1}
    e = bp.simulieren(md, 0, 300)
    f = bp.fluss(e, VW, "zu")
    je = {d.month: float(v) for d, v in zip(e.monate[1:13], f.median[1:13])}
    ausserhalb = sum(v for m, v in je.items() if m not in (1, 7))
    assert je[1] + je[7] >= 0.85 * (je[1] + je[7] + ausserhalb)      # fast alles in Januar und Juli (Rest: Nachrücker)
    md.startmonate = {}                                               # ohne Rhythmus (so war es bis 1.19): verteilt
    alt = bp.fluss(bp.simulieren(md, 0, 300), VW, "zu")
    assert sum(float(v) for d, v in zip(e.monate[1:13], alt.median[1:13]) if d.month not in (1, 7)) > 2


def test_zaehlwerte_bleiben_saeulen():
    from modern import bestand_prognose_ui

    q = inspect.getsource(bestand_prognose_ui._fluss_ansicht)
    assert 'r_["m_fest"] = True' in q


# ---- 1.20b: Cockpit-Diagramm „Freie Betten“ + Klartext-Tooltip + Einstellungen ----

from modern import cockpit_kern as ck  # noqa: E402
from test_steuerung_v116_cockpit import _bedarf, _karte  # noqa: E402


def _reihe(o, name):
    return next(s for s in o["series"] if s["name"] == name)["data"]


def test_freie_betten_saeulen_addieren_sich():
    bd = _bedarf()
    bw = ck.bewerten([_karte("a", 10, 1, 0, 3)], {"a": 3}, bd, None, 0, [])
    o = ck.diagramm_frei(bd, bw)
    sicher, extra = _reihe(o, "frei auch im ungünstigen Fall"), _reihe(o, "frei, wenn es wie erwartet kommt")
    for i, e in enumerate(bd.erwartet):
        if e is None:
            continue
        frei_e = bd.decke - bw.baustellen[i] - e
        if frei_e >= 0:
            assert abs((sicher[i] or 0) + (extra[i] or 0) - frei_e) < 0.11
    assert all(s.get("m_fest") for s in o["series"])                       # Diagrammtyp „Linie“ macht keine Kurve daraus
    assert o["tooltip"]["trigger"] == "axis" and ":formatter" in o["tooltip"]


def test_fehlende_betten_rot_unter_null():
    bd = _bedarf()
    w = ck.wenn_dann(bd, 2, 130, 0.5)                                       # mehr Bedarf als Betten
    bw = ck.bewerten([], {}, w.bedarf, None, 0, [])
    o = ck.diagramm_frei(w.bedarf, bw, wd=w)
    assert (_reihe(o, "fehlen")[2] or 0) < 0
    assert "ohne Wenn-dann" in o["legend"]["data"]
    ohne = ck.diagramm_frei(w.bedarf, bw, band=False)
    assert "frei (erwartet)" in ohne["legend"]["data"] and "frei, wenn es wie erwartet kommt" not in ohne["legend"]["data"]


def test_monats_texte_klartext():
    bd = _bedarf()
    bw = ck.bewerten([_karte("a", 10, 1, 0, 3)], {"a": 3}, bd, None, 0, [])
    t = ck.monats_texte(bd, bw)
    assert len(t) == len(bd.monate)
    i = next(k for k, e in enumerate(bd.erwartet) if e is not None and not bd.ist[k])
    assert "erwartet belegt" in t[i] and "8 von 10" in t[i] and "verfügbar" in t[i] and " – " not in t[i].split("<br>")[-1][:2]


def test_bedarf_ohne_band_und_ab_null():
    bd = _bedarf()
    bw = ck.bewerten([], {}, bd, None, 0, [])
    namen = {s["name"] for s in ck.diagramm(bd, bw, band=False)["series"]}
    assert "ungünstiger Fall (8 von 10)" not in namen
    assert ck.diagramm(bd, bw, null=True)["yAxis"]["min"] == 0


def test_cockpit_ersetzt_altes_und_hat_einstellungen():
    from modern import cockpit_ui, seite_steuerung as st

    assert st.ANSICHTEN["cockpit"] == "Überblick" and "cockpit_neu" not in st.ANSICHTEN     # 1.39: Name
    assert st.ALT["cockpit_neu"] == "cockpit" and not hasattr(st, "_cockpit")
    q = inspect.getsource(cockpit_ui)
    for s in ('"Freie Betten"', '"Bedarf & Decke"', '"Unsicherheit zeigen"', '"Achse ab 0"', "SO_LESEN", "ck_ansicht"):
        assert s in q
