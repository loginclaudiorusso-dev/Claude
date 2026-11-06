"""Arbeitsfläche 0.74 – eine Seitenvorlage für alle Ansichten (Konzept „Arbeitsfläche v2“ + Entwürfe 1–6).

Was hier festgelegt wird (rein, ohne Oberfläche – testbar):

* **Kontextzeile:** Seitenkopf und Leiste bilden im Office-Layout EINE Zeile. Feste Reihenfolge von links nach rechts:
  Titel → Kontext (Datum, Haus, Anreise …) → Filter-Chips → Luft → Suche → Seitenknöpfe → ⋯ → Hauptaktion.
* **Feste Skalen:** sechs Schriftstufen (12–24 px, nur 400/600), Bedienelemente 32 px, Tabellenzeilen je Dichte
  28 / 36 / 44 px, Raster 4 · 8 · 12 · 16 · 24 · 32.
* **Zustand nie nur über Farbe:** jede Statusfarbe hat ein Symbol (und „geplant“ zusätzlich einen gestrichelten Rand).
* **Ein Symbol-Wörterbuch:** eine Bedeutung = ein Symbol, alle aus EINER Familie (Umriss, im Programm enthalten).
* **Detailpanel:** Zimmer- und Personenkarten docken rechts an (420 px), die Liste bleibt sichtbar und bedienbar.

Das CSS greift nur im Office-Layout (``body.lay-office``) – die übrigen Layouts bleiben wie sie sind.
"""

from __future__ import annotations

# Schriftstufen: Größe, Zeilenhöhe, Gewicht
SKALA = {"K": (24, 32, 600, "Kennzahl in Karten"), "T": (16, 24, 600, "Seitentitel"), "A": (14, 20, 600, "Abschnitt"),
         "B": (14, 20, 400, "Text, Tabellen"), "S": (13, 18, 400, "Knöpfe, Chips, Tabellenkopf"),
         "N": (12, 16, 400, "Nebentext, Badges, Statusleiste – Untergrenze")}
ABSTAENDE = (4, 8, 12, 16, 24, 32)
STEUERHOEHE = {"kompakt": 28, "normal": 32, "komfort": 32}
ZEILE = {"kompakt": 28, "normal": 36, "komfort": 44}
KOPFZEILE = {"kompakt": 28, "normal": 32, "komfort": 36}
PANEL_BREITE = 420
PANEL_BREIT = 480
KONTEXTZEILE = 44

# Reihenfolge in der Kontextzeile (CSS „order“) – was eine Seite nicht hat, entfällt; die Reihenfolge bleibt
REIHENFOLGE = {"titel": 0, "kontext": 10, "chips": 20, "luft": 50, "suche": 60, "knoepfe": 70, "mehr": 80, "haupt": 90}

# Statusfarben (hell): Hintergrund, Text/Rand, Symbol – sie wechseln NICHT mit dem Farbschema
STATUS = {
    "frei": ("#E6F4EA", "#1E6B34", "check_circle"),
    "belegt": ("#E3EEFB", "#1F4E8C", "person"),
    "geplant": ("#F1EBFB", "#5B3A9E", "schedule"),
    "warnung": ("#FFF3DD", "#8A4B00", "warning"),
    "dringend": ("#FDE7E7", "#A4161A", "error_outline"),
    "nicht_nutzbar": ("#ECEFEF", "#4F5959", "block"),
}

# Symbol-Wörterbuch: eine Bedeutung = ein Symbol (Material-Umriss-Symbole, im Programm enthalten – auch offline)
SYMBOL = {
    "person": "person", "gruppe": "group", "zimmer": "bed", "haus": "apartment", "termin": "event",
    "zeitraum": "date_range", "anreise": "login", "abreise": "logout", "reinigung": "cleaning_services",
    "mangel": "warning", "dringend": "error_outline", "nicht_nutzbar": "block", "geplant": "schedule",
    "frei": "check_circle", "uebernehmen": "check", "neu": "add", "suche": "search", "filter": "filter_list",
    "mehr": "more_horiz", "bearbeiten": "edit", "mail": "mail", "vertrag": "description", "info": "info",
    "drucken": "print", "exportieren": "ios_share", "schliessen": "close",
}


def mehrzahl(n: int, einzahl: str, mehrzahl_: str) -> str:
    """Grammatik zentral: „1 laufender Vertrag“, „2 laufende Verträge“, „0 laufende Verträge“."""
    return f"{n} {einzahl if n == 1 else mehrzahl_}"


def sichtbare_zeilen(hoehe: int, dichte: str = "normal", band_zu: bool = False) -> int:
    """Wie viele Tabellenzeilen passen in eine App-Höhe (Browserfenster ohne Leisten)? Menüband 168 px (eingeklappt
    72 px), Kontextzeile 44, Abstand 12, Tabellenkopf, Statusleiste 24."""
    oben = (72 if band_zu else 168) + KONTEXTZEILE + 12 + KOPFZEILE.get(dichte, 32)
    return max(0, (hoehe - oben - 24) // ZEILE.get(dichte, 36))


def _status_css() -> str:
    zeilen = []
    for k, (bg, fg, _sym) in STATUS.items():
        zeilen.append(f"--st-{k}-bg: {bg}; --st-{k}: {fg};")
    return " ".join(zeilen)


CSS = r"""
.m-kz { display: contents; }                       /* andere Layouts: Kopf und Leiste wie bisher */
body.lay-office { STATUS_VARS }
/* ---------- Kontextzeile: Kopf + Leiste = EINE Zeile ---------- */
body.lay-office .m-kz { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; min-height: 44px; padding: 6px 16px;
  background: var(--ob-fl); border-bottom: 1px solid var(--rand); flex: none; zoom: var(--m-zoom, 1); position: relative; z-index: 3; }
body.lay-office .m-kz > .m-kopf, body.lay-office .m-kz .m-werkzeuge, body.lay-office .m-kz > .m-leiste { display: contents !important; }
body.lay-office .m-kz .m-kopf > .m-titel { order: 0; font-size: 16px !important; line-height: 24px; font-weight: 600 !important;
  white-space: nowrap; margin-right: 6px; letter-spacing: 0; }
body.lay-office .m-kz .m-werkzeuge > * { order: 10; }
body.lay-office .m-kz .m-leiste > * { order: 20; }
body.lay-office .m-kz .m-kz-luft { order: 50; flex: 1 1 0 !important; min-width: 0; }
body.lay-office .m-kz .m-leiste > .m-sucheingabe { order: 60; }
body.lay-office .m-kz .m-leiste > .m-knopf, body.lay-office .m-kz .m-kz-rechts { order: 70; }
body.lay-office .m-kz .m-kz-mehr { order: 80; }
body.lay-office .m-kz .m-knopf.primaer { order: 90; }
body.lay-office .m-kz .m-segm { margin-left: 0 !important; flex: none; }
body.lay-office .m-kz .m-stats { display: contents; }
body.lay-office .m-kz .m-stats > .m-stat { order: 20; flex: none; }
body.lay-office .m-kz .m-knopf, body.lay-office .m-kz .m-segm, body.lay-office .m-kz .m-tagwahl { margin-left: 0 !important; }
body.lay-office .m-kz .m-tagwahl { display: inline-flex; align-items: center; gap: 2px; flex: none; }
body.lay-office .m-kz .m-tagwahl .m-knopf { width: 32px; padding: 0; justify-content: center; }
body.lay-office .m-kz .m-tagwahl .m-knopf:has(.q-icon + *) { width: auto; padding: 0 10px; }
/* Bedienelemente: alle 32 px, Unterkanten fluchten */
body.lay-office .m-kz .m-knopf { height: 32px; flex: none; font-size: 13px; }
body.lay-office .m-kz .m-segm { height: 32px; align-items: center; padding: 2px; border-radius: 4px; }
body.lay-office .m-kz .m-segm button { height: 26px; font-size: 13px; border-radius: 3px; }
body.lay-office .m-kz .q-field--dense .q-field__control, body.lay-office .m-kz .q-field--dense .q-field__marginal,
body.lay-office .m-kz .q-field--dense .q-field__native { min-height: 32px !important; height: 32px; }
body.lay-office .m-kz .q-field--dense.q-field--float .q-field__label { display: none; }
body.lay-office .m-kz .q-field { flex: none; }
body.lay-office .m-kz .m-sucheingabe { width: 200px !important; }
body.lay-office .m-kz .q-field.m-zimmer { width: 300px !important; min-width: 0 !important; }
body.lay-office .m-kz .m-kpi { font-size: 13px; color: var(--text2); white-space: nowrap; }
body.lay-office .m-kz .m-trennlinie { height: 20px; margin: 0 4px; }
body.lay-office.dichte-kompakt .m-kz { min-height: 36px; padding-top: 2px; padding-bottom: 2px; }
body.lay-office.dichte-kompakt .m-kz .m-knopf, body.lay-office.dichte-kompakt .m-stat { height: 28px; }
/* Filter-Chips: 32 px, rund, Zahl zuerst; Null bleibt GRAU stehen (feste Positionen) */
body.lay-office .m-stat { height: 32px; border-radius: 16px !important; }
body.lay-office .m-stat .z { font-size: 13px !important; font-weight: 600 !important; }
body.lay-office .m-stat .l { font-size: 13px !important; }
body.lay-office .m-stat.null { display: flex; }
body.lay-office .m-stat.null .l, body.lay-office .m-stat.null .z, body.lay-office .m-stat.null .s { color: var(--text3) !important; }
body.lay-office .m-stat.an { background: color-mix(in srgb, var(--ob-akzent) 12%, var(--ob-fl)) !important;
  border-color: var(--ob-akzent) !important; box-shadow: none !important; }
/* ---------- Schrift: eine Skala, keine Monospace, gleich breite Ziffern ---------- */
body.lay-office .m-inhalt { font-size: 14px; line-height: 20px; font-variant-numeric: tabular-nums; }
body.lay-office .m-mono, body.lay-office .m-kpi b, body.lay-office .m-pille, body.lay-office .m-stat .z { font-family: inherit !important; }
body.lay-office .m-zweite, body.lay-office .m-ptext { font-size: 13px; }
body.lay-office .m-btitel, body.lay-office .m-ktitel { font-size: 14px !important; font-weight: 600 !important; text-transform: none !important;
  letter-spacing: 0 !important; }
body.lay-office .m-inhalt *, body.lay-office .m-kz *, body.lay-office .m-center * { text-transform: none !important; }
body.lay-office .m-inhalt .m-tz-kat, body.lay-office .m-inhalt .m-tz-wann, body.lay-office .m-inhalt .m-tz-ab,
body.lay-office .m-inhalt .m-tz-zahl-l, body.lay-office .m-inhalt .m-tz-datum, body.lay-office .m-inhalt .m-btitel { letter-spacing: 0 !important; }
/* ---------- Symbole: EINE Familie (Umriss) ---------- */
body.lay-office .material-icons { font-family: "Material Icons Outlined" !important; }
/* ---------- Tabellen: Zeile 36 / 28 / 44 px, Kopf fest, ruhig ---------- */
body.lay-office .m-zeile { min-height: 36px; }
body.lay-office .m-zeile > div { padding-top: 3px; padding-bottom: 3px; }
body.lay-office.dichte-kompakt .m-zeile { min-height: 28px; }
body.lay-office.dichte-kompakt .m-zeile > div { padding-top: 1px; padding-bottom: 1px; font-size: 13px; }
body.lay-office.dichte-komfort .m-zeile { min-height: 44px; }
body.lay-office .m-tkopf { background: var(--ob-band, var(--fl)) !important; }
body.lay-office .m-tkopf > * { font-size: 13px !important; font-weight: 600 !important; color: var(--text) !important;
  text-transform: none !important; letter-spacing: 0 !important; }
body.lay-office .m-inhalt table th { position: sticky; top: 0; z-index: 1; background: var(--ob-band, var(--fl)); font-size: 13px; font-weight: 600; }
body.lay-office .m-inhalt table td { height: 36px; }
body.lay-office.dichte-kompakt .m-inhalt table td { height: 28px; }
body.lay-office.dichte-komfort .m-inhalt table td { height: 44px; }
/* ---------- Status: Farbe + Symbol + Wort (+ Form) ---------- */
body.lay-office .m-badge { height: 22px; border-radius: 11px; font-size: 12px; font-weight: 600; }
body.lay-office .m-badge.akzent { border: 1px dashed currentColor; }                       /* geplant: gestrichelt */
/* ---------- Menüband einklappen (Strg+F1) – beim Zeigen auf die Registerkarten klappt es schwebend auf ---------- */
body.lay-office.band-zu .m-ob { position: relative; }
body.lay-office.band-zu .m-ob-band { display: none; }
body.lay-office.band-zu .m-ob-reiter:hover ~ .m-ob-band, body.lay-office.band-zu .m-ob-band:hover {
  display: flex; position: absolute; left: 0; right: 0; top: 100%; z-index: 60; box-shadow: 0 6px 18px rgba(0,0,0,.16); }
body.lay-office.band-zu .m-ob-reiter { border-bottom: 1px solid var(--ob-rand); }
/* ---------- Detailpanel rechts: angedockt, Liste bleibt sichtbar (kein Abdunkeln) ---------- */
body.lay-office .m-schleier { display: none !important; }
body.lay-office .m-center, body.lay-office .m-center.offen { position: fixed !important; top: var(--af-oben, 216px) !important;
  right: 0; bottom: 24px !important; height: auto !important; width: var(--af-pb, PANEL_BREITEpx) !important; z-index: 25;
  background: var(--ob-fl) !important; border-left: 1px solid var(--rand) !important; border-radius: 0 !important;
  box-shadow: -2px 0 8px rgba(0,0,0,.05) !important; backdrop-filter: none !important; transition: none !important; }
body.lay-office .m-center:not(.offen) { transform: translateX(110%) !important; visibility: hidden; }
body.lay-office .m-center.offen { transform: none !important; visibility: visible; }
body.lay-office .m-center.offen.breit, body.lay-office .m-center.breit { width: var(--af-pb, PANEL_BREITpx) !important; }
body.lay-office:has(.m-center.offen) .m-inhalt { margin-right: var(--af-pb, PANEL_BREITEpx); }
body.lay-office:has(.m-center.offen.breit) .m-inhalt { margin-right: var(--af-pb, PANEL_BREITpx); }
body.lay-office .m-center .m-ckopf { min-height: 44px; padding: 6px 8px 6px 16px; }
body.lay-office .m-center .m-ckopf .m-titel { font-size: 16px; font-weight: 600; }
/* ---------- Heute: Sprung-Kacheln · links Aufgaben 60 % · rechts freie Zimmer, 7 Tage, Outlook ---------- */
body.lay-office .m-tz { padding: 12px 16px 24px !important; gap: 16px; max-width: none; }
body.lay-office .m-tz-zahlen { display: grid !important; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px !important;
  margin: 0 !important; }
body.lay-office .m-tz-zahl-k { position: relative; display: block !important; height: auto !important; padding: 10px 40px 10px 16px !important;
  border-radius: 8px !important; border: 1px solid var(--rand) !important; background: var(--ob-fl) !important; text-align: left; }
body.lay-office .m-tz-zahl-k:hover { border-color: var(--ob-akzent) !important; }
body.lay-office .m-tz-zahl-k::after { content: "chevron_right"; font-family: "Material Icons Outlined"; font-feature-settings: "liga";
  font-size: 20px; position: absolute; right: 12px; top: 50%; transform: translateY(-50%); color: var(--text3); }
body.lay-office .m-tz-zahl-k .m-tz-zahl { display: block; font-size: 24px !important; line-height: 32px; font-weight: 600 !important; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-t { display: block !important; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-l { font-size: 14px !important; font-weight: 400 !important; color: var(--text) !important; }
body.lay-office .m-tz-zahl-k .m-tz-zahl-u { display: block !important; font-size: 12px; line-height: 16px; color: var(--text2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
body.lay-office .m-tz-zahl-k.null { opacity: 1 !important; }
body.lay-office .m-tz-raster { grid-template-columns: minmax(0, 3fr) minmax(320px, 2fr) !important; gap: 16px !important; }
body.lay-office .m-tz-links, body.lay-office .m-tz-rechts > section, body.lay-office .m-tz-rechts > div {
  background: var(--ob-fl); border: 1px solid var(--rand); border-radius: 8px; padding: 12px 16px; }
body.lay-office .m-tz-rechts { gap: 16px !important; }
body.lay-office .m-tz-ab { font-size: 14px !important; font-weight: 600 !important; color: var(--text) !important; align-items: center !important; }
body.lay-office .m-tz-meta { font-size: 12px; font-weight: 400; color: var(--text2); }
body.lay-office .m-tz-punkt { padding: 8px 4px 8px 8px !important; gap: 12px !important; grid-template-columns: 28px minmax(0, 1fr) auto !important; }
body.lay-office .m-tz-nr { font-size: 16px !important; }
body.lay-office .m-tz-ptitel { font-size: 14px !important; font-weight: 600; }
body.lay-office .m-tz-pdetail, body.lay-office .m-tz-kat { font-size: 12px !important; }
body.lay-office .m-tz-rechts .m-tz-wochen { display: flex !important; flex-direction: column; gap: 4px !important; }
body.lay-office .m-tz-rechts .m-tz-woche { display: grid !important; grid-template-columns: 56px minmax(0, 1fr) auto; align-items: center; gap: 10px !important; }
body.lay-office .m-tz-rechts .m-tz-wkopf { display: contents !important; }
body.lay-office .m-tz-rechts .m-tz-wkopf > .m-zweite { order: 1; font-size: 13px; }
body.lay-office .m-tz-rechts .m-tz-balken { order: 2; }
body.lay-office .m-tz-rechts .m-tz-wfrei { order: 3; justify-self: end; font-size: 13px; font-weight: 600; white-space: nowrap; }
body.lay-office .m-tz-rechts .m-tz-wunter { display: none; }
body.lay-office .m-tz-wann { font-size: 13px !important; font-weight: 400 !important; }
@media (max-width: 1100px) {   /* schmal: Panel liegt über der Liste statt daneben */
  body.lay-office:has(.m-center.offen) .m-inhalt { margin-right: 0; } }
@media print { body.lay-office .m-inhalt { margin-right: 0 !important; } }
/* ---------- 0.75 Symbolstil: Linie (Standard) · Gefüllt · Rund – immer EINE Familie ---------- */
body.lay-office.sym-gefuellt .material-icons { font-family: "Material Icons" !important; }
body.lay-office.sym-rund .material-icons { font-family: "Material Icons Round" !important; }
/* ---------- 0.75 Knopfstil – gilt für alle Knöpfe und Chips gleichzeitig ---------- */
body.lay-office.knopf-weich .m-knopf { border-radius: 8px !important; }
body.lay-office.knopf-weich .m-knopf:not(.primaer):not(.leise) { border-color: transparent !important;
  background: color-mix(in srgb, var(--ob-akzent) 10%, var(--ob-fl)) !important; }
body.lay-office.knopf-weich .m-stat:not(.an) { border-color: transparent !important; background: color-mix(in srgb, var(--ob-akzent) 7%, var(--ob-fl)) !important; }
body.lay-office.knopf-kontur .m-knopf { border-radius: 6px !important; }
body.lay-office.knopf-kontur .m-knopf.primaer { background: transparent !important; color: var(--ob-akzent) !important;
  border: 1.5px solid var(--ob-akzent) !important; }
body.lay-office.knopf-kontur .m-knopf.primaer:hover { background: var(--ob-akzent) !important; color: #fff !important; }
body.lay-office.knopf-kontur .m-stat { background: transparent !important; }
body.lay-office.knopf-kraeftig .m-knopf { border-radius: 16px !important; }
body.lay-office.knopf-kraeftig .m-knopf.primaer { box-shadow: 0 1px 3px rgba(0,0,0,.25) !important; }
body.lay-office.knopf-kraeftig .m-knopf:not(.primaer):not(.leise) { border-color: transparent !important;
  background: color-mix(in srgb, var(--ob-text) 7%, var(--ob-fl)) !important; }
body.lay-office.knopf-kraeftig .m-stat:not(.an) { border-color: transparent !important; background: color-mix(in srgb, var(--ob-text) 6%, var(--ob-fl)) !important; }
/* ---------- 0.75 Hoher Kontrast: schwarz auf weiß, kräftige Ränder, deutlicher Fokus (Beamer, schwache Monitore) ---------- */
body.lay-office.kontrast { --text: #000 !important; --text2: #1A1A1A !important; --text3: #333 !important; --rand: #000 !important;
  --rand2: #000 !important; --bg: #FFF !important; --fl: #FFF !important; --fl2: #F2F2F2 !important; --ob-text: #000 !important;
  --ob-text2: #1A1A1A !important; --ob-rand: #000 !important; --ob-fl: #FFF !important; --ob-band: #FFF !important; }
body.lay-office.kontrast .m-knopf, body.lay-office.kontrast .m-stat, body.lay-office.kontrast .m-badge,
body.lay-office.kontrast .q-field__control { border: 2px solid #000 !important; }
body.lay-office.kontrast .m-zeile, body.lay-office.kontrast .m-tkopf { border-bottom: 1px solid #000 !important; }
body.lay-office.kontrast *:focus-visible { outline: 3px solid #000 !important; outline-offset: 2px !important; }
body.lay-office.kontrast .m-zweite, body.lay-office.kontrast .m-ptext { color: #1A1A1A !important; }
""".replace("STATUS_VARS", _status_css()).replace("PANEL_BREITE", str(PANEL_BREITE)).replace("PANEL_BREIT", str(PANEL_BREIT))

# Oberkante des Detailpanels = Unterkante der Kontextzeile (Menüband kann wachsen, einklappen oder zoomen)
JS = """<script>
(() => {
  const setz = () => {
    const kz = document.querySelector('.m-kz'), tn = document.querySelector('.m-topnav');
    const el = (kz && kz.getBoundingClientRect().height > 0) ? kz : tn; if (!el) return;
    const y = Math.round(el.getBoundingClientRect().bottom) + 'px';
    if (document.documentElement.style.getPropertyValue('--af-oben') !== y) document.documentElement.style.setProperty('--af-oben', y);
  };
  setInterval(setz, 300); window.addEventListener('resize', setz);
})();
</script>"""
