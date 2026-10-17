"""6.17: Termine nach Dringlichkeit/Gruppen, Datenstatus, fehlende Namen, Balkenbeschriftung, Kontraste, Zeitraum."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

HEUTE = date(2026, 10, 17)


def _t(i, tage, art="abreise", titel="Abreise"):
    from belegung import termine as tm

    return tm.Termin(f"t{i}", HEUTE + timedelta(days=tage), f"{titel} {i}", art=art, erinnern_am=HEUTE - timedelta(days=1))


def test_dringlichkeit_aus_dem_datum():
    from belegung import termine as tm

    assert [tm.dringlichkeit(_t(0, d), HEUTE) for d in (-3, 0, 5, 20)] == ["ueberfaellig", "heute", "bald", "spaeter"]


def test_gruppen_verlieren_nichts_und_zaehlen_richtig():
    from belegung import termine as tm

    termine = [_t(i, -1) for i in range(5)] + [_t(9, -1, art="notiz", titel="Notiz")] + [_t(10, 0)] + [_t(11, 3)]
    gruppen = tm.gruppieren(termine, HEUTE)
    alle = [t.id for _s, bl in gruppen for _ti, liste in bl for t in liste]
    assert sorted(alle) == sorted(t.id for t in termine)                    # jeder Termin genau einmal
    stufe, bloecke = gruppen[0]
    assert stufe == "ueberfaellig"
    gruppe = next((ti, liste) for ti, liste in bloecke if ti)
    assert gruppe[0].startswith("Abreise am 16.10.2026 · 5 Erinnerungen") and len(gruppe[1]) == 5
    assert any(not ti and liste[0].art == "notiz" for ti, liste in bloecke)   # andere Art: nicht zusammengelegt
    assert [s for s, _b in gruppen] == ["ueberfaellig", "heute", "bald"]


def test_fehlende_namen_ehrlich_und_eindeutig():
    from belegung import zimmerplan as zp

    for roh in ("unknown1", "Unknown 12", "", None, "N.N.", "??"):
        assert zp.name_fehlt(roh) and zp.anzeige_name(roh) == zp.NAME_FEHLT
    assert not zp.name_fehlt("Anders, Anna") and zp.anzeige_name("Anders, Anna") == "Anders, Anna"
    a = zp.gp_schluessel("unknown1", "GS-2-101", date(2026, 10, 1))
    b = zp.gp_schluessel("unknown1", "GS-2-102", date(2026, 10, 1))
    assert a != b                                                     # nie zwei Personen unter einem Schlüssel
    assert zp.gp_schluessel("Anders, Anna", "GS-2-101", date(2026, 10, 1)) == zp.gp_schluessel("Anders, Anna")
    bel = zp.Belegung("GS-2-101", date(2026, 10, 1), date(2026, 10, 30), "belegt", "unknown3", "GS ASS")
    assert zp.balken_text(bel)[0].startswith(zp.NAME_FEHLT)


def test_datenstatus_nie_aktuell_nach_fehler():
    from belegung import datenstatus as dst

    ds = SimpleNamespace(stichtag=date(2026, 10, 16), quelle=None, geladen_am=datetime(2026, 10, 17, 9, 31),
                         pivot_aktualisiert=None, pivot=SimpleNamespace(abrufdatum=HEUTE))
    assert dst.pivot(ds, heute=HEUTE).pille == "aktuell"
    fehl = dst.pivot(ds, "Datei gesperrt", datetime(2026, 10, 17, 10, 0), heute=HEUTE)
    assert fehl.stufe == "ueber" and fehl.pille == "Laden fehlgeschlagen" and "Datei gesperrt" in fehl.tipp
    ds.pivot.abrufdatum = date(2026, 9, 28)
    assert dst.pivot(ds, heute=HEUTE).pille == "19 Tage alt"                 # aus dem Zeitstempel berechnet
    ds.pivot.abrufdatum = None
    assert dst.pivot(ds, heute=HEUTE).pille == "Alter unbekannt"
    assert dst.pivot(None, heute=HEUTE).pille == "keine Daten"
    plan = SimpleNamespace(stand=date(2026, 10, 3))
    assert dst.gebaeudeplan(plan, HEUTE) == ("Gebäudeplan: 03.10.2026 · 14 Tage alt", "knapp")
    assert dst.gebaeudeplan(None, HEUTE)[1] == "knapp"


def test_balkenbeschriftung_gestuft(qapp):
    from PySide6.QtGui import QFont, QFontMetrics

    from belegung.ui.zeitstrahl import beschriftung

    fm = QFontMetrics(QFont("Sans", 9))
    text = "Mustermann, Erika (XY ABC DE 000000)"
    assert beschriftung(fm, text, 1000) == text
    mittel = beschriftung(fm, text, fm.horizontalAdvance("Mustermann, Erika") + 2)
    assert mittel == "Mustermann, Erika"
    assert beschriftung(fm, text, fm.horizontalAdvance("Mustermann") + 2) == "Mustermann"
    assert beschriftung(fm, text, 10) == ""                      # zu schmal: keine Schrift statt Zeichensalat


def test_kontraste_in_allen_designs(qapp):
    from belegung.ui import theme

    for d in theme.DESIGNS:
        for m in ("hell", "dunkel"):
            theme.design_setzen(d)
            t = theme.setzen(m)
            for flaeche in (t.surface, t.bg, t.surface_2):
                assert theme.kontrast(t.text_3, flaeche) >= 4.5, (d, m)
                assert theme.kontrast(t.text_2, flaeche) >= 4.5, (d, m)
    theme.design_setzen("klassisch")
    theme.setzen("hell")


@pytest.mark.parametrize("zeitraum, anker, erwartet", [
    ("wochen", date(2026, 10, 17), (date(2026, 10, 12), date(2026, 10, 25))),
    ("monat", date(2026, 10, 17), (date(2026, 10, 1), date(2026, 10, 31))),
    ("quartal", date(2026, 11, 17), (date(2026, 11, 1), date(2027, 1, 31))),
])
def test_zeitstrahl_zeitraum(tmp_path, monkeypatch, qapp, zeitraum, anker, erwartet):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    from belegung.ui.basis import Zustand
    from belegung.ui.seiten.zimmerplan import ZimmerplanSeite

    s = ZimmerplanSeite(Zustand(), nebenfenster=True)
    s._zs_zeitraum, s._zs_start = zeitraum, anker
    assert s._zs_bereich()[:2] == erwartet


def test_kpi_karte_verbreitert_die_reihe_nicht(qapp):
    from belegung.ui.widgets import KpiKarte

    k = KpiKarte("Bad Pyrmont", farbe_punkt="#2a9d8f")
    k.wert.setText("95 %")
    k.einheit.setText("ausgelastet")
    k.delta.setText("▼ 8 / Woche")
    k.detail.setText("180 belegt · 10 frei · 190 Plätze")
    assert k.minimumSizeHint().width() < 200     # vier Karten passen neben die Seitenleiste (1000 px)
    leer = KpiKarte("Belegt heute")
    assert leer.delta.minimumSizeHint().width() <= 60 and leer.delta.minimumWidth() == 1
