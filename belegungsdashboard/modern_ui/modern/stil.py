"""Design-Tokens und Stil der neuen Oberfläche (dunkel, ruhig, wenige Akzente). Alle Farben nur hier."""

T = {
    "bg": "#0E0F12",          # Fenster
    "fl": "#15171C",          # Flächen (Seitenleiste, Center)
    "fl2": "#1B1E24",         # Hover, Eingabefelder
    "rand": "#262A32",
    "rand2": "#323743",
    "text": "#E6E8EC",
    "text2": "#A2A8B4",
    "text3": "#6E7582",
    "akzent": "#7C8CFF",      # einziger Akzent (Auswahl, Hauptknopf)
    "akzent_text": "#0E0F12",
    "rot": "#F2706B",
    "orange": "#E9A15A",
    "gruen": "#4CC38A",
}

CSS = """
:root {
  --bg: %(bg)s; --fl: %(fl)s; --fl2: %(fl2)s; --rand: %(rand)s; --rand2: %(rand2)s;
  --text: %(text)s; --text2: %(text2)s; --text3: %(text3)s;
  --akzent: %(akzent)s; --akzent-text: %(akzent_text)s;
  --rot: %(rot)s; --orange: %(orange)s; --gruen: %(gruen)s;
  --r: 6px;
  --schrift: "Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
}
html, body, .q-layout, .q-page-container { background: var(--bg) !important; color: var(--text); }
body { font-family: var(--schrift); font-size: 13.5px; letter-spacing: -0.005em; -webkit-font-smoothing: antialiased; }
.nicegui-content { padding: 0 !important; gap: 0 !important; }
* { scrollbar-width: thin; scrollbar-color: var(--rand2) transparent; }

/* Rahmen */
.m-app { display: flex; height: 100vh; width: 100%; overflow: hidden; }
.m-nav { width: 216px; flex: none; background: var(--fl); border-right: 1px solid var(--rand); display: flex; flex-direction: column; padding: 14px 10px; gap: 2px; }
.m-marke { display: flex; align-items: center; gap: 10px; padding: 4px 8px 16px; font-weight: 600; }
.m-logo { width: 22px; height: 22px; border-radius: 6px; background: var(--akzent); color: var(--akzent-text); display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.m-navpunkt { display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: var(--r); color: var(--text2); cursor: default; }
.m-navpunkt.aktiv { background: var(--fl2); color: var(--text); }
.m-navpunkt .material-icons { font-size: 17px; }
.m-navgruppe { font-size: 11px; color: var(--text3); padding: 14px 8px 4px; }
.m-navfuss { margin-top: auto; font-size: 11.5px; color: var(--text3); padding: 8px; line-height: 1.5; }
.m-haupt { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.m-kopf { display: flex; align-items: center; gap: 10px; padding: 12px 20px; border-bottom: 1px solid var(--rand); min-height: 54px; }
.m-titel { font-size: 15px; font-weight: 600; }
.m-trenn { color: var(--text3); }
.m-leiste { display: flex; align-items: center; gap: 18px; padding: 10px 20px; border-bottom: 1px solid var(--rand); flex-wrap: wrap; }
.m-kpi { color: var(--text2); font-variant-numeric: tabular-nums; }
.m-kpi b { color: var(--text); font-weight: 600; }
.m-kpi .m-punktt { color: var(--text3); margin: 0 8px; }
.m-inhalt { flex: 1; overflow: auto; }

/* Knöpfe */
.m-knopf { font: inherit; font-size: 13px; display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border-radius: var(--r);
  border: 1px solid var(--rand2); background: var(--fl); color: var(--text); cursor: pointer; white-space: nowrap; transition: background .12s, border-color .12s; }
.m-knopf:hover { background: var(--fl2); border-color: #3C4250; }
.m-knopf:focus-visible { outline: 2px solid var(--akzent); outline-offset: 1px; }
.m-knopf.primaer { background: var(--akzent); border-color: var(--akzent); color: var(--akzent-text); font-weight: 600; }
.m-knopf.primaer:hover { filter: brightness(1.08); }
.m-knopf.leise { border-color: transparent; background: transparent; color: var(--text2); }
.m-knopf.leise:hover { background: var(--fl2); color: var(--text); }
.m-knopf.gruen { border-color: color-mix(in srgb, var(--gruen) 45%, transparent); background: color-mix(in srgb, var(--gruen) 12%, transparent); color: var(--gruen); height: 24px; padding: 0 8px; font-size: 12.5px; }
.m-knopf.gruen:hover { background: color-mix(in srgb, var(--gruen) 20%, transparent); }
.m-knopf .material-icons { font-size: 16px; }
.m-zahl { font-size: 11.5px; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px;
  display: inline-grid; place-items: center; background: var(--fl2); color: var(--text2); }
.m-zahl.rot { background: var(--rot); color: #16090A; }
.m-taste { font-size: 11px; color: var(--text3); border: 1px solid var(--rand2); border-radius: 4px; padding: 0 4px; }

/* Segmented Control */
.m-segm { display: inline-flex; background: var(--fl); border: 1px solid var(--rand); border-radius: 7px; padding: 2px; gap: 2px; margin-left: auto; }
.m-segm button { font: inherit; font-size: 12.5px; border: 0; background: transparent; color: var(--text2); height: 24px; padding: 0 10px; border-radius: 5px; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.m-segm button:hover { color: var(--text); }
.m-segm button.an { background: var(--fl2); color: var(--text); box-shadow: inset 0 0 0 1px var(--rand2); }
.m-segm .n { color: var(--text3); font-variant-numeric: tabular-nums; }

/* Tabelle */
.m-raster { display: grid; grid-template-columns: 28px minmax(140px, 1.3fr) 56px 132px minmax(150px, 210px) minmax(0, 1.7fr); }
.m-tkopf { position: sticky; top: 0; z-index: 1; background: var(--bg); border-bottom: 1px solid var(--rand); }
.m-tkopf > div { font-size: 11.5px; color: var(--text3); padding: 8px 8px; font-weight: 500; }
.m-zeile { border-bottom: 1px solid var(--rand); align-items: center; min-height: 46px; }
.m-zeile:hover { background: color-mix(in srgb, var(--fl2) 55%, transparent); }
.m-zeile > div { padding: 6px 8px; min-width: 0; }
.m-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-zweite { font-size: 12px; color: var(--text3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-mono { font-variant-numeric: tabular-nums; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-ampel { width: 7px; height: 7px; border-radius: 50%; margin-left: 14px; flex: none; }
.m-ampel.ok { background: var(--gruen); } .m-ampel.warn { background: var(--orange); } .m-ampel.krit { background: var(--rot); }
.m-hinweis { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--text2); min-width: 0; }
.m-hinweis .t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-hinweis.krit .t { color: var(--rot); } .m-hinweis.warn .t { color: var(--orange); }
.m-leer { padding: 60px 20px; text-align: center; color: var(--text3); }

/* Zimmer-Auswahl (Quasar q-select) */
.m-zimmer .q-field__control { min-height: 30px !important; height: 30px; border-radius: var(--r) !important; background: var(--fl) !important; padding: 0 8px !important; }
.m-zimmer .q-field__control:before { border-color: var(--rand2) !important; }
.m-zimmer .q-field__native, .m-zimmer .q-field__input { min-height: 28px !important; padding: 0 !important; color: var(--text) !important; font-variant-numeric: tabular-nums; }
.m-zimmer .q-field__append { height: 30px !important; }
.m-zimmer.konflikt .q-field__control:before { border-color: var(--rot) !important; }
.m-zimmer.konflikt .q-field__control { background: color-mix(in srgb, var(--rot) 9%, var(--fl)) !important; }
.m-zimmer.offen .q-field__native span { color: var(--text3); }
.m-popup { background: var(--fl) !important; border: 1px solid var(--rand2); border-radius: 8px !important; }
.m-popup .q-item { min-height: 30px; font-size: 13px; color: var(--text); }
.m-popup .q-item.q-manual-focusable--focused, .m-popup .q-item:hover { background: var(--fl2); }
.m-mitvorschlag .q-item:first-child, .m-mitvorschlag .q-item:first-child .q-item__label { color: var(--gruen) !important; }

/* Aufgaben-Center (Slide-over rechts, schiebt die Tabelle statt sie zu verdecken) */
.m-center { width: 0; flex: none; overflow: hidden; background: var(--fl); border-left: 1px solid transparent; transition: width .2s ease; display: flex; flex-direction: column; }
.m-center.offen { width: 392px; border-left-color: var(--rand); }
@media (prefers-reduced-motion: reduce) { .m-center { transition: none; } }
.m-ckopf { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border-bottom: 1px solid var(--rand); min-height: 54px; min-width: 392px; }
.m-ckopf .m-titel { flex: 1; }
.m-cinhalt { overflow-y: auto; padding: 10px 12px 20px; display: flex; flex-direction: column; gap: 8px; min-width: 392px; }
.m-cgruppe { font-size: 11.5px; color: var(--text3); padding: 8px 2px 0; }
.m-karte { border: 1px solid var(--rand); border-radius: 8px; padding: 11px 12px; display: flex; flex-direction: column; gap: 6px; background: var(--bg); }
.m-karte .k1 { display: flex; gap: 8px; align-items: flex-start; font-weight: 500; line-height: 1.35; }
.m-karte .k1 .m-ampel { margin: 6px 0 0; flex: none; }
.m-karte .k2 { color: var(--text2); font-size: 12.5px; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; padding-left: 15px; }
.m-karte .k3 { display: flex; gap: 6px; flex-wrap: wrap; padding-left: 15px; padding-top: 2px; align-items: center; }
.m-karte .k4 { font-size: 12px; color: var(--text3); }
.m-kopf .m-knopf { flex: none; }
.m-cleer { text-align: center; color: var(--text3); padding: 40px 10px; line-height: 1.6; }

/* Toast unten mittig, nur für eigene Aktionen */
.m-toast { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 50; display: flex; align-items: center; gap: 12px;
  background: #F1F2F5; color: #121418; border-radius: 8px; padding: 7px 8px 7px 14px; box-shadow: 0 10px 30px rgba(0,0,0,.45); font-size: 13px; max-width: calc(100vw - 40px); }
.m-toast.fehler { background: var(--rot); color: #16090A; }
.m-toast .m-knopf { height: 26px; background: transparent; color: inherit; border-color: rgba(0,0,0,.25); }
"""
for _k, _v in T.items():
    CSS = CSS.replace(f"%({_k})s", _v)

CSS += """
/* Navigation als Knöpfe */
.m-navliste { display: flex; flex-direction: column; gap: 2px; }
button.m-navpunkt { font: inherit; border: 0; background: transparent; text-align: left; width: 100%; cursor: pointer; }
button.m-navpunkt:hover { background: var(--fl2); color: var(--text); }
button.m-navpunkt:focus-visible { outline: 2px solid var(--akzent); outline-offset: -2px; }
.m-werkzeuge { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 0 1 auto; overflow-x: auto; scrollbar-width: none; }
.m-segm button { white-space: nowrap; flex: none; }
.m-werkzeuge .m-segm, .m-leiste .m-segm + .m-segm { margin-left: 0; }
.m-kopf .m-titel { flex: none; }

/* Allgemein */
.m-leer { white-space: pre-line; line-height: 1.7; }
.m-zeile.fertig { opacity: .5; }
.m-pille { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 10px; background: var(--fl2); color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.m-pille.krit { background: color-mix(in srgb, var(--rot) 16%, transparent); color: var(--rot); }
.m-pille.warn { background: color-mix(in srgb, var(--orange) 16%, transparent); color: var(--orange); }
.m-pille.ok { background: color-mix(in srgb, var(--gruen) 14%, transparent); color: var(--gruen); }
.m-ampel.neutral { background: var(--text3); } .m-ampel.akzent { background: var(--akzent); }
.m-haken { width: 20px; height: 20px; border-radius: 5px; border: 1px solid var(--rand2); background: transparent; color: transparent; display: grid; place-items: center; cursor: pointer; margin-left: 6px; padding: 0; }
.m-haken .material-icons { font-size: 15px; }
.m-haken:hover { border-color: var(--gruen); color: color-mix(in srgb, var(--gruen) 60%, transparent); }
.m-haken.an { background: var(--gruen); border-color: var(--gruen); color: #0B1A12; }
.m-abschnitt { font-size: 12px; color: var(--text3); padding: 22px 20px 8px; }
.m-zwei { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; padding: 20px; align-items: start; }
.m-block { border: 1px solid var(--rand); border-radius: 10px; padding: 16px 18px; background: var(--fl); display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.m-btitel { font-weight: 600; font-size: 14px; }
.m-ptext { color: var(--text2); font-size: 12.5px; line-height: 1.5; }
.m-dl { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 10px; padding: 7px 0; border-top: 1px solid var(--rand); }
.m-dl .k { color: var(--text3); }
.m-dl .v { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-einst { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 6px 0; border-top: 1px solid var(--rand); }
.m-legende { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text3); }
.m-legende i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-left: 8px; }

/* Formulare im Panel */
.m-formular { gap: 12px !important; padding: 14px !important; }
.m-paktionen { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 4px; }
.m-feld { width: 100%; }
.m-feld.klein { width: 90px; }
.m-feld .q-field__control { background: var(--bg) !important; border-radius: var(--r) !important; }
.m-feld .q-field__control:before { border-color: var(--rand2) !important; }
.m-feld .q-field__label { color: var(--text3) !important; }
.m-feld textarea { min-height: 220px; font-size: 13px; line-height: 1.5; }
.m-plan-liste { display: flex; flex-direction: column; gap: 8px; }
.m-plan-u { border: 1px solid var(--rand); border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 3px; background: var(--bg); }
.m-plan-u .m-zweite { white-space: normal; }

/* Zeitstrahl */
.m-zs-wrap { padding: 0 20px 24px; min-width: 760px; }
.m-zs { --lab: 128px; font-size: 12px; }
.m-zs-kopf, .m-zs-zeile { display: grid; grid-template-columns: var(--lab) 1fr; }
.m-zs-kopf { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--rand); height: 40px; }
.m-zs-spur { position: relative; }
.m-zs-tag { position: absolute; top: 4px; width: calc(100% / var(--tage)); text-align: center; color: var(--text3); font-size: 11px; line-height: 1.25; font-variant-numeric: tabular-nums; }
.m-zs-tag.we { color: color-mix(in srgb, var(--text3) 60%, transparent); }
.m-zs-tag.heute { color: var(--akzent); font-weight: 700; }
.m-zs-zeile { height: 30px; border-bottom: 1px solid color-mix(in srgb, var(--rand) 60%, transparent); }
.m-zs-zeile:hover { background: color-mix(in srgb, var(--fl2) 50%, transparent); }
.m-zs-lab { display: flex; align-items: center; gap: 4px; padding-right: 10px; color: var(--text2); white-space: nowrap; overflow: hidden; }
.m-zs-lab b { color: var(--text); font-weight: 500; font-variant-numeric: tabular-nums; }
.m-zs-h { color: var(--orange); font-size: 10px; margin-left: 4px; cursor: help; }
.m-zs-we { position: absolute; top: 0; bottom: 0; width: calc(100% / var(--tage)); background: color-mix(in srgb, var(--fl2) 55%, transparent); }
.m-zs-jetzt { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--akzent); opacity: .7; }
.m-zs-b { position: absolute; top: 5px; height: 20px; border-radius: 5px; margin-left: 1px; padding: 0 6px; display: flex; align-items: center; overflow: hidden; font-size: 11.5px; cursor: default; }
.m-zs-b span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-zs-b.ol { border-top-left-radius: 0; border-bottom-left-radius: 0; }
.m-zs-b.or { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.m-zs-b.belegt, .m-legende i.belegt { background: #2A3350; color: #C9D1F5; }
.m-zs-b.geplant, .m-legende i.geplant { background: color-mix(in srgb, var(--akzent) 22%, transparent); color: var(--text); box-shadow: inset 0 0 0 1px var(--akzent); }
.m-zs-b.gesperrt, .m-legende i.gesperrt { background: repeating-linear-gradient(135deg, #2A2D34 0 6px, #22252B 6px 12px); color: var(--text3); }
.m-zs-b.konflikt, .m-legende i.konflikt { background: color-mix(in srgb, var(--rot) 22%, transparent); color: var(--rot); box-shadow: inset 0 0 0 1px var(--rot); }

/* Auswertung */
.m-aw-tab { display: grid; grid-template-columns: minmax(170px, 1.4fr) 44px minmax(120px, 2fr) 44px 54px; gap: 6px 10px; align-items: center; font-variant-numeric: tabular-nums; }
.m-aw-tab .k { font-size: 11.5px; color: var(--text3); }
.m-aw-kw { display: flex; align-items: center; color: var(--text2); white-space: nowrap; min-width: 0; }
.m-aw-balken { display: grid; grid-template-columns: 1fr 44px; gap: 8px; align-items: center; }
.m-spur { height: 8px; border-radius: 4px; background: var(--fl2); overflow: hidden; }
.m-bar { height: 8px; border-radius: 4px; }
.m-bar.ok { background: var(--gruen); } .m-bar.warn { background: var(--orange); }
.m-bar.krit { background: var(--rot); } .m-bar.akzent { background: var(--akzent); }
.m-aw-haus { display: grid; grid-template-columns: minmax(70px, 130px) 1fr; gap: 4px 50px; align-items: center; padding: 8px 0; border-top: 1px solid var(--rand); }
.m-aw-haus .m-zweite { grid-column: 2; }
"""

CSS += """
/* Heute */
.m-heute { display: grid; grid-template-columns: minmax(360px, 1.15fr) minmax(320px, 1fr); gap: 20px; padding: 20px; align-items: start; }
@media (max-width: 1100px) { .m-heute { grid-template-columns: 1fr; } }
.m-heute-links, .m-heute-rechts { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.m-liste-zeile { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 7px 4px; border-top: 1px solid var(--rand);
  font: inherit; color: inherit; background: transparent; border-left: 0; border-right: 0; border-bottom: 0; text-align: left; width: 100%; }
button.m-liste-zeile { cursor: pointer; border-radius: 0; }
button.m-liste-zeile:hover { background: var(--fl2); }
.m-neu { display: grid; grid-template-columns: 12px 1fr; gap: 8px; padding: 6px 0; border-top: 1px solid var(--rand); }

/* Suche */
.m-palette { width: min(640px, 92vw); background: var(--fl); border: 1px solid var(--rand2); border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,.55); overflow: hidden; margin-top: 8vh; }
.m-palette-ein { padding: 6px 14px; border-bottom: 1px solid var(--rand); }
.m-palette-ein input { font-size: 15px !important; color: var(--text) !important; }
.m-palette-liste { max-height: 56vh; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; }
.m-palette-z { font: inherit; text-align: left; border: 0; background: transparent; color: var(--text); padding: 7px 10px; border-radius: 7px; cursor: pointer; display: grid; gap: 1px; }
.m-palette-z:hover, .m-palette-z.an { background: var(--fl2); }
.m-suche { margin-top: 10px; border: 1px solid var(--rand) !important; }
.q-dialog__backdrop { background: rgba(0,0,0,.45) !important; }
"""

CSS += """
/* Zimmer */
.m-center.offen.breit { width: 480px; }
.m-center.breit .m-ckopf, .m-center.breit .m-cinhalt { min-width: 480px; }
.m-ktitel { font-size: 11.5px; color: var(--text3); padding-top: 8px; text-transform: none; }
.m-mangel { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px solid var(--rand); }
.m-notiz { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 8px; padding: 6px 0 6px 10px; border-left: 2px solid var(--rand2); }
.m-notiz .m-zweite { grid-column: 1; }
.m-notiz .m-knopf { grid-row: 1 / span 2; grid-column: 2; }
.m-klick { cursor: pointer; }
.m-krit { color: var(--rot) !important; } .m-warn { color: var(--orange) !important; }
.m-zs-lab, .m-zs-b { cursor: pointer; }
.m-zs-punkt { width: 10px; height: 10px; border-radius: 3px; background: #2A3350; }
.m-zs-punkt.geplant { background: color-mix(in srgb, var(--akzent) 40%, transparent); }
.m-zs-punkt.gesperrt { background: #3A3D44; }
.m-sucheingabe { width: 220px !important; }
.m-leiste { flex-wrap: wrap; row-gap: 8px; }
"""

CSS += """
/* Auswertung */
.m-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; padding: 20px 20px 0; }
.m-kpikarte { border: 1px solid var(--rand); border-radius: 10px; padding: 12px 14px; background: var(--fl); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.m-kpiwert { font-size: 24px; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.m-chart { height: 300px !important; width: 100%; }
"""

CSS += """
.m-link { cursor: pointer; }
.m-link:hover { text-decoration: underline; text-decoration-color: var(--text3); text-underline-offset: 3px; }
.m-menue { background: var(--fl) !important; border: 1px solid var(--rand2); border-radius: 8px !important; }
.m-menue .q-item { min-height: 32px; font-size: 13px; color: var(--text); }
.m-menue .q-separator { background: var(--rand); }
"""

CSS += """
.m-zweispaltig { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
/* Termine: Monat */
.m-monat { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 1px; background: var(--rand); margin: 16px 20px; border: 1px solid var(--rand); border-radius: 10px; overflow: hidden; }
.m-monat-kopf { background: var(--fl); padding: 6px 8px; font-size: 11.5px; color: var(--text3); }
.m-monat-tag { background: var(--bg); min-height: 104px; padding: 6px; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.m-monat-tag.we { background: color-mix(in srgb, var(--fl) 60%, var(--bg)); }
.m-monat-tag.fremd { opacity: .45; }
.m-monat-tag.heute .m-monat-nr { background: var(--akzent); color: var(--akzent-text); border-radius: 10px; padding: 0 6px; }
.m-monat-nr { font-size: 12px; color: var(--text2); align-self: flex-start; font-variant-numeric: tabular-nums; }
.m-chip { font-size: 11.5px; padding: 1px 6px; border-radius: 4px; background: var(--fl2); color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: default; }
.m-chip.warn { background: color-mix(in srgb, var(--orange) 18%, transparent); }
.m-chip.ok { background: color-mix(in srgb, var(--gruen) 16%, transparent); }
.m-chip.akzent { background: color-mix(in srgb, var(--akzent) 22%, transparent); cursor: pointer; }
.m-chip.fertig { opacity: .5; text-decoration: line-through; }
/* Assistenz: Chat */
.m-chat { max-width: 860px; margin: 0 auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.m-chat-verlauf { display: flex; flex-direction: column; gap: 10px; }
.m-blase { max-width: 85%; padding: 10px 14px; border-radius: 12px; line-height: 1.5; display: flex; flex-direction: column; gap: 6px; }
.m-blase.nutzer { align-self: flex-end; background: color-mix(in srgb, var(--akzent) 22%, transparent); }
.m-blase.assistent { align-self: flex-start; background: var(--fl); border: 1px solid var(--rand); }
.m-chat-tab { border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.m-chat-tab th, .m-chat-tab td { padding: 3px 10px 3px 0; text-align: left; border-bottom: 1px solid var(--rand); }
.m-chat-tab th { color: var(--text3); font-weight: 500; }
.m-chat-ein { display: flex; gap: 8px; align-items: center; position: sticky; bottom: 0; background: var(--bg); padding: 8px 0; }
"""

CSS += """
.m-kap { display: grid; grid-template-columns: minmax(110px, 1fr) 110px 110px; gap: 6px 10px; align-items: center; }
.hidden { display: none !important; }
"""

CSS += """
.m-block > .m-knopf, .m-plan-u > .m-knopf { align-self: flex-start; }
"""
