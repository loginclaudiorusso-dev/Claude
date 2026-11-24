"""Mail-Erkennung nachgeschärft (1.04). Rein, ohne Oberfläche.

Die Erkennung des Hauptprogramms (``belegung.mails.erkennen``) bleibt unverändert; hier wird ihr Ergebnis ergänzt,
wo sie typische Mails des Internatsdiensts nicht ganz versteht:

* **Zeitraum mit Gedankenstrich:** „vom 08.02. – 26.02.2027“, „8.2.–26.2.27“, „08.02. bis 26.02.2027“ → von/bis (das
  Jahr kommt vom Enddatum).
* **„Zusätzliche Unterbringung“, „Internatsplatz“, „Zimmer anfragen“ …** → Art „Anmeldung“ statt „Hinweis“ (sonst
  zählte nur das erste Datum).
* **Name aus dem Betreff:** „UWTler Muster, Max (123456)“ → „Muster, Max“ (bisher nur „für Vorname Nachname“).
* **Gruppe UWT:** „UWT“, „UWTler“, „Umschüler“ → Maßnahme „UWT“.
* **„Anreise am Sonntag“:** liegt der Beginn nicht auf einem Sonntag, zählt der Sonntag davor als Anreise.
* **„… bestätigen?“** gilt als Bitte um Bestätigung.
* **1.41 – Kurzmeldungen der Pforte:** „Schlüssel für Herrn X, der reist heute an“ → X reist heute (bzw. morgen,
  am Mittwoch, am 26.11.) an und braucht Zimmer und Schlüssel. Steht X nicht in der Anreiseliste, wird er als Gast
  (Gästezimmer) vorgeschlagen; „Hospitant“, „Praktikant“, „Besucher“ … werden genannt. Dazu der Schritt
  „Schlüssel bereitlegen“ mit dem Zimmer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from belegung import mails

_G = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
_BEREICH = re.compile(r"(?<![\d.])(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?\s*,?\s*(?:–|—|-|bis)"
                      # 1.57: bis zu zwei Wörter dazwischen – „6.12., bis Freitagnachmittag, 11.12.26“
                      r"(?:\s*,?\s*[A-Za-zÄÖÜäöüß]+\s*,?){0,2}\s*"
                      r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?(?![\d])")
_UNTERBRINGUNG = re.compile(r"unterbringung|internatsplatz|zimmer\s*(?:anfrage|reservier|benötig|gebraucht|buchung)|"
                            r"(?:benötigt|braucht)\s+(?:ein\s+)?zimmer|unterkunft|"
                            # 1.57: „Bitte um Bereitstellung von Zimmer und Essensmarken“, „Zimmer bereitstellen“
                            r"bereitstellung\s+(?:von\s+|eines\s+)?(?:einem\s+)?zimmers?|zimmer\s+(?:\w+\s+)?bereitstell", re.I)
_ESSEN = re.compile(r"essensmarken|verpflegung|mittagessen", re.I)
_ERPROBUNG = re.compile(r"erprobung|hospitation|probewoche|schnupper", re.I)
_UWT = re.compile(r"\bUWT(?:ler(?:in)?)?\b|umsch[üu]l(?:er|erin|ung)", re.I)
_NAME_WORT_NICHT = {"hallo", "liebe", "lieber", "sehr", "guten", "zusätzliche", "zusaetzliche", "unterbringung",
                    "anfrage", "anmeldung", "uwtler", "uwt", "aw", "wg", "re", "fw", "betreff"}
_TAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
_SCHLUESSEL = re.compile(r"schl[üu]e?ssel", re.I)
_ROLLE = re.compile(r"\b(hospitant(?:in)?|hospitation|praktikant(?:in)?|praktikum|besucher(?:in)?|dozent(?:in)?|"
                    r"referent(?:in)?|gutachter(?:in)?|gast)\b", re.I)
_RELATIV = {"heute": 0, "morgen": 1, "übermorgen": 2, "uebermorgen": 2}
_ANREISE_WORT = re.compile(r"\b(reist|reisen|kommt|kommen|anreise|anreisen|eintrifft|eintreffen)\b", re.I)


def anreise_tag(text: str, heute: date) -> date | None:
    """1.41: Anreisetag aus einer Kurzmeldung – „reist heute an“, „kommt morgen“, „Anreise am Mittwoch“, „am 26.11.“.
    Nur, wenn im selben Satz von einer Anreise die Rede ist."""
    for satz in re.split(r"(?<=[!?\n])|(?<=\.)\s+(?=[A-ZÄÖÜ])", text or ""):     # Datum „27.11.“ bleibt ganz
        if not _ANREISE_WORT.search(satz):
            continue
        klein = satz.lower()
        for wort, tage in _RELATIV.items():
            if re.search(rf"\b{wort}\b", klein):
                return heute + timedelta(days=tage)
        for i, wt in enumerate(WOCHENTAGE):
            if re.search(rf"\b{wt.lower()}\b", klein):
                return heute + timedelta(days=(i - heute.weekday()) % 7)
        m = re.search(r"(?<![\d.])(\d{1,2})\.\s*(\d{1,2})\.(\d{2,4})?", satz)
        if m:
            d = mails._jahr(int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None, heute)
            if d:
                return d
    return None


@dataclass
class Anliegen:
    """1.41: Was eine Kurzmeldung will – z. B. Zimmer und Schlüssel für eine heutige Anreise."""
    tag: date
    schluessel: bool
    rolle: str = ""

    def text(self, heute: date) -> str:
        wann = {0: "heute", 1: "morgen"}.get((self.tag - heute).days, "")
        tag = f"{WOCHENTAGE[self.tag.weekday()]}, {self.tag:%d.%m.%Y}"
        braucht = "Zimmer und Schlüssel" if self.schluessel else "ein Zimmer"
        return f"Anreise {wann + ' ' if wann else ''}({tag}) – braucht {braucht}" + (f" · {self.rolle}" if self.rolle else "")


def anliegen(betreff: str, text: str, heute: date) -> Anliegen | None:
    alles = f"{_bereinigt(betreff)}\n{mails._koerper(text or '')}"
    tag = anreise_tag(alles, heute)
    if tag is None or tag < heute:
        return None
    schluessel = bool(_SCHLUESSEL.search(alles))
    if not schluessel and not _UNTERBRINGUNG.search(alles):
        return None
    r = _ROLLE.search(alles)
    return Anliegen(tag, schluessel, r.group(1).capitalize() if r else "")


def _bereinigt(betreff: str) -> str:
    return re.sub(r"^\s*((AW|WG|RE|FW|Fwd?)\s*:\s*)+", "", betreff or "", flags=re.I)


def zeitraum(text: str, heute: date) -> tuple[date, date] | None:
    """Erster Bereich „TT.MM.(JJ) – TT.MM.(JJ)“ im Text; Jahr vom Enddatum, sonst wie im Hauptprogramm ergänzt."""
    for m in _BEREICH.finditer(text or ""):
        j1 = int(m.group(3)) if m.group(3) else None
        j2 = int(m.group(6)) if m.group(6) else None
        bis = mails._jahr(int(m.group(4)), int(m.group(5)), j2 if j2 is not None else j1, heute)
        if not bis:
            continue
        von = mails._jahr(int(m.group(1)), int(m.group(2)), j1 if j1 is not None else bis.year, heute)
        if von and von > bis and j1 is None:
            von = mails._jahr(int(m.group(1)), int(m.group(2)), bis.year - 1, heute)
        if von and von <= bis:
            return von, bis
    return None


def name_aus(text: str) -> str:
    """„Nachname, Vorname“ irgendwo im Text (z. B. Betreff „UWTler Muster, Max (123456)“)."""
    for m in re.finditer(rf"({_G}),\s*({_G})\b", text or ""):
        n, v = m.group(1), m.group(2)
        if n.lower() in _NAME_WORT_NICHT or v.lower() in _NAME_WORT_NICHT or n.lower() in mails._KEIN_NAME:
            continue
        titel = lambda w: w if not w.isupper() else w.capitalize()     # noqa: E731
        return f"{titel(n)}, {titel(v)}"
    return ""


def erkennen(betreff: str, text: str, heute: date | None = None):
    heute = heute or date.today()
    text, betreff = einheitlich(text), einheitlich(betreff)
    e = mails.erkennen(betreff, text, heute)
    b = _bereinigt(betreff)
    koerper = mails._koerper(text or "")
    alles = f"{b}\n{koerper}"
    klein = alles.lower()
    neu = {}
    unterbringung = bool(_UNTERBRINGUNG.search(alles))
    if e.art in ("hinweis", "unklar") and unterbringung:
        neu["art"] = "anmeldung"
    art = neu.get("art", e.art)
    if not e.name:
        n = name_aus(b) or name_aus(koerper)
        if n:
            neu["name"] = n
    uwt = bool(_UWT.search(alles))
    if uwt and not e.massnahme:
        neu["massnahme"] = "UWT"
    von, bis = e.von, e.bis
    if art in ("anmeldung", "gast", "storno"):
        zr = zeitraum(alles, heute)
        if zr and (bis is None or von is None or (von, bis) != zr):
            if bis is None or von is None or not (zr[0] <= von <= bis <= zr[1]):
                von, bis = zr
    anreise_so = bool(re.search(r"anreise\s+(?:am\s+)?sonntag", klein))
    beginn = von
    if von and anreise_so and von.weekday() != 6:
        von = von - timedelta(days=von.weekday() + 1)       # der Sonntag davor
    if (von, bis) != (e.von, e.bis):
        neu["von"], neu["bis"] = von, bis
    if not e.bestaetigung and re.search(r"bestätigen\b|bestaetigen\b", klein):
        neu["bestaetigung"] = True
    al = anliegen(betreff, text, heute) if neu.get("art", e.art) in ("hinweis", "unklar") else None
    if al is not None:                                # 1.41: „Schlüssel für X, reist heute an“ → Zimmer für die Anreise
        neu.update(art="gast", von=al.tag, bis=(e.bis if e.bis and e.bis > al.tag else al.tag + timedelta(days=1)))
    if not neu:
        return e
    e2 = replace(e, **neu)
    if al is not None:
        e2.massnahme = e2.massnahme or "Gast Gästehaus"
        e2.zusammenfassung = al.text(heute)
        e2.unsicher = [x for x in e2.unsicher if not x.startswith(("Art der Mail", "Zeitraum"))]
        if not (e.bis and e.bis > al.tag):
            e2.unsicher.append("Abreise steht nicht in der Mail – eine Nacht angenommen, bitte prüfen.")
        e2.unsicher.append("Steht die Person nicht in der Anreiseliste, wird sie als Gast angelegt (Gästezimmer).")
        e2.anliegen = al                              # für den Schritt „Schlüssel bereitlegen“
        return e2
    # Zusammenfassung neu, wenn sich Art oder Zeitraum geändert haben
    if "art" in neu or "von" in neu:
        teile = []
        if art == "anmeldung":
            was = "Zusätzliche Unterbringung" if re.search(r"zusätzlich|zusaetzlich", klein) else "Unterbringung"
            teile.append(was + (" (UWT)" if uwt else ""))
            if beginn and bis:
                teile[-1] += f" {beginn:%d.%m.}–{bis:%d.%m.%Y}"
            if anreise_so and von:
                teile.append(f"Anreise {_TAGE[von.weekday()]} {von:%d.%m.%Y}")
            if re.search(r"nahtlos|anschließend\b|direkt\s+im\s+anschluss", klein):
                teile.append("nahtlos im Anschluss")
            if _ERPROBUNG.search(alles):
                teile.append("Erprobung/Hospitation")
            if _ESSEN.search(alles):
                teile.append("Essensmarken gewünscht")
        if e2.bestaetigung:
            teile.append("Bestätigung erbeten")
        if e2.kostenuebernahme:
            teile.append("Kostenübernahme folgt")
        e2.zusammenfassung = " · ".join(teile) or e.zusammenfassung
    # „unsicher“ neu bewerten
    u = [x for x in e.unsicher if not (x.startswith("Keine Person") and (e2.name or e2.tn_id))
         and not (x.startswith("Zeitraum unvollständig") and e2.von and e2.bis)
         and not (x.startswith("Art der Mail") and e2.art != "unklar")]
    if e2.art in ("gast", "anmeldung") and not (e2.von and e2.bis) and not any(x.startswith("Zeitraum") for x in u):
        u.append("Zeitraum unvollständig – bitte Anreise und Abreise prüfen.")
    if anreise_so and beginn and von != beginn:
        u.append(f"Anreise am Sonntag: Zimmer ab {von:%d.%m.%Y} eingeplant (Unterbringung ab {beginn:%d.%m.}) – bitte prüfen.")
    e2.unsicher = u
    return e2


# ---- 1.09: mehrere Gästehaus-Vormerkungen in einer Mail ---------------------------------------------------------------
# Typisch vom Kundenmanagement: je Zeile „Hr. Vorname NACHNAME, Zusatz <Tab> 2 DZ <Tab> 04. - 06.12.2026“, davor ein Satz,
# wer fest ist („… und … sind fix“) und wer sich noch meldet. Die Erkennung des Hauptprogramms kennt nur EINE Person je
# Mail – hier wird jede Zeile eine eigene Buchung.

_ZIMMER = re.compile(r"(\d+)\s*(EZ|DZ|Einzelzimmer|Doppelzimmer)\b", re.I)
_GAESTE = re.compile(r"(\d+)\s*(?:[-–]\s*(\d+)\s*)?(?:Gäste|Gaeste|Personen|Pers\.)", re.I)
_ANREDE = re.compile(r"^\s*(Herrn?|Hr\.?|Frau|Fr\.?)\s+", re.I)
_FIX = re.compile(r"\b(fix|fest|bestätigt|verbindlich|zugesagt)\b", re.I)
_OFFEN = re.compile(r"melde[nt]?\s+sich\s+noch|noch\s+offen|vorläufig|unverbindlich|nicht\s+bestätigt|"
                    r"steh(?:t|en)\s+noch\s+nicht\s+fest|unter\s+vorbehalt", re.I)


@dataclass
class Buchung:
    name: str                         # „Nachname, Vorname“ bzw. nur Nachname
    zusatz: str                       # Firma/Bereich/Anschrift aus der Zeile
    zimmer: int                       # so viele Zimmer werden reserviert
    art: str                          # „EZ“ | „DZ“ | „EZ o. DZ“
    von: date
    bis: date
    gaeste: tuple[int, int] | None = None   # „Zimmer für 5 - 6 Gäste“
    status: str = "offen"             # fix | offen (meldet sich noch / vorgemerkt)
    hinweise: list[str] = field(default_factory=list)
    geschlecht: str = ""

    @property
    def nachname(self) -> str:
        return self.name.split(",")[0].strip()

    @property
    def text(self) -> str:
        z = f"{self.zimmer} {self.art}" if self.gaeste is None else \
            f"{self.zimmer} Zimmer ({self.art}) für {self.gaeste[0]}{'–' + str(self.gaeste[1]) if self.gaeste[1] != self.gaeste[0] else ''} Gäste"
        return (f"{self.name}" + (f" · {self.zusatz}" if self.zusatz else "") + f" · {z} · {self.von:%d.%m.}–{self.bis:%d.%m.%Y}"
                + (" · fest" if self.status == "fix" else " · vorgemerkt, Bestätigung offen"))


def _name_zeile(teil: str) -> tuple[str, str]:
    """„Hr. Max MUSTER“ → („Muster, Max“, „m“); „René HOPPE“ → („Hoppe, René“, „“); „Hr. Probe“ → („Probe“, „m“)."""
    g = ""
    m = _ANREDE.match(teil)
    if m:
        g = "w" if m.group(1).lower().startswith("fr") else "m"
        teil = teil[m.end():]
    woerter = [w for w in re.split(r"\s+", teil.strip()) if w]
    if not woerter:
        return "", g
    titel = lambda w: w if not w.isupper() else w.capitalize()      # noqa: E731
    gross = [w for w in woerter if w.isupper() and len(w) > 1]
    if gross:                                                       # NACHNAME in Großbuchstaben
        nach = gross[-1]
        vor = " ".join(titel(w) for w in woerter if w is not nach)
        return (f"{titel(nach)}, {vor}" if vor else titel(nach)), g
    if len(woerter) == 1:
        return titel(woerter[0]), g
    return f"{titel(woerter[-1])}, {' '.join(woerter[:-1])}", g


def _zellen_zusammenfuegen(koerper: str, heute: date) -> str:
    """Tabelle aus Outlook: jede Zelle in einer eigenen Zeile, oft mit Leerzeilen dazwischen. 1.10: Zu jeder kurzen
    Zeile mit Zeitraum werden die Zellen davor gesucht – Zimmerangabe und Name (Leerzeilen zählen nicht) – und zu EINER
    Zeile mit Tabs zusammengefügt. Alles andere bleibt Begleittext."""
    zeilen = [z.strip() for z in koerper.splitlines() if z.strip()]
    benutzt: set[int] = set()
    zeilen_neu: dict[int, str] = {}
    for i, z in enumerate(zeilen):
        if len(z) > 60 or len(mails.daten(z, heute)) < 2:
            continue
        zellen = [z]
        k = i - 1
        if k >= 0 and k not in benutzt and (_ZIMMER.search(zeilen[k]) or _GAESTE.search(zeilen[k])
                                           or re.search(r"\b(EZ|DZ|Zimmer)\b", zeilen[k])) and len(zeilen[k]) <= 80:
            zellen.insert(0, zeilen[k])
            k -= 1
        if k >= 0 and k not in benutzt and len(zeilen[k]) <= 100 and not mails.daten(zeilen[k], heute):
            zellen.insert(0, zeilen[k])
            k -= 1
        if len(zellen) < 3:
            continue
        for x in range(k + 1, i + 1):
            benutzt.add(x)
        zeilen_neu[k + 1] = "\t".join(zellen)
    aus = []
    for i, z in enumerate(zeilen):
        if i in zeilen_neu:
            aus.append(zeilen_neu[i])
        elif i not in benutzt:
            aus.append(z)
    return "\n".join(aus)


def buchungen(betreff: str, text: str, heute: date | None = None) -> list[Buchung]:
    """Alle Zeilen mit Zeitraum und Zimmerangabe als eigene Buchungen; dazu fest/offen aus dem Begleittext."""
    heute = heute or date.today()
    text = einheitlich(text)
    erg = _buchungen(mails._koerper(text), heute)
    if not erg:
        erg = _buchungen(_zellen_zusammenfuegen(mails._koerper(text), heute), heute)
    return erg


_STRICHE = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "–", "\u2013": "–", "\u2014": "–", "\u2015": "–",
                          "\u2212": "-", "\u00a0": " ", "\u202f": " ", "\u2007": " ", "\u200b": "", "\ufeff": "",
                          "\r": ""})


def einheitlich(text: str | None) -> str:
    """1.10: Text aus Outlook vereinheitlichen – geschützte Leerzeichen, besondere Bindestriche, Windows-Zeilenenden."""
    return (text or "").translate(_STRICHE)


def _buchungen(koerper: str, heute: date) -> list[Buchung]:
    erg: list[Buchung] = []
    begleit: list[str] = []
    for zeile in koerper.splitlines():
        if not zeile.strip():
            continue
        daten = [d for _p, d in mails.daten(zeile, heute)]
        zm = list(_ZIMMER.finditer(zeile))
        gm = _GAESTE.search(zeile)
        if len(daten) < 2 or not (zm or gm or re.search(r"\b(EZ|DZ|Zimmer)\b", zeile)):
            begleit.append(zeile)
            continue
        von, bis = daten[0], daten[1]
        if bis < von:
            continue
        teile = [t.strip() for t in re.split(r"\t+|\s{3,}", zeile.strip()) if t.strip()]
        kopf = teile[0] if teile else zeile
        if _ZIMMER.search(kopf) or mails.daten(kopf, heute):         # ohne Tabs: bis zur Zimmer-/Datumsangabe
            kopf = re.split(r"\s\d+\s*(?:EZ|DZ)|Zimmer|\d{1,2}\.\s*[-–]", kopf)[0]
        name_teil, _, zusatz = kopf.partition(",")
        woerter = [w for w in _ANREDE.sub("", name_teil).split() if w]
        # Fließtext ist keine Buchungszeile: Name = 1–4 großgeschriebene Wörter, Zeile kurz oder in Zellen geteilt
        if not woerter or len(woerter) > 4 or not all(w[0].isupper() for w in woerter) \
                or (len(teile) < 2 and len(zeile) > 140):
            begleit.append(zeile)
            continue
        name, g = _name_zeile(name_teil)
        if not name:
            continue
        zusatz = zusatz.strip(" ,")
        if zm:
            anzahl = sum(int(m.group(1)) for m in zm)
            arten = {("EZ" if m.group(2).upper().startswith("E") else "DZ") for m in zm}
            art = " + ".join(sorted(arten)) if len(arten) > 1 else arten.pop()
            gaeste = None
            hinweise = []
        else:
            lo = int(gm.group(1)) if gm else 1
            hi = int(gm.group(2)) if gm and gm.group(2) else lo
            ez, dz = bool(re.search(r"\bEZ\b|Einzel", zeile, re.I)), bool(re.search(r"\bDZ\b|Doppel", zeile, re.I))
            art = "EZ o. DZ" if ez and dz else ("DZ" if dz else "EZ")
            anzahl = hi if art != "DZ" else -(-hi // 2)
            gaeste = (lo, hi)
            hinweise = [f"Zimmerzahl offen ({lo}–{hi} Gäste{', EZ oder DZ' if art == 'EZ o. DZ' else ''}) – "
                        f"{anzahl} Zimmer vorgemerkt, bitte bei der Bestätigung anpassen."]
        erg.append(Buchung(name, zusatz, max(1, anzahl), art, von, bis, gaeste, "offen", hinweise, g))
    if not erg:
        return []
    # fest / meldet sich noch – je Satzteil die genannten Nachnamen
    satz = " ".join(begleit)
    letzter = None
    for teil in re.split(r"[,;.]|\bwobei\b|\baber\b", satz):
        genannt = [b for b in erg if re.search(rf"\b{re.escape(b.nachname)}\b", teil, re.I)]
        if _FIX.search(teil):
            for b in genannt:
                b.status = "fix"
        elif _OFFEN.search(teil):
            for b in genannt:
                b.status = "offen"
        if genannt:
            letzter = genannt[-1]
        if re.search(r"\bletzterer\b|\bletztere\b", teil, re.I) and letzter is not None:
            if re.search(r"kurzfristig|ändert|geändert|visa", satz, re.I):
                letzter.hinweise.append("Kurzfristige Bestätigung oder Änderung möglich (laut Mail).")
    return erg


def erkannt_fuer(b: Buchung, nr: int | None = 0) -> "mails.Erkannt":
    """Eine Buchung (bzw. ihr ``nr``-tes Zimmer) als Erkannt fürs Hauptprogramm (Gästehaus). ``nr=None``: die ganze
    Buchung (z. B. für den Posteingang) – ohne Zimmerzusatz im Namen."""
    name = b.name if b.zimmer == 1 or nr is None else f"{b.name} ({b.art.split()[0]} {nr + 1}/{b.zimmer})"
    notiz = " · ".join(x for x in (f"Gästehaus {b.art}", b.zusatz,
                                    "fest" if b.status == "fix" else "vorgemerkt – Bestätigung offen") if x)
    return mails.Erkannt(art="gast", name=name, von=b.von, bis=b.bis, geschlecht=b.geschlecht,
                         massnahme="Gast Gästehaus", einzelzimmer=b.art == "EZ", zusammenfassung=notiz[:200],
                         bestaetigung=False)


def schritte(liste: list[Buchung], stand, heute: date | None = None) -> list[list]:
    """Je Buchung die Schritte: Person(en) anlegen, Zimmer reservieren (gemeinsam vorgeschlagen, damit sich die
    Buchungen keine Zimmer wegnehmen), bei offenen Vormerkungen eine Wiedervorlage."""
    from belegung import zimmerplan as zp

    heute = heute or date.today()
    personen = []                      # (Buchung-Index, Person)
    for i, b in enumerate(liste):
        for n in range(b.zimmer):
            p = mails.neue_person(erkannt_fuer(b, n))
            if p is not None:
                personen.append((i, p))
    bedarf = zp.bedarf_aus_personen([p for _i, p in personen]) if personen else []
    vorschlaege = zp.vorschlagen(stand.lage, bedarf) if bedarf else []
    zu = {zt.bedarf.schluessel: zt for zt in vorschlaege}
    erg: list[list] = [[] for _ in liste]
    for i, p in personen:
        erg[i].append(mails.Schritt("person_anlegen", f"Gast anlegen: {p.name}, {p.anreise:%d.%m.} – {p.abreise:%d.%m.%Y}",
                                    daten={"person": p.zu_dict()}))
        zt = zu.get(p.schluessel)
        if zt is not None and zt.zimmer is not None:
            erg[i].append(mails.Schritt("zimmer", f"Zimmer reservieren: {zt.zimmer.kurz} ({zt.grund})",
                                        daten={"zimmer": zt.zimmer.id, "person": p.schluessel}))
        else:
            grund = (zt.warnungen[0] if zt is not None and zt.warnungen else "")
            erg[i].append(mails.Schritt("zimmer", f"Kein passendes Zimmer frei – {grund}".rstrip(" –"), an=False,
                                        daten={"zimmer": "", "person": p.schluessel}))
    for i, b in enumerate(liste):
        if b.status != "fix" and personen:
            wv = min(max(heute, b.von - timedelta(days=14)), heute + timedelta(days=7))
            erg[i].append(mails.Schritt("notiz", f"Wiedervorlage {wv:%d.%m.}: Bestätigung von {b.nachname} abwarten",
                                        daten={"text": f"Vormerkung {b.nachname}: Bestätigung abwarten", "wv": wv.isoformat()}))
    return erg


# ---- 1.41: Vorschlag mit „Schlüssel bereitlegen“ ---------------------------------------------------------------------

def vorschlag(e, treffer, stand, heute: date | None = None) -> list:
    """Wie ``mails.vorschlag``, bei einer Kurzmeldung mit Schlüssel zusätzlich „Schlüssel bereitlegen“ (mit Zimmer)."""
    heute = heute or date.today()
    s = mails.vorschlag(e, treffer, stand, heute)
    al = getattr(e, "anliegen", None)
    if al is None or not al.schluessel:
        return s
    zimmer = (treffer.zimmer.removeprefix("GS-") if treffer and treffer.zimmer else "")
    if not zimmer:
        z = next((x for x in s if x.art == "zimmer" and x.daten.get("zimmer")), None)
        zimmer = z.text.split(": ", 1)[-1].split(" (")[0] if z else ""
    wer = treffer.name if treffer else e.name
    tag = f"{_TAGE[al.tag.weekday()]} {al.tag:%d.%m.}"
    s.append(mails.Schritt("aufgabe", f"Schlüssel bereitlegen für {wer}" + (f" – Zimmer {zimmer}" if zimmer else "")
                           + f", Anreise {tag}", daten={"person": treffer.schluessel if treffer else None}))
    return s


# ---- 1.41: Einschätzung durch die KI (Qwen lokal über Ollama oder Claude), nur wenn eingeschaltet ------------------

def ki_an() -> bool:
    from belegung import speicher

    return (speicher.einstellungen().get("ki", {}) or {}).get("backend", "aus") in ("lokal", "claude")


def ki_einschaetzung(betreff: str, text: str, heute: date | None = None) -> str:
    """Kurze Einschätzung der eingestellten KI: Was will die Mail, für wen, wann, welches Zimmer kommt in Frage?
    Die KI darf über ihre Werkzeuge freie Zimmer nachsehen. Fehler → Text mit dem Grund (kein Absturz)."""
    from belegung import speicher
    from belegung.assistent.llm import Einstellungen, backend_erstellen

    from . import auswertung_kern as ak

    heute = heute or date.today()
    backend = backend_erstellen(Einstellungen.aus_dict(speicher.einstellungen().get("ki", {})))
    if backend is None:
        return ""
    ds, fehler = ak.datenstand()
    if ds is None:
        return f"KI: {fehler or 'Datenstand fehlt'}"
    frage = (f"Heute ist {WOCHENTAGE[heute.weekday()]}, der {heute:%d.%m.%Y}. Du hilfst dem Internatsdienst. Lies diese "
             "Mail und sage in höchstens drei kurzen Sätzen: was zu tun ist, für wen, ab wann und bis wann (falls "
             "genannt), und ob ein Zimmer gebraucht wird. Wenn ja, nenne ein bis zwei freie, passende Zimmer (Gäste und "
             "Hospitanten bevorzugt ins Gästezimmer). Erfinde nichts; was fehlt, nenne als offene Frage.\n\n"
             f"Betreff: {betreff}\n\n{mails._koerper(text or '')[:3000]}")
    try:
        return backend.antworte(frage, [], ds, heute).strip()
    except Exception as exc:                          # noqa: BLE001 – Komfort; die Regeln oben gelten trotzdem
        return f"KI nicht erreichbar: {exc}"


# ---- 1.57: Antwort an den Absender mit Zimmer und Zeitraum --------------------------------------------------------

def _anrede_absender(absender: str) -> str:
    """„Beispiel, Erika“ / „Erika Beispiel <…>“ → „Erika Beispiel“ (ohne Herr/Frau – das Geschlecht steht nicht
    sicher in der Mail)."""
    a = re.sub(r"<[^>]*>|\S+@\S+", "", absender or "").strip().strip('"')
    if "," in a:
        n, v = [t.strip() for t in a.split(",", 1)]
        a = f"{v} {n}".strip()
    return a


def antwort_text(e, schritte: list, treffer, stand, absender: str = "", unterschrift: str = "") -> str:
    """Antwort-Entwurf nach dem Umsetzen: für wen, welcher Zeitraum, welches Zimmer (mit Lage), ggf. Essensmarken.
    Rein – das Zimmer kommt aus dem angehakten Schritt „Zimmer reservieren“, sonst aus der gefundenen Buchung."""
    zid = next((s.daten.get("zimmer") for s in schritte if s.art == "zimmer" and s.an and s.daten.get("zimmer")), "")
    if not zid and treffer is not None and getattr(treffer, "zimmer", ""):
        zid = treffer.zimmer
    z = stand.lage.zimmer.get(zid) if (zid and stand is not None) else None
    zimmer = (f"Zimmer {z.kurz} ({zp_flur(z)})" if z is not None else f"Zimmer {zid.removeprefix('GS-')}") if zid else ""
    name = (treffer.name if treffer is not None and getattr(treffer, "name", "") else e.name) or ""
    if "," in name:
        n, v = [t.strip() for t in name.split(",", 1)]
        name = n if e.geschlecht in ("m", "w") else f"{v} {n}"
    wer = {"m": f"Herrn {name}", "w": f"Frau {name}"}.get(e.geschlecht, name) if name else "die angefragte Person"
    zeit = ""
    if e.von and e.bis:
        zeit = f" vom {_TAGE[e.von.weekday()]} {e.von:%d.%m.} bis {_TAGE[e.bis.weekday()]} {e.bis:%d.%m.%Y}"
    elif e.von:
        zeit = f" ab {_TAGE[e.von.weekday()]} {e.von:%d.%m.%Y}"
    gruss = _anrede_absender(absender)
    zeilen = [f"Hallo {gruss}," if gruss else "Hallo,", ""]
    if zimmer:
        zeilen.append(f"für {wer} ist{zeit} {zimmer} bereitgestellt.")
    else:
        zeilen.append(f"wir haben die Anfrage für {wer}{zeit} erhalten – das Zimmer teilen wir Ihnen noch mit.")
    if (e.zusammenfassung or "").find("Essensmarken") >= 0:
        zeilen.append("Die Essensmarken liegen zur Anreise bereit.")
    zeilen.append("Den Schlüssel gibt es bei der Anreise im Internat.")
    zeilen += ["", "Viele Grüße", unterschrift or ""]
    return "\n".join(zeilen).rstrip() + "\n"


def zp_flur(z) -> str:
    from belegung import zimmerplan as zp

    return zp.flur_text(z)
