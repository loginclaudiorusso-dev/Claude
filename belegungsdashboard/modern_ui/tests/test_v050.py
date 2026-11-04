"""0.50: Maßnahmen-Prognose – Pivot einlesen (nur Zählwerte), Lücke überbrücken, Gruppen, erwartete Kurse, Rückwärts-
test, Internatsanteil aus Word/PDF-Listen (P = Pendler, K = Kostenzusage). Erfundene Kurse und Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    from belegung import aenderungen

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    yield tmp_path
    aenderungen.verlauf_leeren()


def _pivot(luecke=None):
    """Erfundener Pivot: VW startet jedes Jahr am 1.6. (20 Personen, 600 Tage), FISY am 1.1. und 1.6. (8, 500 Tage),
    EMR jeden Monat 2 Tage. Je Kurs eine Personenzeile davor (Name erfunden)."""
    tage = [date(2021, 1, 1) + timedelta(days=i) for i in range(365 * 8)]
    if luecke:
        tage = [t for t in tage if not (luecke[0] <= t <= luecke[1])]
    kopf = ("Zeilenbeschriftungen",) + tuple(t.strftime("%d.%m.%Y") for t in tage)
    zeilen = [("Maßnahme", "(Mehrere Elemente)"), ("Teilnehmer Anzahl",), kopf]

    def kurs(name, start, n, dauer, schwund=0.0):
        for p in range(n):
            ende = start + timedelta(days=dauer - 1 if p >= n * schwund else dauer // 6)
            zeilen.append((f"Muster, Person{p}",))
            zeilen.append((name,) + tuple(1 if start <= t <= ende else None for t in tage))
    for j in range(2021, 2027):
        kurs(f"GS VW {j % 100}06", date(j, 6, 1), 20, 600, .1)
        kurs(f"GS FISY {j % 100}01", date(j, 1, 15), 8, 500)
        kurs(f"GS FISY {j % 100}06", date(j, 6, 15), 8, 500)
        for m in range(1, 13):
            kurs(f"GS EMR ASS {j % 100}{m:02d}05", date(j, m, 5), 2, 2)
    kurs("GS virtueller Infotag", date(2024, 3, 3), 3, 1)
    zeilen.append(("Gesamtergebnis",))
    return zeilen


def test_pivot_nur_zaehlwerte_und_luecke_ueberbrueckt(leer):
    from modern import massnahmen_kern as mk

    erg = mk.pivot_aus_zeilen(_pivot(luecke=(date(2025, 12, 1), date(2025, 12, 31))))
    assert erg.luecken == [(date(2025, 12, 1), date(2025, 12, 31))]
    vw = erg.kurse["GS VW 2506"]
    werte = mk._unrle(vw["werte"])
    k = (date(2025, 12, 15) - date(2025, 6, 1)).days
    assert werte[k] == werte[k - 20] == 18                # Dezember wie Ende November (2 von 20 schon weg)
    assert not any("Muster" in k for k in erg.kurse) and vw["dauer"] == 600
    mk.pivot_schritt(erg, "pivot.xlsx")
    gr = mk.gruppen()
    assert gr["GS VW"] == "lang" and gr["GS FISY"] == "lang" and gr["GS EMR ASS"] == "uebrige"
    assert gr["GS virtueller Infotag"] == "ohne"


def test_erwartete_kurse_im_rhythmus_und_gebuchte_nicht_doppelt(leer):
    from modern import massnahmen_kern as mk

    mk.pivot_uebernehmen(mk.pivot_aus_zeilen(_pivot()), "p.xlsx")
    ks = mk.kurse()
    neu = mk.erwartete_kurse(ks, date(2026, 11, 3), date(2028, 12, 31), None, date(2021, 1, 1), {"GS VW", "GS FISY"})
    vw = [e.start for e in neu if e.familie == "GS VW"]
    assert vw == [date(2027, 6, 1), date(2028, 6, 1)]                    # 2026 ist gebucht, also nicht doppelt
    assert all(round(e.spitze) == 20 for e in neu if e.familie == "GS VW")
    fisy = [e.start for e in neu if e.familie == "GS FISY"]
    assert date(2027, 1, 15) in fisy and date(2027, 6, 15) in fisy
    mk.plaetze_schritt("GS VW", "2027-06", 30)
    neu2 = mk.erwartete_kurse(ks, date(2026, 11, 3), date(2028, 12, 31), mk._roh()["plaetze"], date(2021, 1, 1), {"GS VW"})
    p = next(e for e in neu2 if e.start.year == 2027)
    assert p.herkunft == "geplant" and round(p.spitze) == 30


def test_prognose_internat_und_tabelle(leer):
    from modern import massnahmen_kern as mk

    mk.pivot_uebernehmen(mk.pivot_aus_zeilen(_pivot()), "p.xlsx")
    mk.listen_uebernehmen({"GS VW 2506": {"tn": 20, "pendler": 5, "zusage": 19}, "GS FISY 2501": {"tn": 10, "pendler": 0, "zusage": 10}}, "l.docx")
    tn = mk.prognose(None, date(2026, 11, 3), 12, 24)
    bett = mk.prognose(None, date(2026, 11, 3), 12, 24, internat=True)
    assert tn.zeilen[0].art == "ist" and tn.zeilen[-1].art == "prognose" and len(tn.zeilen) == 37
    z = next(x for x in tn.zeilen if x.monat == date(2027, 9, 1))
    zb = next(x for x in bett.zeilen if x.monat == date(2027, 9, 1))
    assert z.erwartet > 15 and z.klein <= z.erwartet <= z.gross
    assert zb.je_gruppe["lang"] < z.je_gruppe["lang"] and "ohne" not in z.je_gruppe
    t = {f.familie: f for f in tn.familien}
    assert set(t) == {"GS VW", "GS FISY"} and t["GS VW"].naechster == date(2027, 6, 1) and t["GS VW"].kursgroesse == 20
    assert 0.85 < t["GS VW"].verbleib < 0.95                              # 10 % gehen früh
    anteile, gesamt = mk.internat_anteile()
    assert anteile["GS VW"] == 0.75 and anteile["GS FISY"] == 1.0 and gesamt == pytest.approx(25 / 30)


def test_rueckwaertstest_bei_regelmaessigen_kursen_genau(leer):
    from modern import massnahmen_kern as mk

    mk.pivot_uebernehmen(mk.pivot_aus_zeilen(_pivot()), "p.xlsx")
    ts = {t.jahr: t for t in mk.rueckwaertstest(jahre=[2024, 2025])}
    assert abs(ts[2024].h1) < 2 and abs(ts[2024].h2) < 2 and len(ts[2025].monate) == 12


def test_word_und_pdf_liste_p_ist_pendler_k_ist_zusage(leer):
    from modern import massnahmen_kern as mk

    text = """Teilnehmer Beginn
GS VW 2706   vom 01.06.2027 bis 31.12.2028
01.06.27 Muster, Anna   01.01.90   DRV Bund   P   K
01.06.27 Probe, Ben   02.02.91   AA Musterstadt   K
03.06.27* Test, Carla   03.03.92   JC MusterstadtSP K
05.06.27 Beispiel, Dora   04.04.93   DRV   H
Maßnahme GS VW 2706: 4 TN"""
    erg = mk.listen_aus_text(text)
    assert erg == {"GS VW 2706": {"tn": 4, "pendler": 2, "zusage": 3}}


def test_docx_wird_gelesen(leer):
    import zipfile

    from modern import pdf_anreise_kern as pk

    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    def zelle(t): return f"<w:tc><w:p><w:r><w:t>{t}</w:t></w:r></w:p></w:tc>"
    xml = (f"<w:document {w}><w:body><w:tbl><w:tr>{zelle('GS KBM 2701')}{zelle('vom 15.01.2027 bis 14.01.2029')}</w:tr>"
           f"<w:tr>{zelle('15.01.27 Muster, Max')}{zelle('01.01.90 DRV Bund')}{zelle('P K')}</w:tr></w:tbl>"
           f"<w:p><w:r><w:t>Maßnahme GS KBM 2701: 1 TN</w:t></w:r></w:p></w:body></w:document>")
    pfad = leer / "liste.docx"
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("word/document.xml", xml)
    listen = pk.lesen_text(pk.text_lesen(pfad), "liste.docx")
    assert len(listen) == 1 and listen[0].gruppe == "GS KBM 2701" and not listen[0].personen[0].internat
