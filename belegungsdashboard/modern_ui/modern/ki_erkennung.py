"""1.61: Mail-Erkennung mit einem lokalen KI-Modell (z. B. Qwen über Ollama) – standardmäßig AUS.

Ablauf
1. Die Regel-Erkennung (``mail_kern.erkennen``) läuft wie bisher.
2. Ist die KI-Erkennung eingeschaltet (Einstellungen → KI, nur mit einem LOKALEN Modell – keine Mail verlässt den PC),
   liest das Modell die Mail und füllt ein festes Formular (JSON): Art, Person, Zeitraum, Maßnahme, Einzelzimmer …
3. Das Programm prüft jede Angabe, bevor sie zählt: Datum lesbar und plausibel, Zeitraum in der richtigen
   Reihenfolge, Art bekannt, Maßnahme in der Anreiseliste. Was nicht passt, fällt auf die Regel-Erkennung zurück
   und steht als Hinweis da. Wo KI und Regeln sich widersprechen, steht das ebenfalls als Hinweis da.
4. Übernommen wird nie automatisch – nur nach Klick auf „Umsetzen“. Dann wird die Mail als Beispiel gemerkt
   (``importe/modern_ki_beispiele.json`` im Standortordner, nicht im Programm) – die drei ähnlichsten Beispiele
   bekommt das Modell beim nächsten Mal mit. So wird es mit der Zeit besser, ohne Training.

Rein bis auf den Aufruf des Modells und das Lesen/Schreiben der Beispieldatei.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date, timedelta

SCHLUESSEL = "ki_mail"                      # Einstellung je Standort: {"an": bool}
BEISPIELE = "importe/modern_ki_beispiele.json"
MAX_BEISPIELE = 200
MAX_TEXT = 4000
ARTEN_KI = {"anmeldung", "gast", "storno", "abbruch", "hinweis", "unklar"}
WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


# ---- Einstellungen ---------------------------------------------------------------------------------------------------

def an() -> bool:
    """Eingeschaltet UND ein lokales Modell eingestellt. Mit Claude (Cloud) bleibt die Mail-Erkennung aus –
    Mails mit Personendaten verlassen den PC nicht."""
    from belegung import speicher

    e = speicher.einstellungen()
    return bool((e.get(SCHLUESSEL) or {}).get("an")) and (e.get("ki") or {}).get("backend") == "lokal"


def setzen(ein: bool) -> str:
    from belegung import speicher

    from .benutzer_kern import admin_pruefen
    from .kern import _schritt

    admin_pruefen("Die KI-Mail-Erkennung schalten")

    _schritt("KI-Mail-Erkennung", lambda: speicher.einstellung_setzen(SCHLUESSEL, {"an": bool(ein)}),
             [speicher.EINSTELLUNGEN])
    return ("KI-Mail-Erkennung eingeschaltet – wirkt nur mit einem lokalen Modell (Einstellungen → KI: „lokales "
            "Modell“)") if ein else "KI-Mail-Erkennung ausgeschaltet – es gilt wieder nur die Regel-Erkennung"


# ---- Anfrage ---------------------------------------------------------------------------------------------------------

FORMULAR = """{
  "art": "anmeldung | gast | storno | abbruch | hinweis | unklar",
  "nachname": "Nachname der betroffenen Person (nicht des Absenders) oder leer",
  "vorname": "Vorname oder leer",
  "geschlecht": "m | w | leer",
  "tn_id": "Teilnehmernummer, falls genannt, sonst leer",
  "von": "JJJJ-MM-TT Anreise bzw. Beginn, sonst leer",
  "bis": "JJJJ-MM-TT Abreise bzw. Ende, sonst leer",
  "massnahme": "Maßnahme/Kurs, wie in der Liste unten, sonst wie in der Mail, sonst leer",
  "einzelzimmer": true | false | null,
  "bestaetigung_erbeten": true | false,
  "kostenuebernahme_folgt": true | false,
  "zusammenfassung": "ein kurzer Satz: was ist zu tun",
  "unsicher": ["was in der Mail fehlt oder unklar ist"]
}"""


def prompt(betreff: str, text: str, heute: date, massnahmen: list[str], beispiele: list[dict]) -> list[dict]:
    """Nachrichten für das Modell – Systemregeln, bis zu drei bestätigte Beispiele, dann die Mail."""
    system = (
        f"Du liest Mails an den Internatsdienst. Heute ist {WOCHENTAGE[heute.weekday()]}, {heute:%d.%m.%Y}. "
        "Fülle NUR dieses JSON-Formular aus, ohne weiteren Text:\n" + FORMULAR + "\n"
        "Regeln: Die betroffene Person ist die, die ein Zimmer braucht, absagt oder abbricht – nie der Absender und "
        "nie die Grußformel. „anmeldung“ = Unterbringung/Zimmer für Teilnehmende oder Umschüler; „gast“ = "
        "Gästehaus/Hospitation/Besuch; „storno“ = Absage vor der Anreise; „abbruch“ = Ende während des Aufenthalts. "
        "Daten ohne Jahr beziehen sich auf das nächste passende Datum ab heute. Erfinde nichts – was nicht in der "
        "Mail steht, bleibt leer und gehört in „unsicher“."
        + (("\nBekannte Maßnahmen: " + ", ".join(massnahmen[:80])) if massnahmen else ""))
    msgs = [{"role": "system", "content": system}]
    for b in beispiele[:3]:
        msgs.append({"role": "user", "content": f"Betreff: {b.get('betreff', '')}\n\n{b.get('text', '')}"})
        msgs.append({"role": "assistant", "content": json.dumps(b.get("ergebnis", {}), ensure_ascii=False)})
    msgs.append({"role": "user", "content": f"Betreff: {betreff}\n\n{(text or '')[:MAX_TEXT]}"})
    return msgs


def _json(text: str) -> dict:
    """Erstes JSON-Objekt aus der Antwort (Modelle setzen gern ```json … ``` darum)."""
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("Die KI hat kein Formular geliefert.")
    d = json.loads(m.group(0))
    if not isinstance(d, dict):
        raise ValueError("Die KI hat kein gültiges Formular geliefert.")
    return d


def fragen(betreff: str, text: str, heute: date | None = None, massnahmen: list[str] | None = None,
           beispiele: list[dict] | None = None) -> dict:
    """Das lokale Modell fragen. Fehler → ValueError mit verständlichem Grund."""
    from belegung import speicher
    from belegung.assistent.llm import Einstellungen, KIFehler, LokalBackend

    e = Einstellungen.aus_dict(speicher.einstellungen().get("ki", {}))
    if e.backend != "lokal":
        raise ValueError("Die KI-Mail-Erkennung arbeitet nur mit einem lokalen Modell (Einstellungen → KI).")
    heute = heute or date.today()
    if beispiele is None:
        beispiele = aehnliche(betreff, text, beispiele_laden())
    b = LokalBackend(e.lokal_url, e.lokal_modell)
    try:
        antwort = b._post({"model": e.lokal_modell, "temperature": 0, "response_format": {"type": "json_object"},
                           "messages": prompt(betreff, text, heute, massnahmen or [], beispiele)})
    except KIFehler as exc:
        raise ValueError(str(exc)) from exc
    try:
        return _json(antwort["choices"][0]["message"].get("content") or "")
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError(f"Antwort der KI nicht lesbar: {exc}") from exc


# ---- Prüfen und Zusammenführen ----------------------------------------------------------------------------------------

def _datum(x) -> date | None:
    if not x or not isinstance(x, str):
        return None
    try:
        return date.fromisoformat(x.strip()[:10])
    except ValueError:
        return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", (s or "").lower())


def massnahme_finden(text: str, massnahmen: list[str]) -> str | None:
    """Maßnahme der KI einer bekannten zuordnen (exakt, dann ohne Leer-/Sonderzeichen, dann enthalten)."""
    if not text:
        return None
    n = _norm(text)
    for m in massnahmen:
        if m.lower() == text.lower() or _norm(m) == n:
            return m
    teil = [m for m in massnahmen if n and (n in _norm(m) or _norm(m) in n) and len(_norm(m)) >= 2]
    return min(teil, key=len) if len(teil) >= 1 else None


def zusammenfuehren(regel, ki: dict, heute: date, massnahmen: list[str] | None = None):
    """Regel-Ergebnis (``mails.Erkannt``) mit dem geprüften KI-Formular zusammenführen. Rückgabe: neues Erkannt mit
    ``quelle = "KI (lokal)"``; jede verworfene oder strittige Angabe steht in ``unsicher``."""
    massnahmen = massnahmen or []
    hinweise: list[str] = []
    neu: dict = {}
    art = str(ki.get("art") or "").strip().lower()
    if art in ARTEN_KI:
        neu["art"] = art
        if regel.art not in ("unklar", "hinweis") and art != regel.art and art not in ("unklar", "hinweis"):
            hinweise.append(f"KI und Regeln uneins bei der Art: KI „{art}“, Regeln „{regel.art}“ – bitte prüfen.")
    nach, vor = str(ki.get("nachname") or "").strip(), str(ki.get("vorname") or "").strip()
    if nach and len(nach) <= 40 and not re.search(r"\d|@", nach):
        neu["name"] = f"{nach}, {vor}" if vor else nach
        r_nach = (regel.name or "").split(",")[0].strip().lower()
        if r_nach and r_nach != nach.lower():
            hinweise.append(f"Name: KI „{neu['name']}“, Regeln „{regel.name}“ – bitte prüfen.")
    if str(ki.get("geschlecht") or "").lower() in ("m", "w"):
        neu["geschlecht"] = str(ki["geschlecht"]).lower()
    tn = str(ki.get("tn_id") or "").strip()
    if tn and re.fullmatch(r"[A-Za-z0-9\-/]{3,20}", tn):
        neu["tn_id"] = tn
    von, bis = _datum(ki.get("von")), _datum(ki.get("bis"))
    ok_von = von is not None and heute - timedelta(days=120) <= von <= heute + timedelta(days=550)
    ok_bis = bis is not None and (von is None or von <= bis <= von + timedelta(days=1100))
    if von is not None and not ok_von:
        hinweise.append(f"KI-Datum {von:%d.%m.%Y} ist unplausibel – verworfen.")
    if bis is not None and not ok_bis:
        hinweise.append(f"KI-Enddatum {bis:%d.%m.%Y} ist unplausibel – verworfen.")
    if ok_von:
        neu["von"] = von
        if regel.von and regel.von != von:
            hinweise.append(f"Beginn: KI {von:%d.%m.%Y}, Regeln {regel.von:%d.%m.%Y} – bitte prüfen.")
    if ok_bis:
        neu["bis"] = bis
        if regel.bis and regel.bis != bis:
            hinweise.append(f"Ende: KI {bis:%d.%m.%Y}, Regeln {regel.bis:%d.%m.%Y} – bitte prüfen.")
    m_text = str(ki.get("massnahme") or "").strip()
    if m_text:
        gefunden = massnahme_finden(m_text, massnahmen)
        neu["massnahme"] = gefunden or m_text[:60]
        if massnahmen and not gefunden:
            hinweise.append(f"Maßnahme „{m_text[:40]}“ steht so nicht in der Anreiseliste – bitte prüfen.")
    if isinstance(ki.get("einzelzimmer"), bool):
        neu["einzelzimmer"] = ki["einzelzimmer"]
    if ki.get("bestaetigung_erbeten") is True:
        neu["bestaetigung"] = True
    if ki.get("kostenuebernahme_folgt") is True:
        neu["kostenuebernahme"] = True
    z = " ".join(str(ki.get("zusammenfassung") or "").split())
    if z:
        neu["zusammenfassung"] = z[:220]
    ki_unsicher = [str(x)[:160] for x in (ki.get("unsicher") or []) if str(x).strip()][:4]
    e = replace(regel, **neu)
    e.unsicher = [u for u in regel.unsicher if not (u.startswith("Zeitraum unvollständig") and e.von and e.bis)
                  and not (u.startswith("Keine Person") and (e.name or e.tn_id))
                  and not (u.startswith("Art der Mail") and e.art != "unklar")] + hinweise + ki_unsicher
    if e.art in ("gast", "anmeldung") and not (e.von and e.bis) and not any("Zeitraum" in u for u in e.unsicher):
        e.unsicher.append("Zeitraum unvollständig – bitte Anreise und Abreise prüfen.")
    e.quelle = "KI (lokal)"
    return e


# ---- Beispiele aus bestätigten Mails -----------------------------------------------------------------------------------

def _woerter(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß]{4,}", (s or "").lower())}


def aehnliche(betreff: str, text: str, beispiele: list[dict], anzahl: int = 3) -> list[dict]:
    """Die ähnlichsten bestätigten Beispiele (gemeinsame Wörter im Verhältnis zur Gesamtzahl)."""
    w = _woerter(f"{betreff} {text}")
    if not w:
        return []
    def wert(b):
        v = _woerter(f"{b.get('betreff', '')} {b.get('text', '')}")
        return len(w & v) / (len(w | v) or 1)
    return sorted((b for b in beispiele if wert(b) > .08), key=wert, reverse=True)[:anzahl]


def als_formular(e) -> dict:
    """Ein bestätigtes Erkannt als Formular (so soll die KI künftig antworten)."""
    nach, _, vor = (e.name or "").partition(",")
    return {"art": e.art, "nachname": nach.strip(), "vorname": vor.strip(), "geschlecht": e.geschlecht or "",
            "tn_id": e.tn_id or "", "von": e.von.isoformat() if e.von else "", "bis": e.bis.isoformat() if e.bis else "",
            "massnahme": e.massnahme or "", "einzelzimmer": e.einzelzimmer, "bestaetigung_erbeten": bool(e.bestaetigung),
            "kostenuebernahme_folgt": bool(e.kostenuebernahme), "zusammenfassung": e.zusammenfassung or "", "unsicher": []}


def beispiele_laden() -> list[dict]:
    from belegung import speicher

    d = speicher.lesen(BEISPIELE, {})
    return list((d or {}).get("beispiele") or []) if isinstance(d, dict) else []


def beispiel_merken(betreff: str, text: str, e) -> None:
    """Nach „Umsetzen“: Mail und bestätigtes Ergebnis als Beispiel merken (höchstens 200, neueste zuerst)."""
    try:
        from belegung import speicher

        liste = [b for b in beispiele_laden() if b.get("betreff") != betreff]
        liste.insert(0, {"betreff": betreff, "text": (text or "")[:1500], "ergebnis": als_formular(e)})
        speicher.schreiben(BEISPIELE, {"beispiele": liste[:MAX_BEISPIELE]})
    except Exception:                                  # noqa: BLE001 – Beispiele sind Komfort
        pass
