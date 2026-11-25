"""1.61: KI-Mail-Erkennung (lokal, standardmäßig aus) – Prüfen und Zusammenführen sind rein und ohne Modell testbar."""

from datetime import date

from belegung import mails

from modern import ki_erkennung as ke

HEUTE = date(2026, 11, 25)
MASSN = ["Umschulung Kauffrau Büromanagement", "BvB Reha", "Erprobung"]


def _regel(**kw):
    e = mails.Erkannt(art=kw.pop("art", "unklar"))
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def test_aus_ist_standard(monkeypatch):
    from belegung import speicher

    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki": {"backend": "lokal"}})
    assert ke.an() is False
    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki_mail": {"an": True}, "ki": {"backend": "claude"}})
    assert ke.an() is False, "Mit Cloud-KI bleibt die Mail-Erkennung aus"
    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki_mail": {"an": True}, "ki": {"backend": "lokal"}})
    assert ke.an() is True


def test_json_aus_codeblock():
    assert ke._json('```json\n{"art": "storno"}\n```') == {"art": "storno"}


def test_zusammenfuehren_fuellt_und_prueft():
    r = _regel(art="unklar", unsicher=["Keine Person erkannt – bitte Namen eintragen.",
                                       "Art der Mail nicht erkannt – bitte auswählen."])
    ki = {"art": "anmeldung", "nachname": "Beispiel", "vorname": "Erika", "geschlecht": "w",
          "von": "2026-12-01", "bis": "2027-05-31", "massnahme": "umschulung kauffrau büromanagement",
          "einzelzimmer": True, "zusammenfassung": "Zimmer ab 1.12. bereitstellen", "unsicher": []}
    e = ke.zusammenfuehren(r, ki, HEUTE, MASSN)
    assert (e.art, e.name, e.geschlecht) == ("anmeldung", "Beispiel, Erika", "w")
    assert (e.von, e.bis) == (date(2026, 12, 1), date(2027, 5, 31))
    assert e.massnahme == "Umschulung Kauffrau Büromanagement"
    assert e.einzelzimmer is True and e.quelle == "KI (lokal)"
    assert not any("Keine Person" in u or "Art der Mail" in u for u in e.unsicher)


def test_unplausibles_wird_verworfen():
    r = _regel(art="anmeldung", von=date(2026, 12, 1), bis=date(2026, 12, 20))
    ki = {"art": "anmeldung", "von": "2019-01-01", "bis": "kein Datum", "nachname": "12345"}
    e = ke.zusammenfuehren(r, ki, HEUTE, MASSN)
    assert e.von == date(2026, 12, 1), "Regel-Datum bleibt"
    assert e.name in ("", None)
    assert any("unplausibel" in u for u in e.unsicher)


def test_widerspruch_wird_gemeldet():
    r = _regel(art="storno", name="Beispiel, Erika", von=date(2026, 12, 1))
    e = ke.zusammenfuehren(r, {"art": "abbruch", "nachname": "Musterhoff", "von": "2026-12-02"}, HEUTE, MASSN)
    text = " ".join(e.unsicher)
    assert "uneins bei der Art" in text and "Name:" in text and "Beginn:" in text


def test_unbekannte_massnahme_hinweis():
    e = ke.zusammenfuehren(_regel(art="anmeldung"), {"art": "anmeldung", "massnahme": "Schweißkurs"}, HEUTE, MASSN)
    assert e.massnahme == "Schweißkurs" and any("Anreiseliste" in u for u in e.unsicher)


def test_prompt_mit_datum_und_beispielen():
    b = [{"betreff": "Absage", "text": "Erika Beispiel kommt nicht", "ergebnis": {"art": "storno"}}]
    m = ke.prompt("Neue Anmeldung", "Text", HEUTE, MASSN, b)
    assert "Mittwoch, 25.11.2026" in m[0]["content"] and "BvB Reha" in m[0]["content"]
    assert [x["role"] for x in m] == ["system", "user", "assistant", "user"]


def test_aehnliche_beispiele():
    bs = [{"betreff": "Stornierung Zimmer", "text": "Absage der Unterbringung für Probehaus"},
          {"betreff": "Heizung defekt", "text": "Wasser läuft"}]
    t = ke.aehnliche("Stornierung", "Absage der Unterbringung", bs)
    assert t and t[0]["betreff"] == "Stornierung Zimmer"


def test_als_formular_rundreise():
    e = _regel(art="gast", name="Beispiel, Erika", von=date(2026, 12, 1), bis=date(2026, 12, 3))
    f = ke.als_formular(e)
    assert f["nachname"] == "Beispiel" and f["von"] == "2026-12-01"
    e2 = ke.zusammenfuehren(_regel(art="unklar"), f, HEUTE, [])
    assert (e2.art, e2.name, e2.von, e2.bis) == ("gast", "Beispiel, Erika", e.von, e.bis)


def test_fragen_mit_nachgebildetem_modell(monkeypatch):
    import pytest

    from belegung import speicher
    from belegung.assistent import llm

    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki": {"backend": "lokal"}})
    gesendet = {}

    def post(self, payload):
        gesendet.update(payload)
        return {"choices": [{"message": {"content": '```json\n{"art": "storno", "nachname": "Beispiel"}\n```'}}]}
    monkeypatch.setattr(llm.LokalBackend, "_post", post)
    d = ke.fragen("Absage", "Erika Beispiel kommt nicht", HEUTE, MASSN, beispiele=[])
    assert d == {"art": "storno", "nachname": "Beispiel"}
    assert gesendet["temperature"] == 0 and gesendet["response_format"] == {"type": "json_object"}

    def kaputt(self, payload):
        raise llm.KIFehler("nicht erreichbar")
    monkeypatch.setattr(llm.LokalBackend, "_post", kaputt)
    with pytest.raises(ValueError, match="nicht erreichbar"):
        ke.fragen("Absage", "Text", HEUTE, MASSN, beispiele=[])
    monkeypatch.setattr(speicher, "einstellungen", lambda: {"ki": {"backend": "claude"}})
    with pytest.raises(ValueError, match="lokalen Modell"):
        ke.fragen("Absage", "Text", HEUTE, MASSN, beispiele=[])
