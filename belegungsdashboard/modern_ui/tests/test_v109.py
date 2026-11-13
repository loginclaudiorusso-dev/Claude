"""1.09 – mehrere Gästehaus-Vormerkungen in einer Mail. Nur erfundene Namen, Orte und Anschriften."""

from datetime import date

from modern import mail_kern as mk

HEUTE = date(2026, 11, 13)
BETREFF = "Vormerkungen Dezember"
TEXT = (
    "Hallo Erika,\n\n"
    "folgende Vormerkungen habe ich für den Dezember, Probe und Test sind fix, Muster und Beispiel melden sich noch, "
    "wobei letzterer immer Gäste aus dem Ausland hat, die Visa benötigen, so dass es meistens sehr kurzfristig "
    "bestätigt oder auch geändert wird.\n\n"
    "Hr. Max MUSTER, MA JH\t2 DZ\t04. - 06.12.2026\n"
    "Hr. Beispiel, Feuerwehr Musterstadt\tZimmer für 5 - 6 Gäste, EZ o. DZ\t10. - 13.12.2026\n"
    "Paula PROBE, ehem. TN \t3 EZ\t19. - 20.12.2026\n"
    "Hr. Tim TEST, Musterweg 1, 12345 Musterort\t1 DZ\t11. - 13.12.26\n\n"
    "Freundliche Grüße\n\ni. A. Lena Lorem\nKundenmanagement\nBeispiel gGmbH\nMusterallee 1\n12345 Musterstadt\n"
    "Tel: +49 0000 000-000\n")


def test_vier_buchungen_mit_zimmern_und_zeitraum():
    b = mk.buchungen(BETREFF, TEXT, HEUTE)
    assert [x.name for x in b] == ["Muster, Max", "Beispiel", "Probe, Paula", "Test, Tim"]
    assert [(x.zimmer, x.art) for x in b] == [(2, "DZ"), (6, "EZ o. DZ"), (3, "EZ"), (1, "DZ")]
    assert [(x.von, x.bis) for x in b] == [(date(2026, 12, 4), date(2026, 12, 6)), (date(2026, 12, 10), date(2026, 12, 13)),
                                           (date(2026, 12, 19), date(2026, 12, 20)), (date(2026, 12, 11), date(2026, 12, 13))]
    assert b[0].zusatz == "MA JH" and b[3].zusatz == "Musterweg 1, 12345 Musterort"
    assert b[1].gaeste == (5, 6) and any("Zimmerzahl offen" in h for h in b[1].hinweise)
    assert b[0].geschlecht == "m" and b[2].geschlecht == ""


def test_fest_und_offen_aus_dem_begleittext():
    b = {x.nachname: x for x in mk.buchungen(BETREFF, TEXT, HEUTE)}
    assert b["Probe"].status == "fix" and b["Test"].status == "fix"
    assert b["Muster"].status == "offen" and b["Beispiel"].status == "offen"
    assert any("Kurzfristige" in h for h in b["Beispiel"].hinweise)
    assert not any("Kurzfristige" in h for h in b["Muster"].hinweise)


def test_unterschrift_und_einzelmail_ergeben_keine_buchung():
    assert mk.buchungen("Frage", "Wann ist die Hausordnung fertig?\n\nViele Grüße\nMax", HEUTE) == []
    einzel = mk.buchungen("Anfrage", "Herr Max Muster kommt am 04.12.2026 zur Schulung.", HEUTE)
    assert einzel == []                                   # ohne Zimmerangabe: bleibt die normale Erkennung


def test_erkannt_je_zimmer_eindeutig():
    b = mk.buchungen(BETREFF, TEXT, HEUTE)[0]
    namen = [mk.erkannt_fuer(b, n).name for n in range(b.zimmer)]
    assert namen == ["Muster, Max (DZ 1/2)", "Muster, Max (DZ 2/2)"]
    e = mk.erkannt_fuer(b, 0)
    assert e.art == "gast" and e.massnahme == "Gast Gästehaus" and "vorgemerkt" in e.zusammenfassung


def test_tabelle_aus_outlook_je_zelle_eine_zeile():
    zellen = TEXT.replace("\t", "\n")
    b = mk.buchungen(BETREFF, zellen, HEUTE)
    assert [(x.name, x.zimmer, x.von) for x in b] == [("Muster, Max", 2, date(2026, 12, 4)), ("Beispiel", 6, date(2026, 12, 10)),
                                                       ("Probe, Paula", 3, date(2026, 12, 19)), ("Test, Tim", 1, date(2026, 12, 11))]
    assert b[0].zusatz == "MA JH"
    assert {x.nachname: x.status for x in b} == {"Muster": "offen", "Beispiel": "offen", "Probe": "fix", "Test": "fix"}


def test_fliesstext_mit_zimmer_wird_keine_liste():
    t = ("Hallo Erika,\n\nfür UWTler Muster wurde eine zusätzliche Unterbringung angefragt. Die Unterbringung würde "
         "nahtlos vom 08.02. – 26.02.2027 erfolgen, Zimmer bitte im selben Haus.\n\nViele Grüße\nPaula Probe")
    assert mk.buchungen("Zusätzliche Unterbringung UWTler Muster, Max (123456)", t, HEUTE) == []
    assert mk.erkennen("Zusätzliche Unterbringung UWTler Muster, Max (123456)", t, HEUTE).art == "anmeldung"


def test_posteingang_name_ohne_zimmerzusatz():
    b = mk.buchungen(BETREFF, TEXT, HEUTE)[0]
    assert mk.erkannt_fuer(b, None).name == "Muster, Max"


def test_v110_tabelle_mit_leerzeilen_zwischen_den_zellen():
    """So kommt die Tabelle aus Outlook: jede Zelle ein Absatz, dazwischen Leerzeilen."""
    zellen = TEXT.replace("\t", "\n\n")
    b = mk.buchungen(BETREFF, zellen, HEUTE)
    assert [(x.name, x.zimmer, x.art, x.von, x.bis) for x in b] == [
        ("Muster, Max", 2, "DZ", date(2026, 12, 4), date(2026, 12, 6)),
        ("Beispiel", 6, "EZ o. DZ", date(2026, 12, 10), date(2026, 12, 13)),
        ("Probe, Paula", 3, "EZ", date(2026, 12, 19), date(2026, 12, 20)),
        ("Test, Tim", 1, "DZ", date(2026, 12, 11), date(2026, 12, 13))]
    assert {x.nachname: x.status for x in b} == {"Muster": "offen", "Beispiel": "offen", "Probe": "fix", "Test": "fix"}
    assert b[3].zusatz == "Musterweg 1, 12345 Musterort"


def test_v110_tabelle_ohne_begleittext_und_mit_langer_unterschrift():
    t = ("Hr. Max MUSTER, MA JH\n\n2 DZ\n\n04. - 06.12.2026\n\nPaula PROBE, ehem. TN\n\n3 EZ\n\n19. - 20.12.2026\n\n\n"
         "Freundliche Grüße\n\ni. A. Lena Lorem\nKundenmanagement\nMusterallee 1\n12345 Musterstadt\n"
         "Beispiel gGmbH | Sitz der Gesellschaft: 12345 Musterstadt | Amtsgericht Musterstadt HRB: 000000\n")
    b = mk.buchungen("Vormerkungen", t, HEUTE)
    assert [(x.name, x.zimmer) for x in b] == [("Muster, Max", 2), ("Probe, Paula", 3)]


def test_v110_outlook_zeichen():
    t = (TEXT.replace("\t", "\r\n\r\n").replace(". - ", ". ‑ ").replace("Hr. ", "Hr. "))
    b = mk.buchungen(BETREFF, t, HEUTE)
    assert [(x.name, x.zimmer, x.von, x.bis) for x in b][:2] == [("Muster, Max", 2, date(2026, 12, 4), date(2026, 12, 6)),
                                                                ("Beispiel", 6, date(2026, 12, 10), date(2026, 12, 13))]
    assert len(b) == 4
