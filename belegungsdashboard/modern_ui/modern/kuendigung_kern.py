"""1.63: Mietvertrag kündigen und Vertrag aus einem Gebäudeplan-Mieter anlegen.

Kündigung
* Festgehalten werden: Eingang (Datum), wer kündigt (Mieter/Vermieter), zum (letzter Miettag) und ein Grund. Je Standort
  in ``importe/modern_kuendigungen.json`` – der Mietvertrag selbst (Hauptprogramm-Format) bleibt unverändert, außer
  dass sein Ende auf den Kündigungstermin vorgezogen wird (so wird das Zimmer im Plan ab dann frei).
* Eine Kündigungsbestätigung zum Drucken (HTML, ohne Daten auf dem Server).
* Zurücknehmen: das alte Ende wird wiederhergestellt.

Vertrag aus dem Gebäudeplan
* „Weitere Mieter laut Gebäudeplan“ haben keinen Vertrag im Programm. ``vorgabe`` macht aus der Belegung Vorgabewerte
  für „Neuer Mieter“ (Name getrennt, Zimmer, Beginn, Ende).

Rein bis auf Lesen/Schreiben der Dateien (Kündigungen, Mietverträge, Zimmerplan) – in EINEM Schritt (ein Rückgängig).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import escape

DATEI = "importe/modern_kuendigungen.json"
WER = {"mieter": "durch den Mieter", "vermieter": "durch den Vermieter", "einvernehmlich": "einvernehmlich"}


@dataclass
class Kuendigung:
    nr: str                  # Vertragsnummer
    eingang: str             # ISO-Datum
    zum: str                 # ISO-Datum: letzter Miettag
    wer: str                 # mieter | vermieter | einvernehmlich
    grund: str = ""
    bis_alt: str = ""        # Ende vor der Kündigung (für Zurücknehmen)
    erfasst: str = ""        # ISO-Zeit

    @property
    def zum_datum(self) -> date:
        return date.fromisoformat(self.zum)


def laden() -> dict[str, Kuendigung]:
    from belegung import speicher

    d = speicher.lesen(DATEI, {})
    erg = {}
    for x in (d or {}).get("kuendigungen", []) if isinstance(d, dict) else []:
        try:
            k = Kuendigung(**{f: x.get(f, "") for f in Kuendigung.__dataclass_fields__})
            erg[k.nr] = k
        except Exception:                                # noqa: BLE001 – kaputte Zeile überspringen
            continue
    return erg


def _speichern(alle: dict[str, Kuendigung]) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, {"kuendigungen": [asdict(k) for k in alle.values()]})


def pruefen(von: date, bis: date, zum: date, eingang: date) -> list[str]:
    fehler = []
    if zum < von:
        fehler.append(f"Der Kündigungstermin liegt vor dem Mietbeginn ({von:%d.%m.%Y}).")
    if zum > bis:
        fehler.append(f"Der Kündigungstermin liegt nach dem Vertragsende ({bis:%d.%m.%Y}) – dann reicht das Vertragsende.")
    if eingang > date.today() and eingang > zum:
        fehler.append("Der Eingang der Kündigung liegt in der Zukunft.")
    return fehler


def _ende_setzen(nr: str, bis: date, aktion: str) -> None:
    """Vertragsende setzen (Mietverträge + Zimmerplan + Verlauf) – innerhalb des Schritts des Aufrufers, damit
    „Rückgängig“ Kündigung UND Vertragsende zusammen zurücknimmt."""
    from dataclasses import replace

    from belegung import mieter as mt
    from belegung import protokoll

    alt = mt.nach_nummer(nr)
    if alt is None or alt.bis == bis:
        return
    neu = replace(alt, bis=bis, mail_ende="", verlaengerungen=list(alt.verlaengerungen))
    mt._speichern([neu if m.nr == nr else m for m in mt.laden()])
    mt._zuweisung_setzen(neu)
    protokoll.eintragen([{"aktion": aktion, "name": f"{neu.nachname}, {neu.vorname}", "person": neu.person,
                          "alt": f"{alt.bis:%d.%m.%Y}", "neu": f"{bis:%d.%m.%Y}", "von": neu.von.isoformat(),
                          "quelle": "Mieter · Vertragsende"}])


def kuendigen(nr: str, zum: date, eingang: date, wer: str = "mieter", grund: str = "") -> str:
    """Kündigung festhalten und das Vertragsende vorziehen – EIN Schritt (ein Rückgängig für beides)."""
    from belegung import mieter as mt

    from .kern import _schritt

    mv = mt.nach_nummer(nr)
    if mv is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    if f := pruefen(mv.von, mv.bis, zum, eingang):
        raise ValueError(" ".join(f))
    alt = laden().get(nr)
    bis_alt = alt.bis_alt if alt and alt.bis_alt else mv.bis.isoformat()

    def tun():
        _ende_setzen(nr, zum, "Mietvertrag gekündigt")
        alle = laden()
        alle[nr] = Kuendigung(nr, eingang.isoformat(), zum.isoformat(), wer if wer in WER else "mieter", grund.strip(),
                              bis_alt, datetime.now().isoformat(timespec="seconds"))
        _speichern(alle)
    _schritt(f"Kündigung MV {nr}", tun, [DATEI, mt.DATEI])
    return f"MV {nr} gekündigt zum {zum:%d.%m.%Y} – das Zimmer ist im Plan ab dem Folgetag frei"


def zuruecknehmen(nr: str) -> str:
    from belegung import mieter as mt

    from .kern import _schritt

    k = laden().get(nr)
    if k is None:
        raise ValueError("Zu diesem Vertrag gibt es keine Kündigung.")

    def tun():
        if k.bis_alt:
            _ende_setzen(nr, date.fromisoformat(k.bis_alt), "Kündigung zurückgenommen")
        alle = laden()
        alle.pop(nr, None)
        _speichern(alle)
    _schritt(f"Kündigung MV {nr} zurückgenommen", tun, [DATEI, mt.DATEI])
    return f"Kündigung MV {nr} zurückgenommen" + (f" – Ende wieder {date.fromisoformat(k.bis_alt):%d.%m.%Y}"
                                                   if k.bis_alt else "")


def status_text(k: Kuendigung | None) -> str:
    if k is None:
        return ""
    return f"gekündigt zum {k.zum_datum:%d.%m.%Y} ({WER.get(k.wer, k.wer)})"


def bestaetigung_html(mv, k: Kuendigung, ort: str = "", absender: str = "") -> str:
    """Kündigungsbestätigung zum Drucken (eine Seite)."""
    anrede = "Sehr geehrte Frau" if mv.anrede != "Herr" else "Sehr geehrter Herr"
    eingang = date.fromisoformat(k.eingang)
    return (
        "<style>body{font-family:'Segoe UI',sans-serif;font-size:11pt;line-height:1.5;margin:2.5cm 2cm}"
        "h1{font-size:14pt}.klein{color:#555;font-size:9.5pt}</style>"
        f"<p class='klein'>{escape(absender)}</p>"
        f"<p>{escape(mv.anrede)} {escape(mv.vorname)} {escape(mv.nachname)}<br>Zimmer {escape(mv.zimmer_kurz)}</p>"
        f"<p style='text-align:right'>{escape(ort + ', ' if ort else '')}{date.today():%d.%m.%Y}</p>"
        f"<h1>Bestätigung der Kündigung – Mietvertrag {escape(mv.nr)}</h1>"
        f"<p>{anrede} {escape(mv.nachname)},</p>"
        f"<p>wir bestätigen den Eingang Ihrer Kündigung vom {eingang:%d.%m.%Y}. Das Mietverhältnis über das Zimmer "
        f"{escape(mv.zimmer_kurz)} endet am <b>{k.zum_datum:%d.%m.%Y}</b>.</p>"
        "<p>Bitte geben Sie bis zu diesem Tag alle Schlüssel zurück und vereinbaren Sie mit uns einen Termin für die "
        "Zimmerübergabe. Eine vereinbarte Mietsicherheit rechnen wir nach der Übergabe ab.</p>"
        "<p>Mit freundlichen Grüßen</p><p><br><br>_______________________________</p>")


def vorgabe(name: str, zid: str, von: date, bis: date) -> dict:
    """Vorgabewerte für „Neuer Mieter“ aus einem Gebäudeplan-Mieter („Nachname, Vorname“)."""
    nach, _, vor = (name or "").partition(",")
    if not vor and " " in nach.strip():                  # „Vorname Nachname“
        vor, _, nach = nach.strip().rpartition(" ")
    return {"vorname": vor.strip(), "nachname": nach.strip(), "zimmer": zid, "von": von, "bis": bis}
