"""Quelle -> Datenstand. Läuft in der GUI in einem Hintergrund-Thread."""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from . import anreiseliste, importe, pivot, prognose, speicher, uwt
from .datenstand import Datenstand, Eintrag
from .konfig import EXCEL_BEVORZUGTER_NAME, STANDORT_LABEL, STANDORTE, programmordner

log = logging.getLogger(__name__)

Fortschritt = Callable[[str], None]


def excel_suchen(ordner: Path | None = None) -> Path | None:
    """Zuletzt verwendete Datei, sonst pivot_neu.xlsx, sonst die neueste .xlsx/.xlsm im Ordner."""
    zuletzt = speicher.einstellungen().get("quelle")
    if zuletzt and Path(zuletzt).exists():
        return Path(zuletzt)
    ordner = ordner or programmordner()
    bevorzugt = ordner / EXCEL_BEVORZUGTER_NAME
    if bevorzugt.exists():
        return bevorzugt
    kandidaten = [p for p in list(ordner.glob("*.xlsx")) + list(ordner.glob("*.xlsm")) if not p.name.startswith("~$")]
    return max(kandidaten, key=lambda p: p.stat().st_mtime) if kandidaten else None


def refresh_moeglich() -> bool:
    """Server-Abruf braucht Windows, Excel und pywin32."""
    import importlib.util

    return sys.platform == "win32" and importlib.util.find_spec("win32com") is not None


# ---- lokale Daten ------------------------------------------------------------------------

def manuelle_laden() -> list[dict]:
    daten = speicher.lesen(speicher.MANUELLE_EINTRAEGE, [])
    return daten if isinstance(daten, list) else []


def manuelle_speichern(eintraege: list[dict]) -> None:
    speicher.schreiben(speicher.MANUELLE_EINTRAEGE, eintraege)


def kapazitaeten_laden() -> dict[str, dict[str, int]]:
    roh = speicher.lesen(speicher.KAPAZITAETEN, {})
    return {s: {"netto": int(roh.get(s, {}).get("netto", 0)), "brutto": int(roh.get(s, {}).get("brutto", 0))}
            for s in STANDORTE}


def kapazitaeten_speichern(werte: dict[str, dict[str, int]]) -> None:
    speicher.schreiben(speicher.KAPAZITAETEN, werte)


def eintraege_laden() -> tuple[list[Eintrag], dict[str, dict]]:
    eintraege: list[Eintrag] = []
    for d in manuelle_laden():
        try:
            eintraege.append(Eintrag.aus_dict(d, "manuell"))
        except (KeyError, ValueError) as exc:
            log.warning("Manueller Eintrag übersprungen (%s): %s", exc, d)
    meta: dict[str, dict] = {}
    for art in importe.LISTEN_ARTEN:
        datensatz = importe.datensatz_laden(art)
        if not datensatz:
            continue
        meta[art] = {k: v for k, v in datensatz.items() if k != "eintraege"} | {"anzahl": len(datensatz["eintraege"])}
        for d in datensatz["eintraege"]:
            try:
                eintraege.append(Eintrag.aus_dict(d, art))
            except (KeyError, ValueError):
                continue

    personen, listen = anreiseliste.laden()
    if personen:
        wochen = int(speicher.einstellungen().get("anreise_standard_wochen", 0) or 0)
        for d in anreiseliste.eintraege(personen, wochen):
            eintraege.append(Eintrag.aus_dict(d, "anreisen"))
        letzte = max(listen.values(), key=lambda l: l.get("importiert_am", ""), default={})
        meta["anreisen"] = {"quelle": letzte.get("datei", "manuell"), "importiert_am": letzte.get("importiert_am"),
                            "anzahl": len(personen), "listen": len(listen)}
    bloecke = uwt.laden()
    if bloecke:
        for d in uwt.eintraege(bloecke):
            eintraege.append(Eintrag.aus_dict(d, "uwt"))
        meta["uwt"] = {"quelle": bloecke[-1].get("datei"), "importiert_am": max(b.get("importiert_am", "") for b in bloecke),
                       "anzahl": len(bloecke)}
    return eintraege, meta


def erinnerungen_laden(heute: date | None = None) -> list:
    personen, _ = anreiseliste.laden()
    return anreiseliste.faellige_erinnerungen(personen, heute or date.today())


# ---- Hauptfunktion -----------------------------------------------------------------------

def lade(quelle: Path, refresh: bool = False, fortschritt: Fortschritt | None = None) -> Datenstand:
    melden = fortschritt or (lambda _t: None)
    profil = pivot.profil_fuer_datei(quelle.name)
    aktualisiert = None
    if refresh:
        melden("Pivot wird vom Server aktualisiert (Excel im Hintergrund) …")
        pdaten, aktualisiert = pivot.lese_excel(quelle, profil, refresh=True)
    else:
        melden("Pivot-Werte werden gelesen …")
        pdaten = pivot.lese_datei(quelle, profil)

    melden("Listen und Kapazitäten werden geladen …")
    eintraege, meta = eintraege_laden()
    ds = Datenstand(
        pivot=pdaten, eintraege=eintraege, kapazitaeten=kapazitaeten_laden(), quelle=quelle,
        pivot_aktualisiert=aktualisiert, importe=meta,
    )
    ds.hinweise = _hinweise(ds)
    ds.erinnerungen = erinnerungen_laden()

    melden("Prognose wird berechnet (Backtest der Modelle) …")
    ds.prognose = prognose.berechne(pdaten.reha, ds.anreise_bestand(), ds.stichtag)
    return ds


def neu_berechnen(ds: Datenstand) -> Datenstand:
    """Nach Änderungen an Listen/Kapazitäten: Einträge neu laden, Prognose nur bei Anreisen neu."""
    alte_anreisen = [e for e in ds.eintraege if e.kategorie == "Anreise"]
    ds.eintraege, ds.importe = eintraege_laden()
    ds.kapazitaeten = kapazitaeten_laden()
    ds.hinweise = _hinweise(ds)
    ds.erinnerungen = erinnerungen_laden()
    if alte_anreisen != [e for e in ds.eintraege if e.kategorie == "Anreise"] or ds.prognose is None:
        ds.prognose = prognose.berechne(ds.pivot.reha, ds.anreise_bestand(), ds.stichtag)
    return ds


def _hinweise(ds: Datenstand) -> list[str]:
    h = list(ds.pivot.warnungen)
    heute = date.today()
    abruf = ds.pivot.abrufdatum
    if ds.pivot_aktualisiert is False:
        h.append("Der Server-Abruf ist fehlgeschlagen (Netz/VPN/Berechtigung). Angezeigt wird der zuletzt gespeicherte Pivot-Stand.")
    elif abruf and abruf < heute - timedelta(days=1):
        h.append(f"Pivot-Stand vom {abruf:%d.%m.%Y}. Für tagesaktuelle Zahlen „Vom Server aktualisieren“ wählen.")
    ohne = [STANDORT_LABEL[s] for s in STANDORTE if not ds.hat_kapazitaet(s)]
    if ohne:
        h.append("Keine Kapazität hinterlegt für " + ", ".join(ohne) + " – Auslastung ist dort nicht berechenbar (Daten → Kapazitäten).")
    return h
