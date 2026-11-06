"""Leitstand-Workbench (0.62): eine zweite, komplett anders aufgebaute Oberfläche – umschaltbar je PC.

Statt Seiten mit Seitenleiste, Kachelreihe und einfahrendem Panel ein fest eingeteilter Bildschirm:

* **Kommandobrücke** (oben, 40 px): vier Arbeitsbühnen [1]–[4], Live-Omnibar (filtert beim Tippen, ``/`` oder
  Strg+K setzt den Fokus), Stand, Rückgängig im Klartext, Abtipp-Modus, „⇄ Ansicht wechseln“.
* **Drei Spalten:** links der Arbeitsstrom bzw. die Arbeitslisten, in der Mitte die Gebäude-Matrix bzw. das Werkzeug,
  rechts der fest angedockte **Inspektor** – alle Formulare der bisherigen Oberfläche erscheinen dort statt im
  Schiebe-Panel (nichts wird abgedunkelt oder verdeckt).
* **Tastenleiste** (unten, 26 px) mit den gerade gültigen Kürzeln.

Technisch ist ``Leitstand`` eine Unterklasse von ``oberflaeche.Ansicht``: Laden, Speichern (``aendern`` →
``kern._schritt`` mit Schreibsperre), Verlauf und Rückgängig sind dieselben. Die Bühnen 2–4 nutzen die bestehenden
Werkzeuge (Mieter, Termine, Auswertung, Steuerung …) unverändert in der mittleren Spalte. Farben und Schrift nach dem
Corporate Design (PT Sans, Petrol/Orange); CSS nur unter ``body.leitstand``.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from nicegui import app, run, ui

from . import __version__, kern, register, seite_anreisen, themes
from .oberflaeche import CSS, SORTIER_JS, Ansicht
from .ui_bausteine import attr, knopf, leer

log = logging.getLogger(__name__)

EINSTELLUNG = "oberflaeche"            # persönlich je PC: "klassisch" | "leitstand"
BUEHNEN = {"dispo": ("1", "Disposition", "dashboard"), "akten": ("2", "Verwaltung", "folder_open"),
           "radar": ("3", "Auswertung", "insights"), "bau": ("4", "Bau & Budget", "construction")}
# Arbeitslisten der Bühnen 2–4: (Schlüssel, Titel, Seite, Ansicht)
AKTEN = [("eintragen", "Firmenprogramm (ins Trägersystem)", "anreisen", "eintragen"),
         ("mieter", "Mieter & Verträge", "mieter", None), ("termine", "Termine & Wiedervorlagen", "termine", None),
         ("assistenz", "Assistenz & Post", "assistenz", None), ("personen", "Personen (alle Anreisen)", "anreisen", "personen"),
         ("abreisen", "Abreisen", "anreisen", "abreisen"), ("inventar", "Inventar", "inventar", None),
         ("daten", "Daten & Import", "daten", None), ("einstellungen", "Einstellungen", "einstellungen", None)]
RADAR = [("lage", "Lage heute"), ("prognose", "Belegungsprognose"), ("massnahmen", "Maßnahmen (Neuanmeldungen)"),
         ("zimmer", "Zimmer & Engpässe"), ("belegung", "Belegung (Verlauf)")]
BAU = [("cockpit", "Cockpit"), ("vorhaben", "Vorhaben & Renovierung"), ("zeitplan", "Zeitplan & Kapazität"),
       ("finanzen", "Finanzen & Budget"), ("grundlagen", "Grundlagen")]
MITTE = {"etagen": "Etagenplan", "zimmer": "Zeitstrahl", "reinigung": "Reinigung"}
LAYER = {"belegung": "Belegung", "abreise": "Abreisen 7 Tage", "maengel": "Mängel"}
SCHRIFT_DATEIEN = ("PTSans-Regular", "PT_Sans-Web-Regular", "PTSans-Bold", "PT_Sans-Web-Bold", "pt-sans")


def an() -> bool:
    from .netz_kern import persoenlich

    try:
        return persoenlich(EINSTELLUNG, "klassisch", je_standort=False) == "leitstand"
    except Exception:                          # noqa: BLE001 – im Zweifel die gewohnte Oberfläche
        return False


def setzen(leitstand: bool) -> None:
    from .netz_kern import persoenlich_setzen

    persoenlich_setzen(EINSTELLUNG, "leitstand" if leitstand else "klassisch", je_standort=False)


async def umschalten(a) -> None:
    """Zwischen klassischer Oberfläche und Leitstand wechseln (je PC gemerkt); Standort und Daten bleiben."""
    await run.io_bound(setzen, not isinstance(a, Leitstand))
    ui.navigate.reload()


def _schrift_css() -> str:
    """PT Sans (Hausschrift) aus dem Ordner „Vorlagen“ im Datenordner, falls dort abgelegt – sonst installiert/Segoe UI."""
    from .standort_kern import _BASIS

    regeln = []
    try:
        ordner = _BASIS() / "Vorlagen"
        dateien = [p for p in ordner.glob("*") if p.suffix.lower() in (".ttf", ".otf", ".woff", ".woff2")
                   and p.stem.replace(" ", "").lower().startswith(("ptsans", "pt_sans", "pt-sans"))]
        if dateien:
            app.add_static_files("/ls-schrift", str(ordner))
            for p in dateien:
                fett = "bold" in p.stem.lower()
                regeln.append(f"@font-face {{ font-family: 'PT Sans'; src: url('/ls-schrift/{p.name}'); "
                              f"font-weight: {700 if fett else 400}; font-display: swap; }}")
    except Exception:                          # noqa: BLE001 – ohne Schriftdatei: installierte Schrift
        pass
    return "\n".join(regeln)


# Corporate Design: Petrol #134F4F (dunkel) · #007F7F / #009A9B · Orange #EF7D00 / #F7A54A · Grau #5E6E6E ·
# Hellgrund #F4F6F5 · Linien #DEE5E4 / #C9CAC9 · Schrift PT Sans
LS_CSS = """
html body.leitstand.pro.th-innternat.mod-hell, html body.leitstand {
  --ls-petrol: #134F4F; --ls-petrol2: #0E3D3D; --ls-teal: #007F7F; --ls-teal2: #009A9B; --ls-orange: #EF7D00;
  --ls-orange2: #F7A54A; --ls-grau: #5E6E6E; --ls-grund: #F4F6F5; --ls-weiss: #FCFDFC; --ls-linie: #DEE5E4;
  --ls-linie2: #C9CAC9; --ls-text: #1D2B2B; --ls-text2: #384646; --ls-text3: #5E6E6E; --ls-rot: #B3261E; --ls-gruen: #1E7B4F;
  --bg: var(--ls-grund); --fl: var(--ls-weiss); --fl2: #EEF2F1; --text: var(--ls-text); --text2: var(--ls-text2);
  --text3: var(--ls-text3); --rand: var(--ls-linie); --rand2: var(--ls-linie2); --akzent: var(--ls-teal);
  --akzent-text: #FFFFFF; --orange: #B45A00; --rot: var(--ls-rot); --gruen: var(--ls-gruen); --blau: #2C5D8A;
  --schrift: 'PT Sans', 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif; --titel-schrift: var(--schrift);
  background: var(--ls-grund) !important; color: var(--ls-text); font-family: var(--schrift); font-size: 14px;
  overflow: hidden; font-variant-numeric: tabular-nums;
}
body.leitstand * { font-variant-numeric: tabular-nums; }
body.leitstand .m-tb, body.leitstand .m-nav, body.leitstand .m-topnav, body.leitstand .m-center,
body.leitstand .m-schleier { display: none !important; }
.ls-app { position: fixed; inset: 0; display: grid; grid-template-rows: 40px 1fr 26px; background: var(--ls-grund); }
/* Zone A: Kommandobrücke */
.ls-spine { display: flex; align-items: center; gap: 6px; padding: 0 8px; background: var(--ls-petrol); color: #fff;
  overflow: hidden; min-width: 0; }
.ls-spine > * { flex-shrink: 0; }
.ls-spine > .ls-omni { flex: 1 1 160px; min-width: 120px; }
.ls-spine .ls-sknopf.undo { flex-shrink: 1; min-width: 90px; max-width: 280px; }
@media (max-width: 1500px) { .ls-marke small, .ls-buehne span.t { display: none; } }
.ls-marke { font-weight: 700; letter-spacing: .02em; margin-right: 6px; white-space: nowrap; font-size: 14px; }
.ls-marke small { font-weight: 400; opacity: .75; margin-left: 6px; }
.ls-buehne { display: flex; align-items: center; gap: 6px; height: 30px; padding: 0 10px; border-radius: 6px;
  color: #DDE9E8; background: transparent; border: 1px solid transparent; cursor: pointer; font: inherit; white-space: nowrap; }
.ls-buehne b { display: inline-grid; place-items: center; width: 18px; height: 18px; border-radius: 4px; font-size: 11px;
  background: rgba(255,255,255,.14); }
.ls-buehne:hover { background: rgba(255,255,255,.08); }
.ls-buehne.an { background: var(--ls-weiss); color: var(--ls-petrol); font-weight: 700; }
.ls-buehne.an b { background: var(--ls-orange); color: #fff; }
.ls-omni { flex: 1; min-width: 220px; max-width: 620px; margin: 0 8px; position: relative; }
.ls-omni input { width: 100%; height: 28px; border-radius: 6px; border: 1px solid rgba(255,255,255,.25);
  background: rgba(255,255,255,.10); color: #fff; padding: 0 10px 0 30px; font: inherit; outline: none; }
.ls-omni input::placeholder { color: rgba(255,255,255,.65); }
.ls-omni input:focus { background: #fff; color: var(--ls-text); border-color: var(--ls-orange); }
.ls-omni .q-icon { position: absolute; left: 8px; top: 6px; font-size: 16px; color: rgba(255,255,255,.75); }
.ls-omni-tipp { position: absolute; right: 8px; top: 6px; font-size: 11px; color: var(--ls-grau); pointer-events: none; }
.ls-spine .m-datenstand { color: #DDE9E8; background: rgba(255,255,255,.08); border-radius: 6px; padding: 3px 8px;
  font-size: 12px; white-space: nowrap; }
.ls-spine .m-datenstand.neu { background: var(--ls-orange); color: #fff; }
.ls-sknopf { display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 10px; border-radius: 6px;
  border: 1px solid rgba(255,255,255,.22); background: transparent; color: #fff; font: inherit; cursor: pointer;
  white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
.ls-sknopf .q-icon { font-size: 16px; flex: none; }
.ls-sknopf:hover { background: rgba(255,255,255,.10); }
.ls-sknopf.orange { background: var(--ls-orange); border-color: var(--ls-orange); }
/* Hauptbühne: drei Spalten */
.ls-main { display: grid; grid-template-columns: minmax(0, 24fr) minmax(0, 48fr) minmax(0, 28fr); min-height: 0; min-width: 0; }
.ls-main.breit { grid-template-columns: minmax(0, 19fr) minmax(0, 53fr) minmax(0, 28fr); }
.ls-main.ohne-insp { grid-template-columns: minmax(0, 19fr) minmax(0, 81fr); }      /* 0.65: leere Details-Spalte weg */
.ls-main.ohne-insp > .ls-col.rechts { display: none; }
.ls-col { min-height: 0; min-width: 0; overflow: auto; border-right: 1px solid var(--ls-linie); background: var(--ls-weiss); }
.ls-col.mitte { background: var(--ls-grund); display: flex; flex-direction: column; overflow: hidden; }
.ls-col.rechts { border-right: 0; background: var(--ls-weiss); }
.ls-kopf { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 8px 12px; border-bottom: 1px solid var(--ls-linie);
  background: var(--ls-weiss); min-height: 40px; }
.ls-kopf .ls-titel { font-weight: 700; color: var(--ls-petrol); margin-right: 6px; }
.ls-mitte-inhalt { flex: 1; overflow: auto; min-height: 0; }
.ls-col.mitte .m-leiste { position: static; padding: 6px 12px; border-bottom: 1px solid var(--ls-linie); background: var(--ls-weiss); }
.ls-col.mitte .m-inhalt { padding: 0; max-width: none; }
.ls-col.mitte .m-werkzeuge { display: flex; gap: 6px; flex-wrap: wrap; }
/* Spalte 1: Arbeitsstrom */
.ls-puls { display: flex; gap: 6px; padding: 10px 12px; border-bottom: 1px solid var(--ls-linie); flex-wrap: wrap; }
.ls-pill { display: inline-flex; gap: 6px; align-items: center; padding: 3px 9px; border-radius: 999px; font-size: 12px;
  background: var(--fl2); color: var(--ls-text2); border: 1px solid var(--ls-linie); cursor: pointer; }
.ls-pill b { font-size: 13px; }
.ls-pill.krit { background: #FBEAE9; color: var(--ls-rot); border-color: #F1C4C1; }
.ls-pill.warn { background: #FFF1E3; color: #8A4600; border-color: #F7D3AC; }
.ls-gruppe { padding: 10px 12px 4px; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
  color: var(--ls-grau); display: flex; align-items: center; gap: 6px; }
.ls-gruppe .q-select { flex: 1; }
.ls-eintrag { display: grid; grid-template-columns: 8px 1fr auto; gap: 8px; align-items: center; width: 100%;
  padding: 7px 12px; border: 0; border-left: 3px solid transparent; background: transparent; text-align: left;
  font: inherit; color: var(--ls-text); cursor: pointer; }
.ls-eintrag:hover { background: #EEF4F3; }
.ls-eintrag.an { background: #E2EFEE; border-left-color: var(--ls-teal); }
.ls-eintrag .t1 { font-weight: 600; line-height: 1.25; }
.ls-eintrag .t2 { font-size: 12px; color: var(--ls-text3); line-height: 1.25; }
.ls-eintrag .z { font-size: 12px; color: var(--ls-petrol); font-weight: 700; white-space: nowrap; }
.ls-eintrag .z.offen { color: var(--ls-orange); }
.ls-punkt { width: 8px; height: 8px; border-radius: 50%; background: var(--ls-linie2); }
.ls-punkt.krit, .ls-punkt.dringend { background: var(--ls-rot); } .ls-punkt.warn, .ls-punkt.bald { background: var(--ls-orange); }
.ls-punkt.ok, .ls-punkt.info { background: var(--ls-teal2); }
.ls-badges { display: inline-flex; gap: 3px; margin-left: 4px; vertical-align: 1px; }
.ls-b { font-size: 10.5px; padding: 0 5px; border-radius: 4px; background: var(--fl2); color: var(--ls-text2); border: 1px solid var(--ls-linie); }
.ls-b.frage { background: #FFF1E3; color: #8A4600; border-color: #F7D3AC; }
.ls-b.neu { background: var(--ls-teal); color: #fff; border-color: var(--ls-teal); }
.ls-b.warn { background: #FBEAE9; color: var(--ls-rot); border-color: #F1C4C1; }
.ls-leer { padding: 8px 12px; color: var(--ls-text3); font-size: 13px; }
/* Spalte 2: Gebäude-Matrix */
.ls-matrix { padding: 10px 12px 18px; display: flex; flex-direction: column; gap: 12px; }
.ls-haus { background: var(--ls-weiss); border: 1px solid var(--ls-linie); border-radius: 8px; padding: 8px 10px; }
.ls-haus-k { font-weight: 700; color: var(--ls-petrol); margin-bottom: 4px; display: flex; gap: 10px; align-items: baseline; }
.ls-haus-k small { font-weight: 400; color: var(--ls-text3); }
.ls-etage { display: grid; grid-template-columns: 34px 1fr; gap: 6px; align-items: start; padding: 3px 0; }
.ls-etage-n { font-size: 11px; color: var(--ls-text3); padding-top: 6px; text-align: right; }
.ls-zellen { display: flex; flex-wrap: wrap; gap: 3px; }
.ls-z { position: relative; width: 56px; height: 34px; border-radius: 5px; border: 1px solid var(--ls-linie2);
  background: #fff; font: inherit; font-size: 11.5px; line-height: 1.1; padding: 3px 4px; text-align: left; cursor: pointer;
  color: var(--ls-text); overflow: hidden; }
.ls-z .n { font-weight: 700; display: block; }
.ls-z .s { font-size: 10px; color: var(--ls-text3); white-space: nowrap; }
.ls-z.frei { background: #EAF6F1; border-color: #BFE2D2; }
.ls-z.teilweise { background: #F1F8F5; border-color: #CFE7DC; }
.ls-z.belegt { background: #E4EEF5; border-color: #C5D8E6; }
.ls-z.geplant { background: #E6F1F1; border-color: #B7D6D6; border-style: dashed; }
.ls-z.gesperrt { background: repeating-linear-gradient(45deg, #EEF0EF, #EEF0EF 4px, #E1E5E4 4px, #E1E5E4 8px); color: var(--ls-text3); }
.ls-z .mangel { position: absolute; top: 2px; right: 3px; color: var(--ls-orange); font-weight: 700; }
.ls-z .ab { position: absolute; bottom: 2px; right: 3px; font-size: 9.5px; color: #8A4600; }
.ls-z.dim { opacity: .28; }
.ls-z.passt { box-shadow: 0 0 0 2px var(--ls-teal2) inset; opacity: 1; }
.ls-z.vorschlag { box-shadow: 0 0 0 3px var(--ls-gruen) inset, 0 0 0 2px #fff, 0 0 0 4px var(--ls-gruen); }
.ls-z.aktuell { box-shadow: 0 0 0 3px var(--ls-petrol) inset; }
.ls-z.treffer { box-shadow: 0 0 0 2px var(--ls-orange) inset; }
.ls-z.fokus { outline: 3px solid var(--ls-orange); outline-offset: 1px; }
.ls-z.layer-ab { background: #FFF1E3; border-color: #F7D3AC; }
.ls-z.layer-mangel { background: #FBEAE9; border-color: #F1C4C1; }
.ls-legende { display: flex; gap: 12px; flex-wrap: wrap; font-size: 11.5px; color: var(--ls-text3); padding: 0 12px 8px; }
.ls-legende i { display: inline-block; width: 12px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px;
  border: 1px solid var(--ls-linie2); }
.ls-seg { display: inline-flex; border: 1px solid var(--ls-linie2); border-radius: 6px; overflow: hidden; }
.ls-seg button { border: 0; background: #fff; padding: 4px 10px; font: inherit; font-size: 12.5px; cursor: pointer; color: var(--ls-text2); }
.ls-seg button.an { background: var(--ls-petrol); color: #fff; }
.ls-seg button + button { border-left: 1px solid var(--ls-linie2); }
/* Spalte 3: Inspektor */
.ls-insp-k { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--ls-linie);
  position: sticky; top: 0; background: var(--ls-weiss); z-index: 2; }
.ls-insp-k .ls-titel { font-weight: 700; color: var(--ls-petrol); flex: 1; }
.ls-insp { padding: 12px 14px 24px; display: flex; flex-direction: column; gap: 8px; }
.ls-insp.ungespeichert { box-shadow: 0 0 0 3px var(--ls-orange2) inset; }
.ls-ungespeichert { background: #FFF1E3; color: #8A4600; font-size: 12px; padding: 4px 14px; display: none; }
.ls-insp.ungespeichert + .ls-ungespeichert, .ls-ungespeichert.an { display: block; }
.ls-vorschlag { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; padding: 7px 9px;
  border: 1px solid var(--ls-linie); border-radius: 6px; background: #fff; }
.ls-vorschlag.gruen { border-color: #9BD1B6; background: #F1F9F5; }
.ls-vorschlag .t1 { font-weight: 700; } .ls-vorschlag .t2 { font-size: 12px; color: var(--ls-text3); }
.ls-warnbanner { background: #FBEAE9; color: var(--ls-rot); border: 1px solid #F1C4C1; border-radius: 6px; padding: 7px 9px; font-size: 13px; }
.ls-hilfe { color: var(--ls-text3); font-size: 13px; line-height: 1.45; }
/* Zone E: Tastenleiste */
.ls-fuss { display: flex; align-items: center; gap: 14px; padding: 0 10px; background: #E7ECEB; border-top: 1px solid var(--ls-linie2);
  font-size: 11.5px; color: var(--ls-text2); white-space: nowrap; overflow: hidden; }
.ls-fuss kbd { font-family: inherit; font-size: 11px; background: #fff; border: 1px solid var(--ls-linie2); border-bottom-width: 2px;
  border-radius: 4px; padding: 0 4px; margin-right: 3px; color: var(--ls-petrol); }
.ls-fuss .rechts { margin-left: auto; color: var(--ls-text3); }
.ls-kuerzel { position: fixed; bottom: 32px; right: 12px; z-index: 50; background: #fff; border: 1px solid var(--ls-linie2);
  border-radius: 8px; box-shadow: 0 8px 28px rgba(19,79,79,.18); padding: 12px 16px; font-size: 13px; display: none; width: 360px; }
.ls-kuerzel.an { display: block; }
.ls-kuerzel div { display: flex; justify-content: space-between; gap: 12px; line-height: 1.8; }
body.leitstand .m-knopf.primaer { background: var(--ls-teal); border-color: var(--ls-teal); color: #fff; }
body.leitstand .m-knopf.gruen { background: var(--ls-gruen); border-color: var(--ls-gruen); color: #fff; }
body.leitstand .m-toast { background: var(--ls-petrol); color: #fff; }
body.leitstand.abtipp-schmal .ls-spine, body.leitstand.abtipp-schmal .ls-fuss { display: none; }
"""

FUSS = {
    "dispo": [("↑ ↓", "Liste"), ("Enter", "grünen Vorschlag zuweisen"), ("/", "Suche"), ("1–4", "Bereich"),
              ("Strg+Z", "Rückgängig"), ("Strg+Umschalt+L", "Ansicht wechseln")],
    "andere": [("/", "Suche"), ("1–4", "Bereich"), ("Strg+Z", "Rückgängig"), ("Strg+Umschalt+L", "Ansicht wechseln")],
}
KUERZEL = [("1 · 2 · 3 · 4", "Bereich wählen"), ("/ oder Strg+K", "Suche"), ("↑ / ↓", "Arbeitsliste"),
           ("Enter", "grünen Zimmervorschlag zuweisen"), ("Esc", "Details schließen / Suche leeren"),
           ("Strg+Z", "letzte Änderung zurück"), ("Strg+Umschalt+L", "klassische Ansicht"),
           ("L · S", "Postfach-Aufgabe lösen / später"), ("1–6 · E · N", "Abtipp-Modus")]


def _klickbar(z) -> set[str]:
    """Zimmer, die ein Klick in der Matrix sofort zuweist: frei und passend (Ausnahmen wie Gästezimmer nur von Hand
    über „Beste Zimmer“ bzw. „Zimmer prüfen“ – wie in der klassischen Ansicht)."""
    return {o.zimmer for o in z.optionen if o.art in ("frei", "vorschlag")} if z is not None else set()


class Leitstand(Ansicht):
    """Gleiche Daten, gleiche Handlungen – anderer Bildschirm."""

    def __init__(self) -> None:
        super().__init__()
        from .netz_kern import persoenlich

        self.design = {**self.design, "layout": "grid"}       # kein AI-Canvas-Zweig der Basisklasse
        self.buehne = persoenlich("ls_buehne", "dispo", je_standort=False) or "dispo"
        if self.buehne not in BUEHNEN:
            self.buehne = "dispo"
        self.ls_mitte = "etagen"
        self.ls_layer = "belegung"
        self.ls_text = ""
        self.ls_akte = "eintragen"
        self.fokus: tuple | None = None      # ("person", Schlüssel) | ("karte", Id) | ("zimmer", Zimmer-ID)
        self.ls_reihe: list[tuple] = []
        self.ls_maengel: dict = {}
        self.seite = "anreisen"
        self.ansicht["anreisen"] = "zuteilen"
        self._seite_fuer_buehne()

    # ---- Bühnen ↔ Seiten der bisherigen Oberfläche -----------------------------------------

    def _seite_fuer_buehne(self) -> None:
        if self.buehne == "dispo":
            if self.ls_mitte == "zimmer":
                self.seite = "zimmer"
                self.ansicht["zimmer"] = "zeitstrahl"
            elif self.ls_mitte == "reinigung":
                self.seite = "reinigung"
            else:
                self.seite = "anreisen"
                self.ansicht["anreisen"] = "zuteilen"
        elif self.buehne == "akten":
            _k, _t, seite, ans = next((x for x in AKTEN if x[0] == self.ls_akte), AKTEN[0])
            self.seite = seite
            if ans:
                self.ansicht[seite] = ans
        elif self.buehne == "radar":
            self.seite = "auswertung"
            self.ansicht.setdefault("auswertung", "prognose")
        else:
            self.seite = "steuerung"

    async def buehne_waehlen(self, b: str) -> None:
        from .netz_kern import persoenlich_setzen

        if b not in BUEHNEN:
            return
        self.buehne = b
        try:
            persoenlich_setzen("ls_buehne", b, je_standort=False)
        except OSError:
            pass
        self.panel_def = None
        self._seite_fuer_buehne()
        self.daten = None
        self._spine_buehnen()
        self.zeichnen()
        await self.laden()

    async def oeffnen(self, seite: str, ansicht: str | None = None, **zustand) -> None:
        """Sprünge der bisherigen Seiten („zu Mieter“, „Zimmerkarte öffnen“ …) auf die passende Bühne lenken."""
        karte = zustand.pop("karte", None)
        for k, v in zustand.items():
            setattr(self, k, v)
        ziel = ansicht or self.ansicht_von(seite, "")
        if seite in ("heute",) or (seite == "anreisen" and ziel in ("", "zuteilen")):
            self.buehne, self.ls_mitte = "dispo", "etagen"
        elif seite == "zimmer":
            self.buehne, self.ls_mitte = "dispo", ("zimmer" if ziel in ("zeitstrahl", "") or not karte else "etagen")
            if ziel and ziel != "zeitstrahl":
                self.ls_mitte = "etagen"
        elif seite == "reinigung":
            self.buehne, self.ls_mitte = "dispo", "reinigung"
        elif seite == "auswertung":
            self.buehne = "radar"
            if ziel:
                self.ansicht["auswertung"] = ziel
        elif seite == "steuerung":
            self.buehne = "bau"
            if ziel:
                self.ansicht["steuerung"] = ziel
        else:
            self.buehne = "akten"
            self.ls_akte = next((k for k, _t, s, a in AKTEN if s == seite and (a is None or a == ziel)), self.ls_akte)
        self.panel_def = None
        self._seite_fuer_buehne()
        self.daten = None
        self._spine_buehnen()
        self.zeichnen()
        await self.laden()
        if karte:
            from . import seite_zimmer

            self.fokus = ("zimmer", karte)
            await seite_zimmer.karte_oeffnen(self, karte)

    # ---- Laden: der Arbeitsstrom braucht die Anreisen immer -------------------------------

    def _laden(self) -> None:
        super()._laden()
        if self.seite != "anreisen" or self.ansicht_von("anreisen", "zuteilen") != "zuteilen":
            self.anreisen = kern.anreisen(self.stand, self.heute, self.zu_vergangene)
            if self.kennung not in {a.kennung for a in self.anreisen}:
                self.kennung = kern.erste_offene(self.anreisen)
            self.zeilen = kern.zeilen(self.stand, self.kennung, self.heute)
        try:
            self.ls_maengel = kern._maengel_text()
        except Exception:                      # noqa: BLE001
            self.ls_maengel = {}

    # ---- Rahmen -----------------------------------------------------------------------------

    def aufbauen(self) -> None:
        ui.add_css(CSS)
        ui.add_css(themes.CSS)
        ui.add_css(LS_CSS + _schrift_css())
        self.body = ui.query("body")
        self.body.classes("leitstand pro th-innternat mod-hell hell")   # helle Felder der bisherigen Seiten
        # Ablagen, die Methoden der Basisklasse erwarten – im Leitstand unsichtbar
        with ui.element("div").style("display:none"):
            self.nav = ui.element("div")
            self.topnav = ui.element("div")
            self.titel = ui.label("")
            self.glocke = ui.element("div")
            self.aufgaben_knopf = ui.element("div")
            self.center = ui.element("div")
            self.schleier = ui.element("div")
            self.toolbar = ui.element("div")
        with ui.element("div").classes("ls-app"):
            with ui.element("header").classes("ls-spine"):
                with ui.element("div").classes("ls-marke"):
                    from . import standort_kern

                    ui.html(f"INNternat<small>{standort_kern.aktiv().name} · Leitstand</small>", sanitize=False)
                self.ls_buehnen = ui.element("div").style("display:flex; gap:4px")
                self._spine_buehnen()
                with ui.element("div").classes("ls-omni"):
                    ui.icon("search")
                    self.omni = ui.element("input").props(
                        'placeholder="Suchen: Name, Zimmer, Maßnahme … oder Auftrag eintippen (/)" autocomplete="off"')
                    self.omni_tipp = ui.label("").classes("ls-omni-tipp")
                self.omni.on("input", self._omni_geaendert, js_handler=(
                    "(e) => { const v = e.target.value; clearTimeout(window._lsOmni); "
                    "window._lsOmni = setTimeout(() => emit(v), 120); }"))
                self.omni.on("keydown", self._omni_taste, js_handler=(
                    "(e) => { if (e.key === 'Enter' || e.key === 'Escape') emit({k: e.key, v: e.target.value}); }"))
                self.stand_anzeige = ui.label("").classes("m-datenstand")
                self.undo_knopf = ui.element("button").classes("ls-sknopf undo")
                self.undo_knopf.on("click", self.rueckgaengig)
                attr(self.undo_knopf, title="Letzte Änderung zurücknehmen (Strg+Z)")
                k = ui.element("button").classes("ls-sknopf orange")
                with k:
                    ui.icon("keyboard")
                    ui.label("Abtipp-Modus")
                k.on("click", self._abtipp)
                attr(k, title="Firmenprogramm Eintrag für Eintrag ins Trägersystem übertragen")
                w = ui.element("button").classes("ls-sknopf")
                with w:
                    ui.icon("swap_horiz")
                    ui.label("Klassische Ansicht")
                w.on("click", lambda: umschalten(self))
                attr(w, title="Zur klassischen Oberfläche (Strg+Umschalt+L)")
            self.ls_main = ui.element("main").classes("ls-main")
            with self.ls_main:
                self.spalte1 = ui.element("section").classes("ls-col links")
                with ui.element("section").classes("ls-col mitte"):
                    with ui.element("div").classes("ls-kopf"):
                        self.mitte_titel = ui.label("").classes("ls-titel")
                        self.werkzeuge = ui.element("div").classes("m-werkzeuge")
                    self.leiste = ui.element("div").classes("m-leiste")
                    with ui.element("div").classes("ls-mitte-inhalt"):
                        self.inhalt = ui.element("div").classes("m-inhalt")
                with ui.element("aside").classes("ls-col rechts"):
                    with ui.element("div").classes("ls-insp-k"):
                        self.insp_titel = ui.label("Details").classes("ls-titel")
                        self.insp_zu = knopf("", self._insp_schliessen, "leise", "close", "Schließen (Esc)")
                    self.inspektor = ui.element("div").classes("ls-insp m-formular")
                    self.ungespeichert = ui.label("Ungespeichert – Speichern im Formular, Esc verwirft").classes(
                        "ls-ungespeichert")
            self.fuss = ui.element("footer").classes("ls-fuss")
        self.kuerzel = ui.element("div").classes("ls-kuerzel")
        with self.kuerzel:
            ui.label("Tastenkürzel").style("font-weight:700; color:var(--ls-petrol); margin-bottom:4px")
            for t, w_ in KUERZEL:
                with ui.element("div"):
                    ui.label(w_)
                    ui.html(f"<kbd>{t}</kbd>", sanitize=False)
        self._frage_bauen()
        from .seite_prognose import GRAPH_JS

        ui.add_body_html(GRAPH_JS)
        ui.add_body_html(SORTIER_JS)
        ui.add_body_html(_FOKUS_JS)
        self.toast_box = ui.element("div")
        ui.keyboard(self._taste, ignore=["input", "select", "textarea"])
        from .oberflaeche import PRUEF_S

        ui.timer(PRUEF_S, self.pruefen)
        ui.timer(2.0, self._ungespeichert_pruefen)

    def _spine_buehnen(self) -> None:
        if not hasattr(self, "ls_buehnen"):
            return
        self.ls_buehnen.clear()
        with self.ls_buehnen:
            for key, (nr, titel, _i) in BUEHNEN.items():
                b = ui.element("button").classes("ls-buehne" + (" an" if key == self.buehne else ""))
                with b:
                    ui.html(f"<b>{nr}</b>{titel}", sanitize=False)
                b.on("click", lambda key=key: self.buehne_waehlen(key))
                attr(b, title=f"{titel} (Taste {nr})")

    def _undo_text(self) -> None:
        from belegung import aenderungen

        s = aenderungen.letzter()
        self.undo_knopf.clear()
        with self.undo_knopf:
            ui.icon("undo")
            ui.label(f"Rückgängig: {s.titel}" if s else "Rückgängig").style(
                "overflow:hidden; text-overflow:ellipsis; white-space:nowrap")
        if s:
            attr(self.undo_knopf, title=f"„{s.titel}“ zurücknehmen (Strg+Z)")

    # Methoden der Basisklasse, die im Leitstand nichts zu tun haben
    def _nav_fuellen(self) -> None:
        pass

    def _aufgaben_knopf(self) -> None:
        pass

    def _glocke_fuellen(self) -> None:
        pass

    def _center(self) -> None:
        pass

    def _toolbar_fuellen(self) -> None:
        pass

    def center_umschalten(self, an: bool | None = None) -> None:
        pass

    def _schleier_setzen(self) -> None:
        pass

    # ---- Zeichnen ---------------------------------------------------------------------------

    def zeichnen(self) -> None:
        self._undo_text()
        for c in (self.spalte1, self.werkzeuge, self.leiste, self.inhalt):
            c.clear()
        self.ls_main.classes(remove="breit") if self.buehne == "dispo" else self.ls_main.classes(add="breit")
        if self.buehne == "dispo":
            self._strom()
        else:
            self._arbeitslisten()
        if self.fehler:
            with self.inhalt:
                leer(self.fehler)
        elif self.stand is None or (self.daten is None and self.seite != "anreisen") or (
                self.seite == "anreisen" and self.ansicht_von("anreisen", "zuteilen") != "zuteilen" and self.daten is None):
            with self.inhalt:
                leer("Lädt …")
        elif self.buehne == "dispo" and self.ls_mitte == "etagen":
            self._mitte_kopf_dispo()
            self._matrix()
        else:
            if self.buehne == "dispo":
                self._mitte_kopf_dispo()
            else:
                self.mitte_titel.set_text(self._mitte_titel())
            try:
                if self.seite == "anreisen":
                    self._anreisen()
                else:
                    register.SEITEN[self.seite][1](self)
            except Exception as exc:              # noqa: BLE001 – Fehler sichtbar statt leerer Spalte
                log.exception("Leitstand: Seite zeichnen")
                with self.inhalt:
                    leer(f"Diese Ansicht konnte nicht gezeichnet werden: {exc}")
            # Die Reiter der Seite (Lage | Prognose …, Cockpit | Vorhaben …) stehen links als Liste – nicht doppelt
            if self.buehne in ("radar", "bau") or (self.buehne == "akten" and self.seite == "anreisen"):
                kinder = list(self.werkzeuge.default_slot.children)
                if kinder and "m-segm" in kinder[0].classes:
                    kinder[0].delete()
        self.leiste.set_visibility(bool(self.leiste.default_slot.children))
        if self.panel_def is None:
            self._inspektor_fuellen()
        self._fuss_fuellen()

    def _mitte_titel(self) -> str:
        if self.buehne == "akten":
            return next((t for k, t, _s, _a in AKTEN if k == self.ls_akte), "Akten")
        if self.buehne == "radar":
            return next((t for k, t in RADAR if k == self.ansicht_von("auswertung", "prognose")), "Auswertung")
        return "Bau & Budget"

    # ---- Spalte 1: Arbeitsstrom (Bühne Disposition) -------------------------------------------

    def _text_passt(self, *teile) -> bool:
        t = self.ls_text.strip().lower()
        return not t or any(t in str(x).lower() for x in teile if x)

    def _strom(self) -> None:
        self.ls_reihe = []
        karten = list(self.karten or [])
        dringend = [k for k in karten if k.stufe == "dringend"]
        ohne = sum(max(0, a.personen - a.zugeteilt) for a in (self.anreisen or []))
        reinigung = [k for k in karten if k.id.split(":")[0].startswith("reinigung")]
        with self.spalte1:
            with ui.element("div").classes("ls-puls"):
                for n, text, kl, ziel in ((len(dringend), "dringend", "krit", "karten"), (ohne, "ohne Zimmer", "warn", "anreise"),
                                          (len(reinigung), "Reinigung offen", "", "reinigung")):
                    p = ui.element("button").classes(f"ls-pill {kl if n else ''}")
                    with p:
                        ui.html(f"<b>{n}</b> {text}", sanitize=False)
                    if ziel == "reinigung":
                        p.on("click", lambda: self._mitte_setzen("reinigung"))
            # 1) Sofort klären / als Nächstes
            offen = [k for k in karten if k.stufe in ("dringend", "bald") and self._text_passt(k.titel, k.detail)]
            ui.label(f"Offene Aufgaben · {len(offen)}").classes("ls-gruppe")
            if not offen:
                ui.label("Keine offenen Aufgaben.").classes("ls-leer")
            for k in offen:
                self._eintrag(("karte", k.id), k.stufe, k.titel, k.detail, "")
            # 2) Anreisen zum Zuteilen
            with ui.element("div").classes("ls-gruppe"):
                ui.label("Anreisen")
                if self.anreisen:
                    ui.select({a.kennung: a.text for a in self.anreisen}, value=self.kennung,
                              on_change=self._anreise_gewaehlt).props(
                        'dense borderless options-dense popup-content-class="m-popup"').style("font-size:12px")
            bedarf = {b.schluessel: b for b in (self.stand.bedarf if self.stand else [])}
            zs = [z for z in (self.zeilen or []) if self._text_passt(z.name, z.zweite, z.gruppe, z.gespeichert, z.bemerkung)]
            if not zs:
                ui.label("Keine Personen für diese Auswahl.").classes("ls-leer")
            for z in zs:
                self._person_eintrag(z, bedarf.get(z.schluessel))
            # 3) Zur Info
            info = [k for k in karten if k.stufe == "info" and self._text_passt(k.titel, k.detail)]
            if info:
                ui.label(f"Zur Info · {len(info)}").classes("ls-gruppe")
                for k in info:
                    self._eintrag(("karte", k.id), "info", k.titel, k.detail, "")

    def _eintrag(self, fokus: tuple, stufe: str, t1: str, t2: str, rechts: str, offen: bool = False, badges=None) -> None:
        self.ls_reihe.append(fokus)
        b = ui.element("button").classes("ls-eintrag" + (" an" if self.fokus == fokus else ""))
        with b:
            ui.element("span").classes(f"ls-punkt {stufe}")
            with ui.element("div"):
                with ui.element("div").classes("t1"):
                    ui.label(t1).style("display:inline")
                    if badges:
                        with ui.element("span").classes("ls-badges"):
                            for text, kl, titel in badges:
                                attr(ui.label(text).classes(f"ls-b {kl}"), title=titel)
                if t2:
                    ui.label(t2).classes("t2")
            if rechts:
                ui.label(rechts).classes("z" + (" offen" if offen else ""))
        b.on("click", lambda fokus=fokus: self.fokus_setzen(fokus))

    def _person_eintrag(self, z: kern.Zeile, b) -> None:
        badges = []
        if b is not None:
            if b.geschlecht in ("m", "w", "d"):
                badges.append((b.geschlecht + ("?" if b.geschlecht_geschaetzt else ""), "frage" if b.geschlecht_geschaetzt else "",
                               "Geschlecht aus dem Vornamen geschätzt – bitte prüfen" if b.geschlecht_geschaetzt else "Geschlecht"))
            else:
                badges.append(("?", "frage", "Geschlecht unbekannt"))
            if b.tier:
                badges.append(("🐾", "", "mit Tier"))
        if z.gruppe == "EMR":
            badges.append(("EMR", "", "EMR"))
        for h in z.hinweise or []:
            badges.append(({"allergie": "⚠ Allergie"}.get(h.art, h.text[:14]), "warn" if h.art == "allergie" else "", h.text))
        if z.schluessel in (self.neu or {}):
            badges.append(("NEU", "neu", "in den letzten 7 Tagen neu"))
        rechts = kern.kurz(z.gespeichert) if z.gespeichert else ("→ " + kern.kurz(z.vorschlag) if z.vorschlag else "ohne")
        self._eintrag(("person", z.schluessel), z.stufe, z.name, f"{z.gruppe} · {z.zeitraum}" + (f" · {z.grund}" if z.grund and
                      z.status != "ok" else ""), rechts, not z.gespeichert, badges)

    # ---- Spalte 1: Arbeitslisten (Bühnen 2–4) ---------------------------------------------------

    def _arbeitslisten(self) -> None:
        if self.buehne == "akten":
            liste = [(k, t) for k, t, _s, _a in AKTEN]
            aktiv = self.ls_akte
        elif self.buehne == "radar":
            liste, aktiv = RADAR, self.ansicht_von("auswertung", "prognose")
        else:
            from . import seite_steuerung

            liste, aktiv = BAU, seite_steuerung.ansicht(self)
        with self.spalte1:
            ui.label(BUEHNEN[self.buehne][1]).classes("ls-gruppe")
            for k, t in liste:
                if not self._text_passt(t):
                    continue
                b = ui.element("button").classes("ls-eintrag" + (" an" if k == aktiv else ""))
                with b:
                    ui.element("span").classes("ls-punkt ok" if k == aktiv else "ls-punkt")
                    ui.label(t).classes("t1")
                b.on("click", lambda k=k: self._liste_waehlen(k))
            if self.buehne == "bau":
                ui.label("Die flache „Planen“-Maske (Budget → Vorschlag → Feinjustierung) kommt als nächster Schritt; bis "
                         "dahin hier die bisherige Steuerung.").classes("ls-leer")

    async def _liste_waehlen(self, k: str) -> None:
        if self.buehne == "akten":
            self.ls_akte = k
        elif self.buehne == "radar":
            self.ansicht["auswertung"] = k
        else:
            self.ansicht["steuerung"] = k
        self.panel_def = None
        self._seite_fuer_buehne()
        self.daten = None
        self.zeichnen()
        await self.laden()

    # ---- Spalte 2: Gebäude-Matrix ----------------------------------------------------------

    def _seg(self, werte: dict, aktiv: str, klick) -> None:
        with ui.element("div").classes("ls-seg"):
            for k, t in werte.items():
                b = ui.element("button").classes("an" if k == aktiv else "")
                with b:
                    ui.label(t)
                b.on("click", lambda k=k: klick(k))

    def _mitte_kopf_dispo(self) -> None:
        self.mitte_titel.set_text("Gebäude" if self.ls_mitte == "etagen" else MITTE[self.ls_mitte].split(" ", 1)[1])
        with self.werkzeuge:
            self._seg(MITTE, self.ls_mitte, self._mitte_setzen)
            if self.ls_mitte == "etagen":
                self._seg(LAYER, self.ls_layer, self._layer_setzen)
                if self.zeilen and any(z.vorschlag and not z.gespeichert for z in self.zeilen):
                    knopf("Alle grünen Vorschläge", self._alle_vorschlaege, "gruen", "done_all",
                          "Alle offenen Personen dieser Anreise in ihr vorgeschlagenes Zimmer")

    async def _mitte_setzen(self, m: str) -> None:
        self.ls_mitte = m
        self._seite_fuer_buehne()
        self.daten = None
        self.zeichnen()
        await self.laden()

    def _layer_setzen(self, layer: str) -> None:
        self.ls_layer = layer
        self.zeichnen()

    def _fokus_zeile(self) -> kern.Zeile | None:
        if self.fokus and self.fokus[0] == "person":
            return next((z for z in self.zeilen or [] if z.schluessel == self.fokus[1]), None)
        return None

    def _matrix(self) -> None:
        from belegung import zimmerplan as zp

        st = self.stand
        z_fokus = self._fokus_zeile()
        passend = _klickbar(z_fokus)
        vorschlag = z_fokus.vorschlag if z_fokus else None
        aktuell = z_fokus.gespeichert if z_fokus else None
        tag = self.heute
        bald = tag + timedelta(days=7)
        text = self.ls_text.strip().lower()
        haeuser: dict[str, dict[str, list]] = {}
        for z in st.zimmer:
            if z.aktiv:
                haeuser.setdefault(z.haus, {}).setdefault(z.etage, []).append(z)

        def etage_sort(e: str):
            return (-1, e) if e in ("U", "UG") else (0, e) if e in ("E", "EG") else (1, int(e)) if e.isdigit() else (2, e)

        with self.inhalt, ui.element("div").classes("ls-matrix"):
            if z_fokus:
                ui.label(f"Für {z_fokus.name}: passende Zimmer leuchten, der grüne Rahmen ist der Vorschlag – Klick weist "
                         "zu.").classes("ls-hilfe")
            for haus in sorted(haeuser, key=zp._haus_sort):
                etagen = haeuser[haus]
                frei = sum(1 for zs in etagen.values() for z in zs if st.lage.status_am(z.id, tag)[0] in ("frei", "teilweise"))
                with ui.element("div").classes("ls-haus"):
                    with ui.element("div").classes("ls-haus-k"):
                        ui.label(f"Haus {haus}")
                        ui.label(f"{frei} frei heute · {sum(len(v) for v in etagen.values())} Zimmer").classes("").style(
                            "font-weight:400; color:var(--ls-text3); font-size:12px")
                    for etage in sorted(etagen, key=etage_sort, reverse=True):
                        with ui.element("div").classes("ls-etage"):
                            ui.label(etage).classes("ls-etage-n")
                            with ui.element("div").classes("ls-zellen"):
                                for z in sorted(etagen[etage], key=lambda x: x.nummer):
                                    self._zelle(z, tag, bald, text, passend, vorschlag, aktuell, bool(z_fokus))
            with ui.element("div").classes("ls-legende"):
                for kl, t in (("frei", "frei"), ("belegt", "belegt"), ("geplant", "geplant"), ("gesperrt", "gesperrt")):
                    ui.html(f'<span><i class="ls-z {kl}" style="width:12px;height:10px;padding:0;display:inline-block"></i>{t}'
                            "</span>", sanitize=False)
                ui.html("<span><b style='color:var(--ls-orange)'>!</b> Mangel</span><span>↗ Abreise in 7 Tagen</span>",
                        sanitize=False)

    def _zelle(self, z, tag, bald, text, passend, vorschlag, aktuell, mit_person) -> None:
        st = self.stand
        status, heute_bel = st.lage.status_am(z.id, tag)
        personen = [b for b in heute_bel if b.art in ("belegt", "geplant")]
        abreise = min((b.bis for b in personen if tag <= b.bis <= bald), default=None)
        mangel = self.ls_maengel.get(z.id, "")
        kl = ["ls-z", status]
        if self.ls_layer == "abreise" and abreise:
            kl.append("layer-ab")
        if self.ls_layer == "maengel" and mangel:
            kl.append("layer-mangel")
        if mit_person:
            kl.append("vorschlag" if z.id == vorschlag else "aktuell" if z.id == aktuell else "passt" if z.id in passend else "dim")
        if text and not mit_person:
            treffer = text in z.kurz.lower() or any(text in (b.name or "").lower() for b in personen)
            kl.append("treffer" if treffer else "dim")
        if self.fokus == ("zimmer", z.id):
            kl.append("fokus")
        namen = ", ".join(b.name for b in personen if b.name)
        titel = f"{z.kurz} · {status}" + (f" · {namen}" if namen else "") + (f" · Mangel: {mangel}" if mangel else "") + (
            f" · Abreise {abreise:%d.%m.}" if abreise else "")
        el = ui.element("button").classes(" ".join(kl))
        attr(el, title=titel)
        with el:
            ui.label(z.kurz.split("-", 1)[-1]).classes("n")
            unter = (personen[0].name.split(",")[0][:9] if personen and personen[0].name else
                     {"frei": "frei", "teilweise": "1 frei", "gesperrt": "gesperrt"}.get(status, ""))
            ui.label(unter).classes("s")
            if mangel:
                ui.label("!").classes("mangel")
            if abreise:
                ui.label(f"↗{abreise:%d.%m}").classes("ab")
        el.on("click", lambda z=z: self._zelle_klick(z.id))

    async def _zelle_klick(self, zid: str) -> None:
        zf = self._fokus_zeile()
        if zf is not None and zid in _klickbar(zf) and zid != zf.gespeichert:
            await self._zimmer_gewaehlt(zf, zid)            # dieselbe Zuweisung wie in der Tabelle (mit Rückgängig)
            return
        await self.fokus_setzen(("zimmer", zid))

    # ---- Spalte 3: Inspektor ----------------------------------------------------------------

    async def fokus_setzen(self, fokus: tuple | None) -> None:
        self.fokus = fokus
        self.panel_def = None
        if fokus and fokus[0] == "zimmer":
            from . import seite_zimmer

            await seite_zimmer.karte_oeffnen(self, fokus[1])     # Zimmerkarte der bisherigen Oberfläche → Inspektor
            if self.buehne == "dispo" and self.ls_mitte == "etagen":
                self._nur_mitte_neu()
            return
        self.zeichnen()

    def _nur_mitte_neu(self) -> None:
        self.inhalt.clear()
        self.werkzeuge.clear()
        self._mitte_kopf_dispo()
        self._matrix()
        self.spalte1.clear()
        self._strom()

    def _inspektor_fuellen(self) -> None:
        self.inspektor.clear()
        self.inspektor.classes(remove="ungespeichert")
        self.ungespeichert.classes(remove="an")
        f = self.fokus
        leer = not ((f and f[0] == "karte" and any(x.id == f[1] for x in self.karten))
                    or (f and f[0] == "person" and self._fokus_zeile() is not None))
        # 0.65: In den Bereichen 2–4 klappt die Details-Spalte weg, solange dort nichts steht (mehr Platz für die Mitte)
        self.ls_main.classes(add="ohne-insp") if leer and self.buehne != "dispo" else self.ls_main.classes(remove="ohne-insp")
        with self.inspektor:
            if f and f[0] == "karte" and (k := next((x for x in self.karten if x.id == f[1]), None)):
                self.insp_titel.set_text("Aufgabe")
                self._karte(k)
                return
            if f and f[0] == "person" and (z := self._fokus_zeile()) is not None:
                self.insp_titel.set_text(z.name)
                self._person_inspektor(z)
                return
            self.insp_titel.set_text("Details")
            ui.label("Links eine Aufgabe, Person oder in der Mitte ein Zimmer wählen – hier erscheinen Angaben, Vorschläge "
                     "und alle Formulare. Nichts wird verdeckt.").classes("ls-hilfe")
            if self.buehne == "dispo" and self.stand is not None:
                k = kern.kennzahlen(self.stand, self.heute)
                ui.label(f"Heute: {k['frei']} frei · {k['belegt']} belegt · {k['nicht_nutzbar']} nicht nutzbar").classes("ls-hilfe")

    def _person_inspektor(self, z: kern.Zeile) -> None:
        b = next((x for x in self.stand.bedarf if x.schluessel == z.schluessel), None)
        ui.label(f"{z.gruppe} · {z.zeitraum}" + (f" · {z.zweite}" if z.zweite else "")).classes("ls-hilfe")
        if b is not None and (b.geschlecht_geschaetzt or not b.geschlecht):
            ui.label("Geschlecht " + ("aus dem Vornamen geschätzt" if b.geschlecht else "unbekannt") +
                     " – bitte unter „Angaben“ bestätigen.").classes("ls-warnbanner").style(
                "background:#FFF1E3;color:#8A4600;border-color:#F7D3AC")
        allergie = any(h.art == "allergie" for h in (z.hinweise or []))
        ui.label("Zimmer: " + (kern.kurz(z.gespeichert) if z.gespeichert else "noch keins")).style(
            "font-weight:700; color:var(--ls-petrol)")
        if z.grund and z.status != "ok":
            ui.label(z.grund).classes("ls-hilfe")
        ui.label("Beste Zimmer").classes("ls-gruppe").style("padding-left:0")
        reihen = sorted(z.optionen, key=lambda o: (o.art != "vorschlag", o.art != "aktuell", o.art == "ausnahme"))[:5]
        if not reihen:
            ui.label("Kein passendes Zimmer frei.").classes("ls-hilfe")
        for o in reihen:
            mangel = self.ls_maengel.get(o.zimmer, "")
            with ui.element("div").classes("ls-vorschlag" + (" gruen" if o.art == "vorschlag" else "")):
                with ui.element("div"):
                    ui.label(("✓ " if o.art == "vorschlag" else "") + kern.kurz(o.zimmer)).classes("t1")
                    zusatz = "" if o.text.strip() == kern.kurz(o.zimmer) else o.text
                    zusatz += (" · " if zusatz else "") + (f"Mangel: {mangel}" if mangel else "")
                    if zusatz:
                        ui.label(zusatz).classes("t2")
                if o.zimmer != z.gespeichert:
                    knopf("zuweisen", lambda o=o: self._zimmer_gewaehlt(z, o.zimmer), "gruen" if o.art == "vorschlag" else "",
                          "check")
                else:
                    ui.label("aktuell").classes("t2")
            if allergie and mangel:
                ui.label(f"⚠ Allergiker – im Zimmer {kern.kurz(o.zimmer)} ist ein Mangel offen ({mangel}).").classes(
                    "ls-warnbanner")
        with ui.element("div").classes("m-paktionen"):
            knopf("Angaben bearbeiten …", lambda: seite_anreisen.person_panel(self, z.schluessel), "", "edit")
            knopf("Zimmer prüfen …", lambda: seite_anreisen._zimmer_pruefen(self, z.schluessel), "leise", "search")

    # Formulare der bisherigen Oberfläche erscheinen im Inspektor
    def panel(self, titel: str, bauen, breit: bool = False) -> None:
        weiter = self.panel_def is not None and self.panel_def[0] == titel and self.panel_geaendert()
        self.panel_def = (titel, bauen)
        self.ls_main.classes(remove="ohne-insp")
        self.insp_titel.set_text(titel)
        self.inspektor.clear()
        with self.inspektor:
            bauen()
        self._panel_werte, self._panel_geaendert = self._werte(), weiter

    def panel_zu(self) -> None:
        if self.panel_def is not None:
            self.panel_def = None
            if self.fokus and self.fokus[0] == "zimmer":
                self.fokus = None
            self._inspektor_fuellen()

    def _werte(self) -> dict:
        from nicegui.elements.mixins.value_element import ValueElement

        return {el.id: el.value for el in self.inspektor.descendants() if isinstance(el, ValueElement)}

    def _insp_schliessen(self) -> None:
        if self.panel_def is not None:
            self.panel_schliessen()
        else:
            self.fokus = None
            self.zeichnen()

    def _ungespeichert_pruefen(self) -> None:
        """Gelber Rahmen, solange im Inspektor-Formular etwas Ungespeichertes steht."""
        try:
            offen = self.panel_def is not None and self.panel_geaendert()
        except Exception:                          # noqa: BLE001
            offen = False
        if offen:
            self.inspektor.classes(add="ungespeichert")
            self.ungespeichert.classes(add="an")
        else:
            self.inspektor.classes(remove="ungespeichert")
            self.ungespeichert.classes(remove="an")

    # ---- Omnibar ----------------------------------------------------------------------------

    async def _omni_taste(self, e) -> None:
        d = e.args if isinstance(e.args, dict) else {}
        if d.get("k") == "Escape":
            await self._omni_leeren()
        elif d.get("k") == "Enter":
            await self._omni_enter(str(d.get("v") or ""))

    async def _omni_geaendert(self, e) -> None:
        self.ls_text = e.args if isinstance(e.args, str) else ""
        t = self.ls_text.strip()
        self.omni_tipp.set_text("Enter: an Assistenz" if len(t.split()) >= 3 else "")
        self.spalte1.clear()
        if self.buehne == "dispo":
            self._strom()
            if self.ls_mitte == "etagen" and self.stand is not None:
                self.inhalt.clear()
                self._matrix()
        else:
            self._arbeitslisten()

    async def _omni_enter(self, wert: str = "") -> None:
        t = (wert or self.ls_text or "").strip()
        if not t:
            return
        tl = t.lower()
        # 1) genau ein Zimmer oder eine Person → fokussieren
        if self.stand is not None:
            zimmer = [z for z in self.stand.zimmer if z.aktiv and z.kurz.lower() == tl]
            if zimmer:
                self.buehne, self.ls_mitte = "dispo", "etagen"
                self._seite_fuer_buehne()
                self._spine_buehnen()
                await self.fokus_setzen(("zimmer", zimmer[0].id))
                return
            personen = [z for z in self.zeilen or [] if tl in z.name.lower()]
            if len(personen) == 1:
                await self.fokus_setzen(("person", personen[0].schluessel))
                return
        # 2) sonst ein Auftrag → Assistenz versteht ihn (Mängel, Termine, Umzüge …)
        if len(t.split()) >= 2:
            self.as_text = t
            self.ls_akte = "assistenz"
            await self.oeffnen("assistenz")
            await self._omni_leeren()
            return
        await self.suchen()

    async def _omni_leeren(self) -> None:
        ui.run_javascript("const i = document.querySelector('.ls-omni input'); if (i) { i.value = ''; i.blur(); }")
        self.ls_text = ""
        self.omni_tipp.set_text("")
        self.zeichnen()

    # ---- Abtipp, Tastatur, Fußleiste ----------------------------------------------------------

    async def _abtipp(self) -> None:
        self.ein_abtipp, self.ein_pos = True, 0
        self.ls_akte = "eintragen"
        await self.oeffnen("anreisen", "eintragen")
        await seite_anreisen._schmal(self, True)

    def _fuss_fuellen(self) -> None:
        self.fuss.clear()
        with self.fuss:
            for t, w in FUSS["dispo" if self.buehne == "dispo" else "andere"]:
                ui.html(f"<span><kbd>{t}</kbd>{w}</span>", sanitize=False)
            r = ui.element("button").classes("rechts").style("border:0;background:transparent;font:inherit;cursor:pointer")
            with r:
                ui.html(f"<kbd>?</kbd>alle Kürzel · Leitstand {__version__}", sanitize=False)
            r.on("click", lambda: self.kuerzel.classes(toggle="an"))

    async def _extra_taste(self, e) -> bool:
        """Tasten des Leitstands (vor den allgemeinen). True = erledigt."""
        name = e.key.name
        if e.modifiers.ctrl or e.modifiers.alt or self.panel_def is not None:
            return False
        if name in ("/",):
            ui.run_javascript("document.querySelector('.ls-omni input')?.focus()")
            return True
        if name == "?":
            self.kuerzel.classes(toggle="an")
            return True
        if name in ("1", "2", "3", "4") and not self.ein_abtipp:
            await self.buehne_waehlen({"1": "dispo", "2": "akten", "3": "radar", "4": "bau"}[name])
            return True
        if self.buehne == "dispo" and name in ("ArrowDown", "ArrowUp") and self.ls_reihe:
            i = self.ls_reihe.index(self.fokus) if self.fokus in self.ls_reihe else -1
            i = max(0, min(len(self.ls_reihe) - 1, i + (1 if name == "ArrowDown" else -1)))
            await self.fokus_setzen(self.ls_reihe[i])
            ui.run_javascript("document.querySelector('.ls-eintrag.an')?.scrollIntoView({block:'nearest'})")
            return True
        if self.buehne == "dispo" and name == "Enter" and (z := self._fokus_zeile()) is not None and z.vorschlag \
                and z.vorschlag != z.gespeichert:
            await self._zimmer_gewaehlt(z, z.vorschlag)
            return True
        if name == "Escape" and self.fokus is not None:
            self.fokus = None
            self.zeichnen()
            return True
        return False

    async def suchen(self) -> None:
        ui.run_javascript("document.querySelector('.ls-omni input')?.focus()")


_FOKUS_JS = """<script>
// Leitstand: Strg+K setzt den Fokus in die Omnibar (statt eines Suchfensters)
document.addEventListener('keydown', (e) => {
  if (!document.body.classList.contains('leitstand')) return;
  if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault(); document.querySelector('.ls-omni input')?.focus();
  }
});
</script>"""
