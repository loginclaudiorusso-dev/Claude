"""1.61: drei kleine Navigationsschritte aus dem Menü-Audit – Belegungsprognose mit höchstens zwei Kontextkarten,
„Mehr“ in Zuteilen nach Häufigkeit, Reinigung an einer Stelle."""

from types import SimpleNamespace

from modern import menueband as mb
from modern import seite_anreisen


def test_prognose_hoechstens_zwei_kontextkarten():
    kontext = [r for r in mb.reiter({}) if r.kontext and mb.sichtbar(r, "auswertung", "prognose")]
    assert [r.key for r in kontext] == ["prognose"]      # + Werkzeug-Karte der Seite = zwei
    prog = kontext[0]
    assert sum(len(g.punkte) for g in prog.gruppen) <= 9               # 1.75: + „Berechnung“
    ziele = {q.ziel[1] for g in prog.gruppen for p in g.punkte for q in p.menue if q.ziel}
    assert {"dg_typ:auto", "dg_legende:oben", "dg:dg_glatt", "optionen:diagramme", "awt:aw_95", "awt:aw_backtest"} <= ziele
    # andere Diagrammseiten behalten ihre Registerkarte „Diagramm“
    d = next(r for r in mb.reiter({}) if r.key == "diagramm")
    assert mb.sichtbar(d, "auswertung", "belegung") and mb.sichtbar(d, "steuerung", "zeitplan")


def test_reinigung_an_einer_stelle():
    rs = {r.key: r for r in mb.reiter({}) if not r.kontext}
    def ziele(k):
        return {(p.ziel[1], p.ziel[2]) for g in rs[k].gruppen for p in g.punkte if p.ziel and p.ziel[0] == "seite"}
    reinigung = {("reinigung", "liste"), ("reinigung", "last"), ("reinigung", "facility")}
    assert reinigung <= ziele("zimmer")
    assert not any(z[0] == "reinigung" for k in rs if k != "zimmer" for z in ziele(k))
    assert all(sum(len(g.punkte) for g in r.gruppen) <= 8 for r in rs.values())
    # ohne Leitung bleibt in „Planung“ keine leere Gruppe stehen
    ohne = {r.key: r for r in mb.reiter({}, leitung=False)}
    assert all(g.punkte for g in ohne["planung"].gruppen)


def test_mehr_nach_haeufigkeit():
    a = SimpleNamespace(zu_vergangene=False, kennung="x", heute=None)
    abschnitte = seite_anreisen.mehr_eintraege(a)
    assert [k for k, _ in abschnitte] == ["Täglich", "Suchen & Export", "Selten – Umplanen"]
    texte = [t for _k, e in abschnitte for t, _f in e]
    assert texte[0] == "Person hinzufügen …" and len(texte) == 12 and len(set(texte)) == 12
    selten = [t for t, _f in abschnitte[-1][1]]
    assert "Belegung optimieren …" in selten and "Planung dieser Anreise zurücknehmen" in selten
