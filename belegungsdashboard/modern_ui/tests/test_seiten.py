"""Neue Oberfläche: Zeitstrahl, Reinigung, Mieter, Auswertung, Verwalten – nur erfundene Namen."""

from datetime import date, timedelta

import pytest


@pytest.fixture
def haus(tmp_path, monkeypatch):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    heute = date.today()                               # „Erledigt“ zählt erst ab dem ersten Gebrauch (heute)
    p = [anreiseliste.Person("Abreise, Alma", "GS RVL", heute - timedelta(days=30), True, tn_id="1", abreise=heute),
         anreiseliste.Person("Neu, Nils", "GS RVL", heute + timedelta(days=2), True, tn_id="2",
                             abreise=heute + timedelta(days=40))]
    anreiseliste.speichern(p, {})
    st = zp.laden()
    b = {x.name.split(",")[0]: x for x in st.bedarf}
    zp.zuweisungen_speichern([zp.Zuteilung(b["Abreise"], st.lage.zimmer["GS-2-301"]),
                              zp.Zuteilung(b["Neu"], st.lage.zimmer["GS-2-301"])])
    yield heute
    aenderungen.verlauf_leeren()


def test_zeitstrahl_balken(haus):
    from belegung import zimmerplan as zp
    from modern import seiten_kern as sk

    st = zp.laden()
    assert "2" in sk.haeuser(st)
    start = haus - timedelta(days=haus.weekday())
    zs = {z.kurz: z for z in sk.zeitstrahl(st, "2", start, 28, haus)}
    balken = zs["2-301"].balken
    assert [b.text for b in balken] == ["Abreise", "Neu"]
    alt = balken[0]
    assert alt.offen_links and alt.start == 0 and alt.tage == (haus - start).days + 1
    assert balken[1].art == "geplant" and "Neu, Nils" in balken[1].titel


def test_reinigung_abhaken_hinzufuegen_rueckgaengig(haus, monkeypatch):
    from belegung import reinigungsliste as rl
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import seiten_kern as sk

    von, bis = sk.zeitraum("woche", haus)
    zs = sk.reinigung(zp.laden(), von, bis, haus)
    z = next(x for x in zs if x.zimmer == "2-301")
    assert z.art == "Auszug" and not z.erledigt and "Neu" in z.danach
    sk.reinigung_setzen([z.schluessel], True, von, bis)
    assert z.schluessel in rl.erledigt()
    assert kern.rueckgaengig()[0] and z.schluessel not in rl.erledigt()
    sk.reinigung_hinzu("2-310", haus, "Grundreinigung")
    neu = next(x for x in sk.reinigung(zp.laden(), von, bis, haus) if x.zimmer == "2-310")
    assert neu.manuell_id and "Grundreinigung" in neu.art
    sk.reinigung_entfernen(neu.manuell_id)
    assert not any(x.zimmer == "2-310" for x in sk.reinigung(zp.laden(), von, bis, haus))
    with pytest.raises(ValueError):
        sk.reinigung_hinzu("9-999", haus, "")
    assert "<table" in sk.reinigung_druck(von, bis, haus)


def test_mieter_mail_und_vermerk(haus):
    from belegung import mieter as mt
    from modern import seiten_kern as sk

    mt.anlegen(mt.Mietvertrag("26-990", "Frau", "Erika", "Erfunden", "GS-6-1005", haus - timedelta(days=100),
                              haus + timedelta(days=10), email="erika@example.org"))
    vertraege, _weitere = sk.mieter(haus)
    m = next(x for x in vertraege if x.nr == "26-990")
    assert m.mail_offen and m.stufe == "warn"
    an, betreff, text = sk.mieter_mail("26-990", "anfrage", haus)
    assert an == "erika@example.org" and "26-990" in betreff and "Erfunden" in text
    sk.mieter_mail_vermerken("26-990", "erika@example.org")
    assert not next(x for x in sk.mieter(haus)[0] if x.nr == "26-990").mail_offen


def test_auswertung_verwalten_einstellung(haus):
    from belegung import speicher
    from belegung import zimmerplan as zp
    from modern import kern
    from modern import seiten_kern as sk

    aw = sk.auswertung(zp.laden(), haus, 4)
    assert len(aw.wochen) == 4 and aw.haeuser and all(0 <= h.quote <= 100 for h in aw.haeuser)
    bereiche = [x[0] for x in sk.datenstand(zp.laden())]
    assert "Gebäudeplan" in bereiche and "Datenordner" in bereiche
    assert sk.neuer_plan() is None
    sk.einstellung_setzen("reinigung_anreisetag", True)
    assert speicher.einstellungen()["reinigung_anreisetag"] is True
    assert kern.rueckgaengig()[0] and not sk.einstellungen()["reinigung_anreisetag"]
    with pytest.raises(ValueError):
        sk.einstellung_setzen("zimmer_puffer", 30)
