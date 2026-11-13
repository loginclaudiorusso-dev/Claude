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
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from belegung import mails

_G = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
_BEREICH = re.compile(r"(?<![\d.])(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?\s*(?:–|—|-|bis(?:\s+(?:zum|einschließlich))?)\s*"
                      r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?(?![\d])")
_UNTERBRINGUNG = re.compile(r"unterbringung|internatsplatz|zimmer\s*(?:anfrage|reservier|benötig|gebraucht)|"
                            r"(?:benötigt|braucht)\s+(?:ein\s+)?zimmer|unterkunft", re.I)
_UWT = re.compile(r"\bUWT(?:ler(?:in)?)?\b|umsch[üu]l(?:er|erin|ung)", re.I)
_NAME_WORT_NICHT = {"hallo", "liebe", "lieber", "sehr", "guten", "zusätzliche", "zusaetzliche", "unterbringung",
                    "anfrage", "anmeldung", "uwtler", "uwt", "aw", "wg", "re", "fw", "betreff"}
_TAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


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
    if not neu:
        return e
    e2 = replace(e, **neu)
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
            if re.search(r"nahtlos|anschließend|direkt\s+im\s+anschluss", klein):
                teile.append("nahtlos im Anschluss")
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
    """Tabelle aus Outlook: jede Zelle in einer eigenen Zeile → Zellen bis zum Zeitraum wieder zu EINER Zeile (Tab)."""
    aus, puffer = [], []
    for zeile in koerper.splitlines():
        if not zeile.strip():
            if puffer:
                aus.append("\n".join(puffer))
                puffer = []
            aus.append("")
            continue
        puffer.append(zeile.strip())
        if len(mails.daten(zeile, heute)) >= 2:
            aus.append("\t".join(puffer))
            puffer = []
    if puffer:
        aus.append("\n".join(puffer))
    return "\n".join(aus)


def buchungen(betreff: str, text: str, heute: date | None = None) -> list[Buchung]:
    """Alle Zeilen mit Zeitraum und Zimmerangabe als eigene Buchungen; dazu fest/offen aus dem Begleittext."""
    heute = heute or date.today()
    erg = _buchungen(mails._koerper(text or ""), heute)
    if not erg:
        erg = _buchungen(_zellen_zusammenfuegen(mails._koerper(text or ""), heute), heute)
    return erg


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
