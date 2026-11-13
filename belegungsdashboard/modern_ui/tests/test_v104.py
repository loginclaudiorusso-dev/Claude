"""1.04 – Mail-Erkennung nachgeschärft, Outlook-Erkennung robuster, Maßnahmen-Auswahl im Menüband.
Nur erfundene Namen, Nummern und Daten."""

from datetime import date, datetime

from belegung import mails

from modern import mail_kern as mk
from modern import outlook_kern as ok
from modern import seite_massnahmen as sm

HEUTE = date(2026, 11, 13)
BETREFF = "AW: Zusätzliche Unterbringung UWTler Muster, Max (123456)"
TEXT = """Hallo Erika,

für UWTler Muster wurde eine zusätzliche Unterbringung vom Ausbildungsbetrieb angefragt.

Die Unterbringung würde dann also nahtlos vom 08.02. – 26.02.2027 erfolgen, Anreise am Sonntag. Vielleicht kann das
bei der Zimmerplanung direkt berücksichtigt werden? Bzw. kann ich den Zeitraum überhaupt bestätigen?

Viele Grüße
Paula Probe"""


def test_beispielmail_wird_vollstaendig_erkannt():
    alt = mails.erkennen(BETREFF, TEXT, HEUTE)
    assert alt.art == "hinweis" and alt.bis is None              # so las es das Hauptprogramm allein
    e = mk.erkennen(BETREFF, TEXT, HEUTE)
    assert e.art == "anmeldung"
    assert e.name == "Muster, Max" and e.tn_id == "123456" and e.massnahme == "UWT"
    assert e.von == date(2027, 2, 7) and e.bis == date(2027, 2, 26)    # Anreise am Sonntag davor
    assert e.bestaetigung
    assert "08.02.–26.02.2027" in e.zusammenfassung and "Anreise So 07.02.2027" in e.zusammenfassung
    assert not any(u.startswith("Zeitraum unvollständig") or u.startswith("Keine Person") for u in e.unsicher)


def test_zeitraeume_mit_strich_und_bis():
    assert mk.zeitraum("vom 8.2.–26.2.27", HEUTE) == (date(2027, 2, 8), date(2027, 2, 26))
    assert mk.zeitraum("08.02. bis 26.02.2027", HEUTE) == (date(2027, 2, 8), date(2027, 2, 26))
    assert mk.zeitraum("28.12. – 03.01.2027", HEUTE) == (date(2026, 12, 28), date(2027, 1, 3))
    assert mk.zeitraum("14.12.2026 - 08.01.2027", HEUTE) == (date(2026, 12, 14), date(2027, 1, 8))
    assert mk.zeitraum("am 08.02.2027", HEUTE) is None


def test_name_aus_betreff_ohne_fuellwoerter():
    assert mk.name_aus("Zusätzliche Unterbringung UWTler Muster, Max (123456)") == "Muster, Max"
    assert mk.name_aus("Hallo, Erika") == ""
    assert mk.name_aus("Anfrage MUSTER, MAX") == "Muster, Max"


def test_andere_mails_bleiben_wie_im_hauptprogramm():
    b, t = "Storno Zimmer", "Herr Max Beispiel sagt ab, Zeitraum 10.03. – 12.03.2027."
    assert mk.erkennen(b, t, HEUTE).art == mails.erkennen(b, t, HEUTE).art == "storno"
    b2, t2 = "Frage", "Wann ist die Hausordnung fertig?"
    assert mk.erkennen(b2, t2, HEUTE) == mails.erkennen(b2, t2, HEUTE)


# ---- Outlook: welche Mail ist offen? (ohne Outlook, mit Attrappen) ------------------------------------------------
class _Zeit:
    year, month, day, hour, minute = 2026, 11, 13, 9, 30


class _Mail:
    Class = 43
    ReceivedTime = _Zeit()

    def __init__(self, betreff):
        self.Subject, self.Body, self.SenderName = betreff, "Text", "Erika Muster"


class _Liste:
    def __init__(self, xs):
        self.xs = xs
        self.Count = len(xs)

    def Item(self, i):
        return self.xs[i - 1]


class _Unterhaltung:
    Class = 128

    def GetItems(self):
        return _Liste([_Mail("alt"), _Mail("neu")])


class _Explorer:
    def __init__(self, sel):
        self.Selection = _Liste(sel)


class _Inspector:
    def __init__(self, x):
        self.CurrentItem = x


class _Outlook:
    def __init__(self, aktiv=None, fenster=(), auswahl=()):
        self._a, self.Inspectors = aktiv, _Liste([_Inspector(x) for x in fenster])
        self._e = _Explorer(list(auswahl))
        self.Explorers = _Liste([self._e])

    def ActiveInspector(self):
        return _Inspector(self._a) if self._a else None

    def ActiveExplorer(self):
        return self._e


def test_unterhaltungsansicht_liefert_die_neueste_mail():
    x = ok.kandidaten(_Outlook(auswahl=[_Unterhaltung()]))
    assert ok._als_mail(x[0]).Subject == "neu"


def test_offenes_fenster_vor_markierter_mail():
    ol = _Outlook(fenster=[_Mail("im Fenster")], auswahl=[_Mail("markiert")])
    assert [ok._als_mail(x).Subject for x in ok.kandidaten(ol)][:2] == ["im Fenster", "markiert"]


def test_zeit_auch_ohne_empfangszeit():
    class Entwurf:
        Class = 43
    assert isinstance(ok._zeit(Entwurf()), datetime)


# ---- Maßnahmen-Auswahl im Menüband --------------------------------------------------------------------------------
def test_auswahl_text():
    assert sm.auswahl_text([], 23) == "alle 23"
    assert sm.auswahl_text(["a", "b"], 23) == "2 von 23"
    assert ".m-mn-menue" in sm.CSS
