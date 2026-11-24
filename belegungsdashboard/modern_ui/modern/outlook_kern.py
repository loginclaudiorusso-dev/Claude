"""Outlook-Vorschau auf „Heute“: die neuesten Mails eines Ordners (z. B. des Postfachs „Internatsdienst“) – nur lesen.

Zugriff wie bei Erinnerungen und Tagesbriefing: lokal über das klassische Outlook (Windows, pywin32/COM). Es wird
nichts gesendet, verschoben, gelöscht oder als gelesen markiert; Outlook wird nicht gestartet, wenn es nicht läuft.
1.02: Eine Mail (oder den ganzen Ordner) per Klick **in Outlook öffnen** – Outlook zeigt sie in seinem eigenen
Fenster; ob sie dann als gelesen gilt, regelt Outlook wie bei jedem Öffnen dort.
Keine Cloud, kein Server, kein OAuth. Ohne eingestellten Ordner ist die Vorschau aus und zeigt keine Inhalte.
1.47: Im Cockpit-Postfach „Nur Zimmer-Mails“ (Standard, je Person umschaltbar): nur Mails mit Zimmerbezug, nach festen
Stichwörtern in Betreff und Text (``zimmerbezug``).

Ordner-Angabe (Einstellungen): ``Internatsdienst`` = Posteingang des Postfachs „Internatsdienst“,
``Internatsdienst/Posteingang/Anreisen`` = Unterordner, leer = aus. Das neue Outlook (ohne COM) wird nicht unterstützt.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime

from belegung import speicher

EINSTELLUNG = "modern_outlook_vorschau"
ANZAHL = 6
NEU_LADEN_S = 120
_ZWISCHEN: dict = {"zeit": 0.0, "pfad": None, "erg": ([], "")}


@dataclass
class Mail:
    zeit: datetime
    betreff: str
    absender: str
    ungelesen: bool
    eintrag: str = ""            # 1.02: Outlook-EntryID – zum Öffnen in Outlook
    ablage: str = ""             # StoreID des Postfachs (freigegebene Postfächer)
    bezug: str = ""              # 1.47: warum die Mail mit Zimmern zu tun hat („Zimmer 2-101“, „Schlüssel“ …), "" = nicht
    adresse: str = ""            # 1.54: Absenderadresse (für „Absender immer/nie zeigen“)

    @property
    def wann(self) -> str:
        return f"{self.zeit:%H:%M}" if self.zeit.date() == date.today() else f"{self.zeit:%d.%m.}"


# ---- 1.47: nur Mails, die etwas mit Zimmern zu tun haben ----------------------------------------------------------
# Feste Regeln (Stichwörter), keine KI: lieber eine Mail zu viel als eine zu wenig. Reihenfolge = Vorrang der Begründung.

BEZUG = [
    ("Zimmer", re.compile(r"\b(?:zimmer|zi\.?|raum|appartement|apartment|app\.)\s*(?:nr\.?\s*)?[a-z]?\d{1,2}[-./ ]?\d{2,4}\b"
                          r"|\b\d(?:\.\d)?-\d{3,4}\b", re.I)),
    ("Schlüssel", re.compile(r"schl[üu]ssel|transponder|schlie(?:ß|ss)(?:anlage|zylinder)|zylinder|ausgesperrt|"
                             r"chipkarte|zugangskarte", re.I)),
    ("Defekt", re.compile(r"defekt|kaputt|mangel|m[äa]ngel|reparatur|heizung|fenster|rollo|jalousie|dusche|toilette|"
                          r"\bwc\b|waschbecken|verstopf|tropf|undicht|schimmel|wasserschaden|lampe|licht|steckdose|"
                          r"hausmeister|facility|\bfm\b|matratze|k[üu]hlschrank|wlan|internet|t[üu]r\b|schrank", re.I)),
    ("Anreise", re.compile(r"anreise|anreisen|ankunft|anreist|einzug|zimmerbuchung|unterbringung|unterkunft|"
                           r"[üu]bernachtung|hospitant|g[äa]stezimmer|\bgast\b|g[äa]ste|check-?in|bezieht|"
                           r"wohnheim|internatsplatz|unterkunft", re.I)),
    ("Abreise", re.compile(r"abreise|abreisen|auszug|zieht aus|ausziehen|vorzeitig|abbruch|nichtanreise|storn|"
                           r"check-?out|abmeldung|abgemeldet|beendet die ma(?:ß|ss)nahme", re.I)),
    ("Belegung", re.compile(r"belegung|zimmer|umzug|umziehen|\bbett(?:en)?\b|mietvertrag|\bmieter|kaution|"
                            r"einzelzimmer|doppelzimmer|allergiker|tier\b|hund\b|katze", re.I)),
    ("Reinigung", re.compile(r"reinigung|bettw[äa]sche|endreinigung|sauber|putz|w[äa]sche|waschmaschine|trockner|"
                             r"zimmerkontrolle|zimmerabnahme|[üu]bergabe", re.I)),
]


@dataclass
class Kontext:
    """1.54: was das Programm kennt – Zimmernummern des Standorts und Namen der Bewohner/Anreisenden."""
    zimmer: re.Pattern | None = None
    namen: re.Pattern | None = None


def _trenner(kurz: str) -> str:
    # „2-101“ auch als „2 101“, „2.101“, „2/101“; „3.2-105“ auch als „3.2 105“
    teile = re.split(r"[-./ ]", kurz)
    return r"[-./ ]?".join(re.escape(t) for t in teile if t)


def kontext_bauen(zimmer_kurz: list[str], namen: list[str]) -> Kontext:
    zs = sorted({k for k in zimmer_kurz if k and any(c.isdigit() for c in k)}, key=len, reverse=True)
    nn = sorted({n.strip() for n in namen if len(n.strip()) >= 4}, key=len, reverse=True)
    return Kontext(re.compile(r"(?<![\w.])(?:" + "|".join(_trenner(k) for k in zs) + r")(?![\w])") if zs else None,
                   re.compile(r"\b(?:" + "|".join(re.escape(n) for n in nn) + r")\b") if nn else None)


def kontext_laden(tage: int = 60) -> Kontext:
    """Zimmer des aktiven Standorts und Nachnamen aller, die gerade da sind oder in ``tage`` Tagen kommen/gehen."""
    from datetime import timedelta

    from belegung import zimmerplan as zp

    stand = zp.laden()
    heute = date.today()
    namen = []
    for bs in stand.lage.belegungen.values():
        for b in bs:
            if b.art in ("belegt", "geplant") and b.name and b.bis >= heute - timedelta(days=7) and \
                    b.von <= heute + timedelta(days=tage) and b.name != zp.PIVOT_NAME:
                namen.append(b.name.split(",")[0].strip())
    for b in stand.bedarf:
        if b.bis >= heute - timedelta(days=7) and b.von <= heute + timedelta(days=tage):
            namen.append(b.name.split(",")[0].strip())
    return kontext_bauen([z.kurz for z in stand.zimmer if z.aktiv], namen)


def zimmerbezug(betreff: str, text: str = "", kontext: Kontext | None = None) -> str:
    """Hat die Mail mit Zimmern zu tun? Begründung („Zimmer 2-101“, „Bewohner: Muster“, „Schlüssel“ …) oder "".
    Betreff zählt zuerst; bekannte Zimmernummern und Namen (``kontext``) vor den Stichwörtern."""
    for quelle in (betreff or "", (text or "")[:6000]):
        if kontext is not None and kontext.zimmer is not None and (m := kontext.zimmer.search(quelle)):
            return f"Zimmer {m.group(0)}"
        for _name, muster in BEZUG[:1]:
            if m := muster.search(quelle):
                nr = re.search(r"[a-z]?\d(?:\.\d)?[-./ ]?\d{2,4}", m.group(0), re.I)
                return f"Zimmer {nr.group(0)}" if nr else "Zimmer"
        if kontext is not None and kontext.namen is not None and (m := kontext.namen.search(quelle)):
            return f"Bewohner: {m.group(0)}"
        for name, muster in BEZUG[1:]:
            if muster.search(quelle):
                return name
    return ""


# ---- 1.54: Absender immer bzw. nie zeigen (für den ganzen Standort) ------------------------------------------------

ABSENDER = "postfach_absender"


def absender_regeln() -> dict[str, list[str]]:
    d = speicher.einstellungen().get(ABSENDER) or {}
    return {k: [str(x).lower() for x in (d.get(k) or [])] for k in ("immer", "nie")} if isinstance(d, dict) else \
        {"immer": [], "nie": []}


def absender_setzen(adresse: str, art: str | None) -> str:
    """``art``: immer | nie | None (Regel entfernen)."""
    adresse = (adresse or "").strip().lower()
    if not adresse:
        raise ValueError("Diese Mail hat keine Absenderadresse.")
    r = absender_regeln()
    for k in r:
        r[k] = [x for x in r[k] if x != adresse]
    if art in r:
        r[art].append(adresse)
    speicher.einstellung_setzen(ABSENDER, r)
    _ZWISCHEN["zeit"] = 0.0
    return {"immer": f"Mails von {adresse} werden immer gezeigt", "nie": f"Mails von {adresse} werden ausgeblendet"} \
        .get(art or "", f"Regel für {adresse} entfernt")


def _regel(adresse: str, regeln: dict) -> str | None:
    a = (adresse or "").lower()
    if not a:
        return None
    return "immer" if a in regeln["immer"] else "nie" if a in regeln["nie"] else None


NUR_ZIMMER = "postfach_nur_zimmer"           # je Person (netz_kern.persoenlich), Standard: an


def nur_zimmer() -> bool:
    from .netz_kern import persoenlich

    return bool(persoenlich(NUR_ZIMMER, True))


def nur_zimmer_setzen(an: bool) -> None:
    from .netz_kern import persoenlich_setzen

    persoenlich_setzen(NUR_ZIMMER, bool(an))
    _ZWISCHEN["zeit"] = 0.0


def ordner() -> str:
    return str(speicher.einstellungen().get(EINSTELLUNG, "") or "").strip()


def einstellen(pfad: str) -> str:
    speicher.einstellung_setzen(EINSTELLUNG, (pfad or "").strip())
    _ZWISCHEN["zeit"] = 0.0
    return f"Outlook-Vorschau: {pfad.strip()}" if pfad.strip() else "Outlook-Vorschau ausgeschaltet"


def _teile(pfad: str) -> list[str]:
    return [t.strip() for t in re.split(r"[\\/]", pfad or "") if t.strip()]


def _unterordner(f, name: str):
    for i in range(1, f.Folders.Count + 1):
        x = f.Folders.Item(i)
        if str(x.Name).lower() == name.lower():
            return x
    raise ValueError(f"Ordner „{name}“ nicht gefunden (in „{f.Name}“).")


def _ordner_finden(ns, pfad: str):
    teile = _teile(pfad)
    wurzel, rest = None, teile
    for i in range(1, ns.Folders.Count + 1):          # Postfächer (eigenes und freigegebene) nach Anzeigename
        f = ns.Folders.Item(i)
        if teile and str(f.Name).lower() == teile[0].lower():
            wurzel, rest = f, teile[1:]
            break
    if wurzel is None:                                # sonst: Unterordner des eigenen Posteingangs
        wurzel = ns.GetDefaultFolder(6)
        rest = [t for t in teile if t.lower() not in ("posteingang", "inbox")]
    elif not rest:                                    # nur das Postfach angegeben → dessen Posteingang
        for name in ("Posteingang", "Inbox"):
            try:
                return _unterordner(wurzel, name)
            except ValueError:
                continue
        return wurzel
    f = wurzel
    for name in rest:
        f = _unterordner(f, name)
    return f


def _outlook(text: str = "Outlook ist nicht geöffnet – die Vorschau erscheint, sobald Outlook läuft."):
    """(pythoncom, laufendes Outlook) – nie starten. Aufrufer meldet COM an und ab."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ValueError("Die Outlook-Vorschau gibt es nur unter Windows mit dem klassischen Outlook.") from exc
    pythoncom.CoInitialize()
    try:
        return pythoncom, win32com.client.GetActiveObject("Outlook.Application")
    except Exception as exc:                          # noqa: BLE001
        pythoncom.CoUninitialize()
        raise ValueError(text) from exc


DURCHSUCHEN = 250                           # 1.47/1.54: so viele neueste Mails werden für „nur Zimmer“ angesehen


def _adresse(m) -> str:
    try:
        if str(getattr(m, "SenderEmailType", "") or "") == "EX":
            ex = m.Sender.GetExchangeUser()
            if ex is not None and ex.PrimarySmtpAddress:
                return str(ex.PrimarySmtpAddress)
        return str(m.SenderEmailAddress or "")
    except Exception:                                 # noqa: BLE001
        return ""


def lesen(pfad: str, anzahl: int = ANZAHL, filtern: bool = False, kontext: Kontext | None = None) -> list[Mail]:
    """Die neuesten Mails des Ordners – nur lesen. ValueError mit verständlichem Text, wenn es nicht geht.
    ``filtern`` (1.47): nur Mails mit Zimmerbezug, dafür bis zu ``DURCHSUCHEN`` Mails ansehen."""
    pythoncom, ol = _outlook()
    try:
        ns = ol.GetNamespace("MAPI")
        f = _ordner_finden(ns, pfad)
        try:
            ablage = str(f.StoreID or "")
        except Exception:                             # noqa: BLE001
            ablage = ""
        items = f.Items
        items.Sort("[ReceivedTime]", True)
        erg: list[Mail] = []
        regeln = absender_regeln() if filtern else {"immer": [], "nie": []}
        m = items.GetFirst()
        gesehen = 0
        while m is not None and len(erg) < anzahl and gesehen < (DURCHSUCHEN if filtern else anzahl * 4):
            gesehen += 1
            try:
                if getattr(m, "Class", 0) == 43:      # olMail
                    betreff = str(m.Subject or "(ohne Betreff)")
                    adresse = _adresse(m) if filtern else ""
                    regel = _regel(adresse, regeln) if filtern else None
                    bezug = "" if regel == "nie" else ("Absender immer" if regel == "immer" else
                                                       zimmerbezug(betreff, "", kontext))
                    if not bezug and filtern and regel != "nie":     # Text nur lesen, wenn der Betreff nichts verrät
                        bezug = zimmerbezug("", str(m.Body or "")[:6000], kontext)
                    if bezug or not filtern:
                        rt = m.ReceivedTime
                        erg.append(Mail(datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute), betreff,
                                        str(m.SenderName or ""), bool(m.UnRead), str(getattr(m, "EntryID", "") or ""),
                                        ablage, bezug, adresse))
            except Exception:                         # noqa: BLE001 – eine kaputte Mail stoppt die Vorschau nicht
                pass
            m = items.GetNext()
        return erg
    finally:
        pythoncom.CoUninitialize()


def oeffnen(eintrag: str, ablage: str = "") -> str:
    """1.02: Die Mail in Outlook im eigenen Fenster zeigen (nur ein laufendes Outlook). Rückgabe: Fehlertext oder ""."""
    if not eintrag:
        return "Diese Mail lässt sich nicht öffnen."
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten, dann noch einmal klicken.")
    except ValueError as exc:
        return str(exc)
    try:
        ns = ol.GetNamespace("MAPI")
        m = ns.GetItemFromID(eintrag, ablage) if ablage else ns.GetItemFromID(eintrag)
        m.Display()
        return ""
    except Exception:                                 # noqa: BLE001
        return "Die Mail wurde in Outlook nicht gefunden (verschoben oder gelöscht?) – bitte neu laden."
    finally:
        pythoncom.CoUninitialize()


# ---- 1.54: Mail im Programm lesen, beantworten, weiterleiten (über das laufende Outlook) ----------------------------

@dataclass
class Inhalt:
    betreff: str
    von: str
    adresse: str
    an: str
    cc: str
    zeit: str
    text: str


def mail_lesen(eintrag: str, ablage: str = "") -> Inhalt:
    """Text und Kopf einer Mail – nur lesen (Outlook markiert sie dabei nicht als gelesen)."""
    pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten, dann noch einmal klicken.")
    try:
        ns = ol.GetNamespace("MAPI")
        try:
            m = ns.GetItemFromID(eintrag, ablage) if ablage else ns.GetItemFromID(eintrag)
        except Exception as exc:                      # noqa: BLE001
            raise ValueError("Die Mail wurde in Outlook nicht gefunden (verschoben oder gelöscht?).") from exc
        rt = m.ReceivedTime
        return Inhalt(str(m.Subject or ""), str(m.SenderName or ""), _adresse(m), str(m.To or ""), str(m.CC or ""),
                      f"{rt.day:02d}.{rt.month:02d}.{rt.year} {rt.hour:02d}:{rt.minute:02d}",
                      str(m.Body or "")[:30000])
    finally:
        pythoncom.CoUninitialize()


def text_davor(html: str, text: str) -> str:
    """Den eigenen Text vor die zitierte Mail setzen (HTML, Zeilenumbrüche bleiben)."""
    from html import escape

    if not (text or "").strip():
        return html
    block = "<div style=\"font-family:Calibri,Arial,sans-serif;font-size:11pt\">" + \
        escape(text.strip()).replace("\n", "<br>") + "</div><br>"
    if re.search(r"<body[^>]*>", html or "", re.I):
        return re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + block, html, count=1, flags=re.I)
    return block + (html or "")


def _antwort(eintrag: str, ablage: str, art: str, text: str, an: str = "", senden: bool = False, von: str = "") -> str:
    """art: antworten | allen | weiterleiten. Rückgabe "" = erledigt, sonst Grund."""
    from . import fm_mail_kern as fk

    if art == "weiterleiten" and not (an or "").strip():
        return "Bitte eine Adresse für die Weiterleitung eintragen."
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten und noch einmal versuchen.")
    except ValueError as exc:
        return str(exc)
    try:
        ns = ol.GetNamespace("MAPI")
        try:
            m = ns.GetItemFromID(eintrag, ablage) if ablage else ns.GetItemFromID(eintrag)
        except Exception:                             # noqa: BLE001
            return "Die Mail wurde in Outlook nicht gefunden (verschoben oder gelöscht?)."
        neu = m.ReplyAll() if art == "allen" else m.Forward() if art == "weiterleiten" else m.Reply()
        if art == "weiterleiten":
            neu.To = an.strip()
        neu.HTMLBody = text_davor(str(neu.HTMLBody or ""), text)
        fk._als_postfach(ol, neu, von)
        if senden:
            neu.Send()
        else:
            neu.Display(False)
        return ""
    except Exception as exc:                          # noqa: BLE001
        return f"Outlook konnte die Mail nicht {'senden' if senden else 'anlegen'}: {exc}"
    finally:
        pythoncom.CoUninitialize()


def ordner_oeffnen(pfad: str | None = None) -> str:
    """1.02: Den eingestellten Ordner (z. B. das Postfach „Internatsdienst“) in einem Outlook-Fenster zeigen."""
    pfad = ordner() if pfad is None else pfad
    if not pfad:
        return "Kein Outlook-Ordner eingestellt."
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten, dann noch einmal klicken.")
    except ValueError as exc:
        return str(exc)
    try:
        _ordner_finden(ol.GetNamespace("MAPI"), pfad).Display()
        return ""
    except ValueError as exc:
        return str(exc)
    except Exception as exc:                          # noqa: BLE001
        return f"Outlook konnte den Ordner nicht zeigen: {exc}"
    finally:
        pythoncom.CoUninitialize()


def vorschau(neu: bool = False, anzahl: int = ANZAHL, filtern: bool = False) -> tuple[list[Mail], str]:
    """(Mails, Fehlertext) – höchstens alle ``NEU_LADEN_S`` Sekunden frisch aus Outlook."""
    pfad = ordner()
    if not pfad:
        return [], ""
    if (not neu and _ZWISCHEN["pfad"] == (pfad, anzahl, filtern)
            and time.monotonic() - _ZWISCHEN["zeit"] < NEU_LADEN_S):
        return _ZWISCHEN["erg"]
    kontext = None
    if filtern:
        try:
            kontext = kontext_laden()                 # 1.54: Zimmernummern und Namen des Standorts
        except Exception:                             # noqa: BLE001 – ohne Kontext: nur Stichwörter
            kontext = None
    try:
        erg = (lesen(pfad, anzahl, filtern, kontext) if kontext is not None else lesen(pfad, anzahl, filtern), "")
    except ValueError as exc:
        erg = ([], str(exc))
    except Exception as exc:                          # noqa: BLE001 – Outlook-Fehler nie bis zur Oberfläche durchreichen
        erg = ([], f"Outlook konnte nicht gelesen werden: {exc}")
    _ZWISCHEN.update(zeit=time.monotonic(), pfad=(pfad, anzahl, filtern), erg=erg)
    return erg


# ---- Oberfläche (Block auf „Heute“) ------------------------------------------------------

def _als_mail(x):
    """Ein Outlook-Element → Mail (oder None). Auch Unterhaltungen (Unterhaltungsansicht) und Elemente ohne
    Empfangszeit (Entwürfe, Berichte) – Hauptsache Betreff und Text."""
    if x is None:
        return None
    try:
        klasse = int(getattr(x, "Class", 0) or 0)
    except Exception:                              # noqa: BLE001
        klasse = 0
    if klasse == 43:                               # olMail
        return x
    try:                                           # Unterhaltungs-Kopf: die neueste Mail daraus
        teile = x.GetItems()
        beste = None
        for i in range(1, teile.Count + 1):
            m = teile.Item(i)
            if int(getattr(m, "Class", 0) or 0) == 43:
                beste = m
        if beste is not None:
            return beste
    except Exception:                              # noqa: BLE001
        pass
    try:
        if getattr(x, "Subject", None) is not None and getattr(x, "Body", None) is not None:
            return x                               # z. B. Besprechungsanfrage, Bericht – Text reicht zum Erkennen
    except Exception:                              # noqa: BLE001
        pass
    return None


def _zeit(m) -> datetime:
    for feld in ("ReceivedTime", "SentOn", "CreationTime"):
        try:
            rt = getattr(m, feld)
            return datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute)
        except Exception:                          # noqa: BLE001
            continue
    return datetime.now().replace(second=0, microsecond=0)


def kandidaten(ol) -> list:
    """Reihenfolge: aktives Mail-Fenster, alle offenen Mail-Fenster (neuestes zuerst), Auswahl im aktiven Explorer,
    Auswahl in allen Explorern."""
    erg: list = []

    def dazu(f):
        try:
            x = f()
        except Exception:                          # noqa: BLE001
            return
        if x is not None:
            erg.append(x)
    dazu(lambda: ol.ActiveInspector().CurrentItem if ol.ActiveInspector() else None)
    try:
        insp = ol.Inspectors
        for i in range(insp.Count, 0, -1):
            dazu(lambda i=i: insp.Item(i).CurrentItem)
    except Exception:                              # noqa: BLE001
        pass

    def auswahl(ex):
        sel = ex.Selection if ex else None
        if sel is not None and sel.Count:
            for i in range(1, sel.Count + 1):
                dazu(lambda i=i: sel.Item(i))
    try:
        auswahl(ol.ActiveExplorer())
    except Exception:                              # noqa: BLE001
        pass
    try:
        exs = ol.Explorers
        for i in range(1, exs.Count + 1):
            try:
                auswahl(exs.Item(i))
            except Exception:                      # noqa: BLE001
                continue
    except Exception:                              # noqa: BLE001
        pass
    return erg


def offene_mail() -> dict | None:
    """0.91/1.04: Die Mail, an der gerade gearbeitet wird – zuerst ein geöffnetes Mail-Fenster, sonst die in Outlook
    markierte (auch in der Unterhaltungsansicht und in freigegebenen Postfächern). Nur ein laufendes klassisches
    Outlook (nie starten), nur lesen. None = keine Mail offen/markiert. ValueError mit verständlichem Text, wenn
    Outlook nicht erreichbar ist (z. B. „neues Outlook“)."""
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet (oder es ist das „neue Outlook“) – bitte den Text "
                                 "einfügen.")
    except ValueError as exc:
        if "nur unter Windows" in str(exc):
            raise ValueError("Outlook ist nur unter Windows mit dem klassischen Outlook erreichbar – bitte den Text "
                             "einfügen.") from exc
        raise
    try:
        for x in kandidaten(ol):
            m = _als_mail(x)
            if m is None:
                continue
            try:
                betreff, absender, text = str(m.Subject or ""), str(getattr(m, "SenderName", "") or ""), str(m.Body or "")
            except Exception:                      # noqa: BLE001
                continue
            if not (betreff or text):
                continue
            return {"betreff": betreff, "absender": absender, "text": text, "zeit": _zeit(m)}
        return None
    finally:
        pythoncom.CoUninitialize()


def block(a, anzahl: int = ANZAHL, postfach: bool = False) -> None:
    """Mail-Block. ``postfach`` (1.02, Seite „Aufgaben“): mehr Mails, Kopf „Postfach“, Platz unter der Aufgabe.
    Klick auf eine Mail öffnet sie in Outlook; „In Outlook“ zeigt den ganzen Ordner."""
    from nicegui import run, ui

    from .ui_bausteine import attr, knopf

    pfad = ordner()
    zustand = {"nur": postfach and nur_zimmer()}

    async def _oeffnen(m: Mail) -> None:
        fehler = await run.io_bound(oeffnen, m.eintrag, m.ablage)
        if fehler:
            a.toast(fehler, fehler=True)

    async def _ordner() -> None:
        fehler = await run.io_bound(ordner_oeffnen)
        if fehler:
            a.toast(fehler, fehler=True)

    with ui.element("section").classes("m-tz-block m-tz-outlook" + (" m-pf-post" if postfach else "")):
        with ui.element("div").classes("m-tz-ab"):
            ui.label(("Postfach" if postfach else "Outlook") + (f" · {pfad}" if pfad else ""))
            if pfad:
                with ui.element("div").classes("m-tz-abk"):
                    if postfach:                      # 1.47: nur Mails mit Zimmerbezug ⇄ alle
                        filt = ui.element("button").classes("m-pf-filter" + (" an" if zustand["nur"] else ""))
                        attr(filt, type="button", title="Nur Mails zeigen, die etwas mit Zimmern zu tun haben "
                             "(Zimmernummer, Schlüssel, Defekt, An-/Abreise, Gäste, Reinigung)")
                        with filt:
                            ui.icon("filter_alt")
                            filt_text = ui.label("Nur Zimmer-Mails" if zustand["nur"] else "Alle Mails")

                        async def _umschalten() -> None:
                            zustand["nur"] = not zustand["nur"]
                            await run.io_bound(nur_zimmer_setzen, zustand["nur"])
                            filt.classes(add="an") if zustand["nur"] else filt.classes(remove="an")
                            filt_text.set_text("Nur Zimmer-Mails" if zustand["nur"] else "Alle Mails")
                            await _laden(True)
                        filt.on("click", _umschalten)
                    knopf("In Outlook", _ordner, "leise", "open_in_new", "Den Ordner in Outlook öffnen")
                    knopf("", lambda: _laden(True), "leise", "refresh", "Neu laden")
        inhalt = ui.element("div").classes("m-tz-mails")
        if not pfad:
            with inhalt:
                ui.label("Die Vorschau ist aus. In den Einstellungen den Outlook-Ordner eintragen (z. B. „Internatsdienst“) – "
                         "dann stehen hier Betreff, Zeit und ungelesen; ein Klick öffnet die Mail in Outlook.").classes(
                    "m-zweite").style("white-space:normal")
                knopf("Einstellen", lambda: a.oeffnen("einstellungen"), "leise", "settings")
            return
        with inhalt:
            ui.label("Lädt …").classes("m-zweite")

    async def _laden(neu: bool = False) -> None:
        erg = await run.io_bound(vorschau, neu, anzahl, zustand["nur"])
        if erg is None:                    # 1.29.1: Programm wird gerade beendet (NiceGUI liefert dann None)
            return
        mails, fehler = erg
        inhalt.clear()
        with inhalt:
            if fehler:
                ui.label(fehler).classes("m-zweite").style("white-space:normal")
                return
            if not mails:
                ui.label(f"Unter den neuesten {DURCHSUCHEN} Mails ist keine mit Zimmerbezug." if zustand["nur"] else
                         "Keine Mails in diesem Ordner.").classes("m-zweite")
                return
            for m in mails:
                z = ui.element("button").classes("m-tz-mail" + (" neu" if m.ungelesen else ""))
                attr(z, title=f"{m.betreff} – lesen und antworten", type="button")
                with z:
                    ui.label(m.wann).classes("m-tz-mzeit")
                    with ui.element("div").classes("m-tz-mtext"):
                        ui.label(m.betreff).classes("m-tz-mbetreff")
                        ui.label(m.absender + (f" · {m.bezug}" if m.bezug and zustand["nur"] else "")).classes("m-zweite")
                    if m.ungelesen:
                        ui.label("ungelesen").classes("m-pille akzent")
                z.on("click", lambda m=m: mail_panel(a, m))       # 1.54: im Programm lesen und antworten
            ungelesen = sum(1 for m in mails if m.ungelesen)
            ui.label(f"Klick öffnet die Mail · {ungelesen} ungelesen unter den neuesten {len(mails)}"
                     + (" mit Zimmerbezug" if zustand["nur"] else "") + f" · Stand {datetime.now():%H:%M}").classes("m-tz-meta")

    ui.timer(0.05, _laden, once=True)


def mail_panel(a, m: Mail) -> None:
    """1.54: Mail rechts lesen; antworten, allen antworten oder weiterleiten – gesendet über Outlook (aus dem
    gemeinsamen Postfach, wenn unter „Mail an FM“ eins eingetragen ist), oder erst in Outlook öffnen."""
    from nicegui import run, ui

    from . import fm_mail_kern as fk
    from .ui_bausteine import knopf

    def bauen():
        ui.label(f"{m.absender} · {m.wann}" + (f" · {m.bezug}" if m.bezug else "")).classes("m-zweite")
        text_box = ui.element("div").classes("m-mail-text")
        with text_box:
            ui.label("Lädt …").classes("m-zweite")

        async def laden():
            try:
                inh = await run.io_bound(mail_lesen, m.eintrag, m.ablage)
            except ValueError as exc:
                text_box.clear()
                with text_box:
                    ui.label(str(exc)).classes("m-zweite m-warn")
                return
            if inh is None:
                return
            m.adresse = m.adresse or inh.adresse
            text_box.clear()
            with text_box:
                ui.label(f"Von: {inh.von} <{inh.adresse}>" if inh.adresse else f"Von: {inh.von}").classes("m-zweite")
                ui.label(f"An: {inh.an}" + (f" · Cc: {inh.cc}" if inh.cc else "")).classes("m-zweite")
                ui.label(inh.text or "(kein Text)").classes("m-ptext").style("white-space:pre-wrap;margin-top:8px")
        ui.timer(0.05, laden, once=True)

        ui.label("Antworten").classes("m-abschnitt")
        art = ui.select({"antworten": "Antworten", "allen": "Allen antworten", "weiterleiten": "Weiterleiten"},
                        value="antworten", label="Art").classes("m-feld").props(
            'dense outlined dark popup-content-class="m-popup"')
        an = ui.input("An (beim Weiterleiten)").classes("m-feld w-full").props("dense outlined dark")
        an.bind_visibility_from(art, "value", lambda v: v == "weiterleiten")
        text = ui.textarea("Ihr Text (steht über der zitierten Mail)").classes("m-feld w-full m-mail-antwort").props(
            "dense outlined dark rows=4")

        def an_fm():
            art.value = "weiterleiten"
            an.value = fk.adresse()
            if not an.value:
                a.toast("Noch keine FM-Adresse gespeichert – unter Übersicht → „Mail an FM“ eintragen.", fehler=True)

        async def los(senden: bool):
            fehler = await run.io_bound(_antwort, m.eintrag, m.ablage, art.value, text.value or "", an.value or "",
                                        senden, fk.absender())
            if fehler:
                a.toast(fehler, fehler=True)
                return
            a.toast("Gesendet über Outlook" if senden else "In Outlook geöffnet – dort prüfen und senden", rueck=False)
            a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Senden", lambda: los(True), "primaer", "send", "Direkt über Outlook senden")
            knopf("In Outlook öffnen", lambda: los(False), "", "open_in_new", "Fertig vorbereitet in Outlook öffnen")
            knopf("An FM", an_fm, "leise", "engineering", "Weiterleiten an die gespeicherte FM-Adresse")
        if fk.absender():
            ui.label(f"Gesendet wird aus dem Postfach {fk.absender()}.").classes("m-zweite")

        ui.label("Filter „Nur Zimmer-Mails“").classes("m-abschnitt")

        async def regel(art_):
            try:
                a.toast(await run.io_bound(absender_setzen, m.adresse, art_), rueck=False)
            except ValueError as exc:
                a.toast(str(exc), fehler=True)

        async def original():
            f = await run.io_bound(oeffnen, m.eintrag, m.ablage)
            if f:
                a.toast(f, fehler=True)
        with ui.element("div").classes("m-paktionen"):
            knopf("Absender immer zeigen", lambda: regel("immer"), "leise", "visibility")
            knopf("Absender nie zeigen", lambda: regel("nie"), "leise", "visibility_off")
            knopf("Regel entfernen", lambda: regel(None), "leise", "close")
        with ui.element("div").classes("m-paktionen"):
            knopf("Original in Outlook", original, "leise", "open_in_new")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel(m.betreff[:60] or "Mail", bauen)
