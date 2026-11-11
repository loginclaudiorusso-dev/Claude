"""0.94 – Teilnehmer-Prognose: keine Kursfamilie verschwindet (KBM), Treffsicherheit je Maßnahme, Lücke statt 0,
„Heute“ = Startwert, Plausibilität, Leitungsansicht in Worten. Nur erfundene Daten."""

import random
from datetime import date, timedelta

from modern import bestand_kern as bk
from modern import bestand_prognose as bp
from modern import massnahmen_kern as mk

L = date(2026, 10, 25)
T = bk.tabelle_bereinigen(bk.ZUORDNUNG_STANDARD)


def _daten(seed=5):
    rnd = random.Random(seed)
    auf, p = [], 0
    for _ in range(220):                    # Assessments seit 2023, 60 % weiter in CNC
        p += 1
        s = date(2023, 1, 1) + timedelta(days=rnd.randint(0, (L - date(2023, 1, 1)).days - 10))
        auf.append(bk.Aufenthalt(p, f"GS ASS PS {s:%y%m%d}", s, min(L, s + timedelta(days=41)), 42, 12, 0))
        if rnd.random() < .6 and s + timedelta(days=60) < L:
            h = s + timedelta(days=60)
            auf.append(bk.Aufenthalt(p, f"GS CNC {h:%y%m}", h, min(L, h + timedelta(days=729)), 730, 0, 0))
    for i in range(4):                      # neue kleine Maßnahme ohne Historie: erst seit Oktober
        auf.append(bk.Aufenthalt(900 + i, "GS NEU 261012", date(2026, 10, 12), L, 14, 0, 0))
    for i in range(5):                      # KBM (jetzt zugeordnet) und eine unbekannte Familie
        auf.append(bk.Aufenthalt(950 + i, "GS KBM 2604", date(2026, 4, 1), L, 200, 0, 0))
    auf.append(bk.Aufenthalt(990, "GS XYZ 2605", date(2026, 5, 4), L, 170, 0, 0))
    return auf


def _alles():
    auf = _daten()
    return auf, bp.alles(auf, {"bis": L.isoformat()}, T, {}, bp.szenarien_lesen({}), L)


def test_kbm_zugeordnet_und_keine_familie_verschwindet():
    assert bk.zuordnen("GS KBM 2604", T)["art"] == "Hauptmaßnahme KBM"
    auf, erg = _alles()
    arten = set(erg["modell"].arten)
    assert "Hauptmaßnahme KBM" in arten
    ohne = dict(erg["ohne_zuordnung"])
    assert ohne == {"NEU": 4, "XYZ": 1} and {"NEU", "XYZ"} <= arten          # zählen unter „Sonstige“ mit
    # jede Familie aus den Neuanmeldungen ist zugeordnet oder steht in ohne_zuordnung
    for x in auf:
        assert bk.zuordnen(x.kurs, T) is not None or bp.kursfamilie(x.kurs) in ohne, mk.familie(x.kurs)


def test_gespeicherte_tabelle_bekommt_kbm():
    t = bk.tabelle({"zuordnung_arten": [{"muster": "CNC", "art": "CNC", "gruppe": "Hauptmaßnahme", "soll_tage": 730}]})
    assert [e["muster"] for e in t] == ["CNC", "KBM"]


def test_luecke_statt_null_und_heute_gleich_startwert():
    _auf, erg = _alles()
    ist = bp.ist_verlauf(erg["faelle"], L, "NEU")
    assert [n for _d, n in ist[:-1]] == [0] * (len(ist) - 1) and ist[-1][1] == 4   # Daten da, niemand → echte 0
    leer = bp.ist_verlauf([f for f in erg["faelle"] if f.art == "NEU"], L, "NEU")
    assert all(n is None for _d, n in leer[:-1]) and leer[-1][1] == 4      # vor dem Datenbeginn → Lücke
    e = erg["szenarien"]["basis"]
    for art in ("NEU", "Assessment", "Hauptmaßnahme CNC", None):
        assert bp.bestand_heute(erg["faelle"], L, art) == round(float(e.median[e.zeile(art), 0])), art
    assert e.p025 is not None and (e.p025 <= e.p10).all() and (e.p975 >= e.p90).all()


def test_treffsicherheit_je_massnahme_und_regel():
    _auf, erg = _alles()
    je = erg["rueckblick_je"]
    alle6 = next(r for r in je["Alle"] if r.horizont == 6)
    ass6 = next(r for r in je["Assessment"] if r.horizont == 6)
    assert alle6.mae is not None and ass6.mae is not None and ass6.mae != alle6.mae
    assert not bp.treffsicherheit(je["NEU"]).verlaesslich                 # neue Maßnahme: kein Vergleich
    r = bp.Rueckblick(6, 12, 9.0, None, None, None, bestand_mittel=8.0)   # Fehler > halber Bestand
    assert bp.treffsicherheit([r]).satz == "zu wenige Fälle für eine verlässliche Aussage"
    gut = bp.treffsicherheit([bp.Rueckblick(6, 12, 3.0, None, None, None, bestand_mittel=40.0)])
    assert gut.verlaesslich and gut.satz.startswith("im Schnitt 3 daneben, bei durchschnittlich 40 Teilnehmenden")


def test_plausibel_und_leitungssicht():
    ist = [(date(2026, m, 15), 20) for m in range(1, 11)]
    assert "deutlich unter" in bp.plausibel(ist, [5.0] * 12)
    assert bp.plausibel(ist, [18.0] * 12) is None
    assert bp.plausibel([(date(2026, 1, 15), None)] * 10, [1.0] * 12) is None       # ohne Historie kein Urteil
    _auf, erg = _alles()
    s = bp.leitungssicht(erg, "NEU")
    assert s.titel.startswith("NEU: heute 4 Teilnehmende, in 6 Monaten voraussichtlich")
    assert [k.frage for k in s.kacheln] == ["Werden es mehr oder weniger?", "Wie sicher ist das?",
                                            "Wie gut lag die Prognose bisher?"]
    assert s.kacheln[2].antwort == "zu wenige Fälle" and s.klein
    assert any("keiner Maßnahme zugeordnet" in h for h in s.hinweise)
    a = bp.leitungssicht(erg, "Assessment")
    assert [w[0] for w in a.weitere] == ["Eintritte der letzten 90 Tage", "Übergang in die nächste Stufe"]
    c = bp.leitungssicht(erg, "Hauptmaßnahme CNC")
    assert [w[0] for w in c.weitere] == ["Erwartete Abgänge", "Zugänge aus Vorstufen"] and not c.klein


def test_diagramm_heute_und_baender():
    from modern import bestand_prognose_ui as ui_

    _auf, erg = _alles()
    opt, _txt = ui_._verlauf_option(erg, bp.szenarien_lesen({}), "Hauptmaßnahme CNC")
    kat = opt["xAxis"]["data"]
    assert "Heute" in kat and len(kat) == kat.index("Heute") + 13                # 12 Monate nach „Heute“
    namen = [r["name"] for r in opt["series"]]
    assert {"so war es", "erwartet", "sehr wahrscheinlich (8 von 10)", "fast sicher (19 von 20)"} <= set(namen)
    assert opt["yAxis"]["min"] == 0 and opt["yAxis"]["minInterval"] == 1
    assert all(not r.get("smooth") for r in opt["series"])
    klein, _ = ui_._verlauf_option(erg, bp.szenarien_lesen({}), "NEU")
    assert any(r["type"] == "custom" for r in klein["series"]) and any(r["type"] == "bar" for r in klein["series"])
