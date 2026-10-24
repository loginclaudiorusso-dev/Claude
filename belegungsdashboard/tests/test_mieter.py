"""6.20: Mieter-Unterlagen – Maske → Mietvertrag, Vordrucke, Zimmerplan; Verlängerung per Nebenabrede.
Nur erfundene Personen und eine kleine Test-Vorlage (die echten Vorlagen liegen nur im Update-Paket)."""

import io
import zipfile
from datetime import date

import pytest

VORLAGE = """# Test
=Mietvertrag
=Nr. {nr}
{name}, {mieter_adresse}
>im Folgenden [Mieterin|Mieter] genannt
---SEITE---
==§ 1 Mietgegenstand
1. Haus {haus} Zimmer Nr. {zimmer}, Wohnfläche ca. {flaeche} m², {schluessel} Schlüssel.
2. Das Mietverhältnis beginnt am {von} und endet am {bis}. Mietzins {miete} €, Kaution bis {kaution_bis}.
|IBAN:|DE00 0000
+[Die Mieterin|Der Mieter] haftet, wenn [sie|er] es verschuldet.
@UNTERSCHRIFT
"""


@pytest.fixture
def daten(tmp_path, monkeypatch):
    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    return tmp_path


def _mv(nr="26-011", anrede="Frau", zimmer="GS-6-1005"):
    from belegung import mieter as mt

    return mt.Mietvertrag(nr, anrede, "Hanna", "Testfall", zimmer, date(2026, 9, 1), date(2027, 2, 28))


def test_nummer_ende_und_pruefen():
    from belegung import mieter as mt

    assert mt.naechste_nummer(date(2026, 10, 17), ["26-009", "26-010", "25-120"]) == "26-011"
    assert mt.naechste_nummer(date(2027, 1, 3), ["26-010"]) == "27-001"
    assert mt.standard_ende(date(2026, 9, 1)) == date(2027, 2, 28)       # wie MV26-010: 01.09. → 28.02.
    assert mt.standard_ende(date(2026, 8, 31)) == date(2027, 2, 27)
    mv = _mv()
    assert mt.pruefen(mv, []) == []
    assert any("vergeben" in f for f in mt.pruefen(mv, [_mv()]))
    mv.nr, mv.vorname = "26/11", ""
    assert len(mt.pruefen(mv, [])) == 2


def test_vertrag_passt_sich_der_anrede_an():
    from belegung import mieter as mt

    frau = mt.vertrag_html(_mv(), VORLAGE)
    herr = mt.vertrag_html(_mv(anrede="Herr"), VORLAGE)
    for t in (frau, herr):
        assert "[" not in t and "{" not in t                                 # alles ersetzt
        assert "Nr. 26-011" in t and "Hanna Testfall" in t and "Zimmer Nr. 1005" in t and "450,00 €" in t
        assert "Kaution bis 01.09.2026" in t and "page-break-before" in t and "DE00 0000" in t
    assert "Mieterin genannt" in frau and "Die Mieterin haftet, wenn sie" in frau
    assert "Mieter genannt" in herr and "Mieterin" not in herr and "Der Mieter haftet, wenn er" in herr


def test_anlegen_steht_im_zimmerplan_und_verlaengern(daten):
    from belegung import mieter as mt
    from belegung import zimmerplan as zp

    st = zp.laden()
    probe = zp.Bedarf("x", "x", "Miete Goslar", "Mieter", date(2026, 9, 1), date(2027, 2, 28), "w")
    zimmer = next(z for z in st.zimmer if z.aktiv and zp.passt(st.lage, z, probe) is None)
    mv = _mv(zimmer=zimmer.id)
    mt.anlegen(mv)
    st = zp.laden()
    b = next(b for b in st.bedarf if b.schluessel == "mv:26-011")
    assert (b.gruppe, b.name, b.bis) == ("Mieter", "Testfall, Hanna", date(2027, 2, 28))
    assert any(x.person == "mv:26-011" for x in st.lage.belegungen[zimmer.id])
    assert mt.naechste_nummer(date(2026, 10, 17)) == "26-012"
    with pytest.raises(ValueError):
        mt.verlaengern("26-011", date(2027, 1, 31))
    mt.verlaengern("26-011", date(2027, 8, 31))
    st = zp.laden()
    assert next(b for b in st.bedarf if b.schluessel == "mv:26-011").bis == date(2027, 8, 31)
    assert mt.laden()[0].verlaengerungen[0]["bis_alt"] == "2027-02-28"


def test_nebenabrede_word_und_text():
    from belegung import mieter as mt

    t = mt.nebenabrede_texte(_mv(anrede="Herr"), date(2027, 8, 31), date(2027, 2, 1))
    assert t["titel"] == "Nebenabrede zum Mietvertrag 26-011 / Herr Testfall" and "31.08.2027 verlängert" in t["text"]
    assert t["ort"] == "Goslar, 01.02.2027" and t["mieter"] == "Mieter"
    z = zipfile.ZipFile(io.BytesIO(mt.nebenabrede_docx(_mv(), date(2027, 8, 31), None, date(2027, 2, 1))))
    doc = z.read("word/document.xml").decode()
    assert "Nebenabrede zum Mietvertrag 26-011 / Frau Testfall" in doc and "Mieterin" in doc
    assert {"[Content_Types].xml", "word/document.xml", "word/styles.xml"} <= set(z.namelist())


def test_paket_fuellt_vordrucke(tmp_path):
    from pypdf import PdfReader, PdfWriter

    from belegung import mieter as mt

    for name in (mt.WOHNUNGSGEBER, mt.SEPA):                # leere A4-Seiten als Ersatz-Vordrucke
        w = PdfWriter()
        w.add_blank_page(595, 842)
        w.write(tmp_path / name)
    vertrag = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(595, 842)
    w.write(vertrag)
    teile = mt.paket_erstellen(_mv(), vertrag.getvalue(), tmp_path / "paket.pdf", tmp_path)
    assert teile == ["Mietvertrag", "Wohnungsgeberbestätigung", "SEPA-Lastschriftmandat"]   # Mietschulden fehlt hier
    r = PdfReader(tmp_path / "paket.pdf")
    assert len(r.pages) == 3
    assert "Testfall" in r.pages[1].extract_text() and "01.09.2026" in r.pages[1].extract_text()
    assert "MV 26-011" in r.pages[2].extract_text() and "Hanna Testfall" in r.pages[2].extract_text()


def test_status_und_weitere_mieter(daten):
    from belegung import mieter as mt

    mv = _mv()
    assert mt.status(mv, date(2026, 8, 1))[1] == "akzent"                    # beginnt
    assert mt.status(mv, date(2026, 10, 17)) == ("läuft", "ok")
    assert mt.status(mv, date(2027, 2, 1)) == ("endet in 27 Tagen", "knapp")
    assert mt.status(mv, date(2027, 3, 1)) == ("beendet", "neutral")
    from types import SimpleNamespace

    from belegung.gebaeudeplan import Belegung
    lage = SimpleNamespace(belegungen={"GS-6-1": [Belegung("GS-6-1", date(2026, 1, 1), date(2027, 3, 31), "belegt",
                                                            "Beispiel, Kai", "Miete Goslar")],
                                       "GS-6-2": [Belegung("GS-6-2", date(2026, 1, 1), date(2027, 3, 31), "geplant",
                                                            "Testfall, Hanna", "Miete Goslar MV 26-011", person="mv:26-011")],
                                       "GS-2-1": [Belegung("GS-2-1", date(2026, 1, 1), date(2027, 3, 31), "belegt",
                                                            "Reha, Rita", "GS ASS XY 2601")]})
    weitere = mt.weitere_mieter(SimpleNamespace(lage=lage), date(2026, 10, 17))
    assert [b.name for b in weitere] == ["Beispiel, Kai"]                      # eigene (mv:) und Reha nicht


def test_kaution_optional_und_paragrafen_ruecken_auf():
    from belegung import mieter as mt

    vorlage = ("==§ 1 Miete\nText\n?kaution ==§ 2 Mietsicherheit\n?kaution Kaution bis {kaution_bis}.\n"
               "?!kaution Keine Kaution.\n==§ 3 Zustand\nText\n")
    ohne = mt.vertrag_html(_mv(), vorlage)
    assert "Mietsicherheit" not in ohne and "Keine Kaution." in ohne and "§ 2 Zustand" in ohne
    mv = _mv()
    mv.kaution, mv.kaution_bis = True, date(2026, 8, 15)
    mit = mt.vertrag_html(mv, vorlage)
    assert "§ 2 Mietsicherheit" in mit and "Kaution bis 15.08.2026." in mit
    assert "§ 3 Zustand" in mit and "Keine Kaution." not in mit
    # Verträge aus 6.20 (mit Kaution-Datum, ohne Merkmal) behalten ihre Kaution
    d = mv.zu_dict()
    d.pop("kaution")
    assert mt.Mietvertrag.aus_dict(d).kaution is True


def test_mail_zum_vertragsende(daten):
    """6.27: vorgefertigte Mail – Verlängerung anfragen oder Auszug bestätigen; „offen“, bis sie vorbereitet wurde."""
    from belegung import erinnerung, mieter as mt, vorgaenge

    mv = _mv()
    mv.bis, mv.schluessel, mv.kaution, mv.email = date(2026, 11, 30), 2, True, "hanna@example.org"
    mt.anlegen(mv)
    heute = date(2026, 10, 24)
    betreff, text = mt.ende_mail(mv, "anfrage", heute)
    assert betreff == "Ihr Mietvertrag Nr. 26-011 – Zimmer 6-1005 endet am 30.11.2026"
    assert text.startswith("Sehr geehrte Frau Testfall,") and "bis zum 02.11.2026" in text
    assert "alle 2 Schlüssel" in text and "Mietsicherheit" in text and "{" not in text
    betreff, text = mt.ende_mail(mv, "auszug", heute)
    assert "Auszug" in betreff and "bestätigen wir Ihren Auszug" in text
    herr = _mv(anrede="Herr")
    assert mt.ende_mail(herr, "anfrage", heute)[1].startswith("Sehr geehrter Herr Testfall,")
    # ohne Vertrag (laut Gebäudeplan): neutraler Gruß, keine Nummer
    from belegung.gebaeudeplan import Belegung

    ohne = mt.aus_belegung(Belegung("GS-6-1", date(2026, 1, 1), date(2026, 11, 15), "belegt", "Beispiel, Kai"))
    b, t = mt.ende_mail(ohne, "anfrage", heute)
    assert t.startswith("Guten Tag Kai Beispiel,") and "Nr." not in b and "Nr." not in t
    # offen → Vorgang „Heute“ → vermerkt → erledigt; nach Verlängerung wieder offen (für das neue Ende)
    assert mt.mail_offen(mt.laden()[0], heute)
    assert [v.ziel for v in vorgaenge.mieter_vorgaenge(heute)] == ["mieterende:26-011"]
    mt.mail_vermerken("26-011", "neu@example.org", heute)
    assert not mt.mail_offen(mt.laden()[0], heute) and mt.laden()[0].email == "neu@example.org"
    assert vorgaenge.mieter_vorgaenge(heute) == []
    assert not mt.mail_offen(mv, date(2026, 9, 1))                         # noch nicht „bald“
    url = erinnerung.mailto("a@b.de", "Betreff ä", "Zeile 1\nZeile 2")
    assert url == "mailto:a@b.de?subject=Betreff%20%C3%A4&body=Zeile%201%0D%0AZeile%202"


def test_eigene_mail_vorlage(daten, monkeypatch, tmp_path):
    from belegung import mieter as mt

    ordner = tmp_path / "vorlagen"
    ordner.mkdir()
    (ordner / "Mail_Vertragsende_anfrage.txt").write_text("Betreff: Vertrag {nr} endet\n{gruss}\nBis {ende}. {unbekannt}",
                                                          encoding="utf-8")
    monkeypatch.setattr(mt, "vorlagen_ordner", lambda: ordner)
    assert mt.ende_mail(_mv(), "anfrage") == ("Vertrag 26-011 endet",
                                              "Sehr geehrte Frau Testfall,\nBis 28.02.2027. {unbekannt}")
