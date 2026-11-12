"""0.87 – Mietverträge mit einheitlicher Schrift; „Auf einen Blick“ (reine Satzvorlagen); Diagramm-Karte und
einheitlicher Diagrammstil. Erfundene Zahlen."""

from datetime import date
from pathlib import Path

from modern import blick_kern as bk

MOD = Path(__file__).resolve().parent.parent / "modern"


def _monate():
    ms = [date(2026, m, 1) for m in range(3, 13)] + [date(2027, m, 1) for m in range(1, 4)]
    #       Mär  Apr  Mai  Jun  Jul  Aug  Sep | Okt  Nov  Dez  Jan  Feb  Mär
    akt = [150, 152, 148, 145, 141, 150, 162, 175, 186, 180, 172, 174, 178]
    ist = [True] * 7 + [False] * 6
    vj = [152, 150, 149, 147, 143, 165, 182, 178, 188, 183, 176, 178, 181]
    hi80 = [None] * 7 + [190, 205, 210, 212, 215, 217]
    return ms, akt, ist, vj, hi80


def test_monatssaetze_wie_im_beispiel():
    ms, akt, ist, vj, hi80 = _monate()
    b = bk.monate(ms, akt, ist, vj, date(2026, 11, 10), kapazitaet=330, abweichung=4, obere80=hi80)
    t = [s.text for s in b.saetze]
    assert t[0] == "Aktuell 162 belegt (Sep 26), 20 weniger als im Vorjahr (182)."
    assert t[1] == "Tiefpunkt war Juli mit 141, der Höchstwert wird im November erwartet (186)."
    assert t[2] == "Nächste 6 Monate: 172 bis 186 erwartet, im Schnitt 3 unter Vorjahr." or "etwa wie im Vorjahr" in t[2]
    assert t[3] == "Kapazität 330: Reserve mindestens 113 Plätze."
    assert 3 <= len(b.saetze) <= 5 and b.stand == "Datenstand 10.11.2026 · ab Okt 26 Prognose."
    assert b.saetze[0].index == 6 and b.saetze[0].wert == 162 and b.saetze[1].index == 8


def test_kleiner_unterschied_heisst_etwa_wie_im_vorjahr():
    assert bk.vergleich(-3, 4) == "etwa wie im Vorjahr"
    assert bk.vergleich(-20, 4) == "20 weniger als im Vorjahr" and bk.vergleich(5, 4) == "5 mehr als im Vorjahr"
    ms, akt, ist, vj, hi80 = _monate()
    b = bk.monate(ms, akt, ist, vj, date(2026, 11, 10), abweichung=4)
    assert "im Schnitt etwa wie im Vorjahr" in b.saetze[2].text            # Ø −3,2 < übliche Abweichung 4
    b2 = bk.monate(ms, akt, ist, vj, date(2026, 11, 10), abweichung=1)
    assert "im Schnitt 3 unter Vorjahr" in b2.saetze[2].text


def test_zahlen_deutsch_und_ueberschreitung():
    assert bk.zahl(1234.4) == "1.234" and bk.zahl(None) == "–"
    ms, akt, ist, vj, _ = _monate()
    b = bk.monate(ms, akt, ist, vj, date(2026, 11, 10), kapazitaet=180)
    assert "möglicherweise überschritten" in b.saetze[-1].text


def test_tage_und_wellen():
    ts = [date(2026, 11, d) for d in range(1, 21)]
    w = [100 + d for d in range(20)]
    ist = [d < 10 for d in range(20)]
    b = bk.tage(ts, w, ist, date(2026, 11, 10), kapazitaet=150)
    assert b.saetze[1].text.startswith("Höchststand 119 am 20.11.2026 (Prognose)") and "Reserve mindestens 31" in b.saetze[-1].text
    assert b.stand == "Datenstand 10.11.2026 · ab 11.11.2026 Prognose." and len(b.saetze) <= 5
    n = ["W 24/25", "S 25", "W 25/26", "S 26", "W 26/27", "S 27"]
    b = bk.wellen(n, [12, 14, 13, 15, 14, 16], [True] * 4 + [False] * 2, date(2026, 11, 10),
                  klein=[None] * 4 + [10, 12], gross=[None] * 4 + [18, 20], treffer=(3, 4), naechstes_jahr=30)
    t = [s.text for s in b.saetze]
    assert t[0] == "Letzte Welle S 26: 15 Neuanmeldungen, etwa wie ein Jahr zuvor (14)."
    assert t[1] == "Nächste Welle W 26/27: 10 bis 18 erwartet (Planwert 14)."
    assert "Rückwärtstest: 3 von 4 vergangenen Wellen lagen" in t[-1] and b.stand.endswith("ab W 26/27 Prognose.")
    eins = bk.wellen(n, [12, 14, 13, 15, 14, 16], [True] * 4 + [False] * 2, date(2026, 11, 10), treffer=(1, 1))
    assert "1 von 1 vergangenen Welle lag" in eins.saetze[-1].text


def test_mietvertrag_einheitliche_schrift():
    from modern import mieter_kern as mk

    h = mk.einheitlich("<html><body style=\"font-family:'Segoe UI'; font-size:10.5pt\"><table><tr><td>1.</td></tr></table></body></html>")
    assert h.startswith("<!doctype html><html><head>") and "font-size: inherit" in h and "<td>1.</td>" in h
    assert mk.einheitlich(h) == h                                   # nicht doppelt
    assert mk.einheitlich("<p>x</p>").startswith("<!doctype html><html><head>")


# ---- Einheitlicher Diagrammstil ------------------------------------------------------------------------------------

T = {"akzent": "#0B6E66", "rot": "#C0392B", "text3": "#8A8F98", "text2": "#5F6670"}


def _opt():
    x = ["Sep 26", "Okt 26", "Nov 26", "Dez 26"]
    return {"title": {"text": "alt"}, "xAxis": {"type": "category", "data": x}, "yAxis": {"type": "value"},
            "legend": {"bottom": 0}, "tooltip": {"trigger": "item"}, "series": [
                {"name": "Vorvorjahr (Ist)", "type": "line", "data": [1, 2, 3, 4], "smooth": True},
                {"name": "Vorjahr (Ist)", "type": "line", "data": [1, 2, 3, 4]},
                {"name": "Aktuell (Ist)", "type": "line", "data": [1, 2, None, None]},
                {"name": "Aktuell (Prognose)", "type": "line", "data": [None, 2, 3, 4]},
                {"name": "_u80", "type": "line", "stack": "b", "data": [None, 1, 2, 3], "tooltip": {"show": False}, "rolle": "band"},
                {"name": "80-%-Spanne", "type": "line", "stack": "b", "data": [None, 2, 2, 2], "areaStyle": {}, "rolle": "band"},
                {"name": "Kapazität", "type": "line", "data": [330] * 4},
                {"name": "Szenario", "type": "line", "data": [None] * 4}]}


def test_einheitlicher_stil_farben_linien_beschriftung():
    from modern import diagramm_stil as ds

    o = ds.einheitlich(_opt(), T, "Okt 26", "Nov 26")
    s = {se.get("name"): se for se in o["series"]}
    assert "title" not in o and all(se.get("smooth") is False for se in o["series"] if se.get("type") == "line")
    ist, prog = s["Aktuell (Ist)"], s["Aktuell (Prognose)"]
    assert ist["lineStyle"]["width"] == ds.LINIE["ist"] and ist["lineStyle"]["type"] == "solid" \
        and ist["lineStyle"]["color"] == T["akzent"]          # 1.02: kräftiger
    assert prog["lineStyle"]["type"] == "dashed" and prog["lineStyle"]["color"] == T["akzent"]
    vj, vvj = ds.vergleichsfarben(T)                          # 1.02: eigene Farbtöne statt Grau, dicker
    assert s["Vorjahr (Ist)"]["lineStyle"] == {"color": vj, "width": ds.LINIE["vorjahr"], "type": "solid"}
    assert s["Vorvorjahr (Ist)"]["lineStyle"]["color"] == vvj and s["Vorvorjahr (Ist)"]["lineStyle"]["width"] == ds.LINIE["vorvorjahr"]
    assert s["Kapazität"]["lineStyle"]["color"] == T["rot"] and "Kapazität 330" in s["Kapazität"]["endLabel"][":formatter"]
    # nur Ist und Prognose beschriftet, mit hideOverlap und dunklem Hintergrund statt Kontur
    assert ist["label"]["show"] and prog["label"]["show"] and not s["Vorjahr (Ist)"]["label"]["show"]
    assert ist["label"]["textBorderWidth"] == 0 and ist["label"]["backgroundColor"] and ist["label"]["fontSize"] == 13
    assert ist["labelLayout"]["hideOverlap"] and ist["label"]["fontWeight"] == "bold"
    # EINE Legende oben, ohne Bänder und leere Reihen; Namen am Linienende
    assert o["legend"]["top"] == 2 and "bottom" not in o["legend"]
    assert o["legend"]["data"] == ["Vorvorjahr (Ist)", "Vorjahr (Ist)", "Aktuell (Ist)", "Aktuell (Prognose)", "Kapazität"]
    assert "Prognose" in prog["endLabel"][":formatter"]
    # Tooltip: Achse, deutsche Zahlen mit einer Nachkommastelle, Differenz zum Vorjahr
    assert o["tooltip"]["trigger"] == "axis" and "de-DE" in o["tooltip"][":formatter"] and "Differenz zum" in o["tooltip"][":formatter"]
    assert o["yAxis"]["axisLabel"]["fontSize"] == 13 and "de-DE" in o["yAxis"]["axisLabel"][":formatter"]
    f = next(se for se in o["series"] if se.get("id") == ds.FOKUS_ID)
    assert f["markLine"]["data"] == [{"xAxis": "Okt 26"}] and f["markLine"]["label"]["formatter"] == "Datenstand"
    assert f["markArea"]["data"] == [[{"xAxis": "Nov 26"}, {"xAxis": "Dez 26"}]]


def test_tageswerte_als_stufen_und_zaehlwerte_als_balken():
    from modern import diagramm_stil as ds

    o = ds.einheitlich({"xAxis": {"type": "category", "data": ["a", "b"]}, "yAxis": {"type": "value"}, "series": [
        {"name": "Reha", "rolle": "stapel", "type": "line", "stack": "art", "data": [1, 2]}]}, T, tageswerte=True)
    assert o["series"][0]["step"] == "end"
    b = ds.einheitlich({"xAxis": {"type": "category", "data": ["a", "b"]}, "yAxis": {"type": "value"}, "series": [
        {"name": "Ist", "rolle": "balken_ist", "type": "bar", "data": [3, None]},
        {"name": "erwartet", "rolle": "balken_prognose", "type": "bar", "data": [None, 4]}]}, T, legende=False)
    assert b["series"][0]["type"] == "bar" and b["series"][1]["itemStyle"]["borderType"] == "dashed"
    assert b["legend"]["show"] is False


def test_karte_und_ansichten():
    q = lambda n: (MOD / n).read_text(encoding="utf-8")  # noqa: E731
    k = q("diagramm_karte.py")
    for teil in ('"diagramm"', '"tabelle"', '"fx"', '"kopieren"', '"voll"', "Auf einen Blick", "m-dk-stand"):
        assert teil in k, teil
    js, css = q("diagramm_ui.py"), q("diagramm_ui.py")
    assert "karteAusstatten" in js and "'Escape'" in js and "m-fokus" in js and "showTip" in js
    assert "@container (max-width: 760px)" in css and ".m-dk.voll" in css and "minmax(0, 3fr) minmax(240px, 300px)" in css
    assert "<span>Größe ziehen" not in js                                             # Hinweistext entfällt
    assert "_tagesverlauf_karte" in q("seite_auswertung.py") and "diagramm_karte.Karte" in q("seite_massnahmen.py")
    assert "diagramm_karte.Karte" in q("seite_prognose.py") and "m-xg-fuss\" + (\"\" if klassisch else \" m-weg\")" in q("seite_prognose.py")


# ---- inkl. UWTler und Mieter -------------------------------------------------------------------------------------

def test_vertragsgrenze_und_gruppensaetze():
    gr = [30, 32, 31, 33, 30, 12, 4, 0]
    assert bk.vertrags_grenze(gr, 2) == 5 and bk.vertrags_grenze(gr, None) is None and bk.vertrags_grenze([0, 0], 0) is None
    ms = [date(2026, m, 1) for m in range(5, 13)]
    ist = [True] * 3 + [False] * 5
    uwt = [20, 22, 26, 27, 28, 8, 3, 0]
    mie = [9, 9, 9, 9, 9, 4, 1, 0]
    ges = [100 + u + m for u, m in zip(uwt, mie)]
    b = bk.gruppen(ms, ist, ges, uwt, mie, date(2026, 7, 20), 140, 26, 36, bk.vertrags_grenze([u + m for u, m in zip(uwt, mie)], 2))
    t = [s.text for s in b.saetze]
    assert t[0] == "Heute 135 belegt von 140 Plätzen (96 %), davon 26 UWTler und 9 Mieter."
    assert t[1].startswith("Kontingent UWT 26: heute 26 (100 %), in 2 der nächsten 5 Monate darüber (zuerst Aug 26)")
    assert "Kontingent UWT + Mieter 36" in t[2] and "Bekannte Verträge reichen großteils bis Sep 26" in t[3]


def test_status_karte_zwei_flaechen():
    from modern import seite_prognose as sp

    q = (MOD / "seite_prognose.py").read_text(encoding="utf-8")
    assert "def _status_karte" in q and '"axisPointer"' in q and '"link": [{"xAxisIndex": "all"}]' in q
    assert "inkl. UWTler und Mieter" in q and "_js_schalter(" in q and "noch keine Verträge" in q
    z = sp.zoom([f"M{i}" for i in range(48)], 24)
    assert z[0]["startValue"] == "M12" and z[0]["endValue"] == "M36" and z[0]["xAxisIndex"] == "all"
    assert "Netto (Internatsplätze ohne FRAI" in sp.NETTO_TEXT[False]
