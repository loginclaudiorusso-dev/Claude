"""1.57: Im Postfach-Mailfenster erkennen und übernehmen (wie im KI-Assistenten), danach Antwort mit Zimmer und
Zeitraum vorbereitet. Erkennung: „Bereitstellung von Zimmer“, Zeitraum mit Wörtern dazwischen, Essensmarken."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from belegung import mails
from belegung import zimmerplan as zp
from modern import mail_kern as mk

HEUTE = date(2026, 11, 24)
BETREFF = "Bitte um Bereitstellung von Zimmer und Essensmarken"
TEXT = ("Moin nach Goslar,\n\nHerr Probehaus wird in KW 50 an einer Erprobung als Fachinformatiker und anschließender "
        "Hospitation im Umschulungskurs teilnehmen. Wir bitten daher um Bereitstellung von Zimmer und Essensmarken in der "
        "Zeit von Sonntagabend, 6.12., bis Freitagnachmittag, 11.12.26. Bitte wenn bereitgestellt, kurz Info geben.\n\n"
        "Viele Grüße!")


def test_bereitstellung_wird_anmeldung_mit_zeitraum():
    e = mk.erkennen(BETREFF, TEXT, HEUTE)
    assert e.art == "anmeldung" and e.name == "Probehaus"
    assert (e.von, e.bis) == (date(2026, 12, 6), date(2026, 12, 11))
    assert "Essensmarken gewünscht" in e.zusammenfassung and "Erprobung/Hospitation" in e.zusammenfassung
    assert "nahtlos" not in e.zusammenfassung            # „anschließender Hospitation“ ist kein nahtloser Anschluss
    assert not any(u.startswith("Zeitraum") for u in e.unsicher)


def test_zeitraum_mit_woertern_dazwischen():
    assert mk.zeitraum("von Sonntagabend, 6.12., bis Freitagnachmittag, 11.12.26", HEUTE) == \
        (date(2026, 12, 6), date(2026, 12, 11))
    assert mk.zeitraum("vom 06.12. bis zum 11.12.2026", HEUTE) == (date(2026, 12, 6), date(2026, 12, 11))
    assert mk.zeitraum("06.12.–11.12.2026", HEUTE) == (date(2026, 12, 6), date(2026, 12, 11))


def _stand():
    z = SimpleNamespace(id="GS-3.3-114", kurz="3.3-114", haus="3.3", etage="1", flur="")
    return SimpleNamespace(lage=SimpleNamespace(zimmer={z.id: z}))


def test_antwort_mit_zimmer(monkeypatch):
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 3.3 · 1. OG")
    e = mk.erkennen(BETREFF, TEXT, HEUTE)
    sch = [mails.Schritt("zimmer", "Zimmer reservieren: 3.3-114", daten={"zimmer": "GS-3.3-114", "person": "x"})]
    t = mk.antwort_text(e, sch, None, _stand(), "Beispiel, Erika", "Alex")
    assert t.startswith("Hallo Erika Beispiel,")
    assert "für Herrn Probehaus ist vom So 06.12. bis Fr 11.12.2026 Zimmer 3.3-114 (Haus 3.3 · 1. OG) bereitgestellt." in t
    assert "Essensmarken liegen zur Anreise bereit" in t and t.rstrip().endswith("Alex")


def test_antwort_ohne_zimmer_und_abgewaehlt(monkeypatch):
    e = mk.erkennen(BETREFF, TEXT, HEUTE)
    sch = [mails.Schritt("zimmer", "Zimmer reservieren: 3.3-114", an=False, daten={"zimmer": "GS-3.3-114"})]
    t = mk.antwort_text(e, sch, None, _stand(), "Erika Beispiel <erika@example.org>")
    assert t.startswith("Hallo Erika Beispiel,") and "das Zimmer teilen wir Ihnen noch mit" in t


def test_mailfenster_hat_erkennen():
    src = (Path(mk.__file__).parent / "outlook_kern.py").read_text(encoding="utf-8")
    assert "Erkennen & übernehmen" in src and "mail_erkennen(" in src and "antwort_text(" in src
    a = (Path(mk.__file__).parent / "seite_assistenz.py").read_text(encoding="utf-8")
    assert "async def mail_erkennen(a, box, betreff, absender, text, nach=None)" in a
