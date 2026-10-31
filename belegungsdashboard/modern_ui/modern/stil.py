"""Design-Tokens und Stil der neuen Oberfläche (dunkel, ruhig, wenige Akzente). Alle Farben nur hier."""

T = {
    "bg": "#0E0F12",          # Fenster
    "fl": "#15171C",          # Flächen (Seitenleiste, Center)
    "fl2": "#1B1E24",         # Hover, Eingabefelder
    "rand": "#262A32",
    "rand2": "#323743",
    "text": "#E6E8EC",
    "text2": "#A2A8B4",
    "text3": "#848B98",       # Kleinschrift: ≥ 4,5:1 auf allen Flächen (WCAG 1.4.3)
    "akzent": "#7C8CFF",      # einziger Akzent (Auswahl, Hauptknopf)
    "akzent_text": "#0E0F12",
    "rot": "#F2706B",
    "orange": "#E9A15A",
    "gruen": "#4CC38A",
    "blau": "#6E8BD8",
    # Zimmerzustände: frei und belegt klar unterscheidbar (ΔE ≈ 68, auch bei Rot-Grün-Schwäche ≥ 50), Text ≥ 4,5:1;
    # „geplant“ ist hohl mit gestricheltem Rand – unterscheidbar auch ohne Farbe
    "frei_fl": "#2E7556",
    "belegt_fl": "#4459A0",
    "belegt_text": "#F1F3FF",
    "knopf_oben": "#262A33",   # Knopf: leichter Verlauf von oben nach unten
    "knopf_unten": "#1C1F26",
    "akzent_oben": "#94A2FF",
    "akzent_unten": "#6B7BF2",
}

CSS = """
:root {
  --bg: %(bg)s; --fl: %(fl)s; --fl2: %(fl2)s; --rand: %(rand)s; --rand2: %(rand2)s;
  --text: %(text)s; --text2: %(text2)s; --text3: %(text3)s;
  --akzent: %(akzent)s; --akzent-text: %(akzent_text)s;
  --rot: %(rot)s; --orange: %(orange)s; --gruen: %(gruen)s; --blau: %(blau)s;
  --frei: %(frei_fl)s; --belegt: %(belegt_fl)s; --belegt-text: %(belegt_text)s;
  --k-oben: %(knopf_oben)s; --k-unten: %(knopf_unten)s; --a-oben: %(akzent_oben)s; --a-unten: %(akzent_unten)s;
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
.m-raster { display: grid; grid-template-columns: 28px minmax(140px, 1.3fr) 70px 132px minmax(150px, 210px) minmax(0, 1.7fr); }
.m-tkopf { position: sticky; top: 0; z-index: 1; background: var(--bg); border-bottom: 1px solid var(--rand); }
.m-tkopf > div { font-size: 11.5px; color: var(--text3); padding: 8px 8px; font-weight: 500; }
.m-zeile { border-bottom: 1px solid var(--rand); align-items: center; min-height: 46px; }
.m-tkopf.m-sortbar > div:not(:empty) { cursor: pointer; user-select: none; }
.m-tkopf.m-sortbar > div:not(:empty):hover { color: var(--text2); }
.m-tkopf > div.m-sort-auf, .m-tkopf > div.m-sort-ab { color: var(--text); }
.m-tkopf > div.m-sort-auf::after { content: " ▲"; font-size: 9px; } .m-tkopf > div.m-sort-ab::after { content: " ▼"; font-size: 9px; }
.m-sortiert { display: flex; flex-direction: column; }
.m-knopf[disabled] { opacity: .45; cursor: default; pointer-events: none; }
.m-karte .k2.m-klickbar { cursor: pointer; } .m-karte .k2.m-klickbar:hover { color: var(--text); text-decoration: underline dotted; }
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

/* Aufgaben-Center (Slide-over rechts; Lage und Glas siehe Block 0.6) */
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
.m-zs-b.belegt, .m-legende i.belegt { background: var(--belegt); color: var(--belegt-text); }
.m-zs-b.geplant, .m-legende i.geplant { background: color-mix(in srgb, var(--akzent) 8%, transparent); color: var(--text); border: 1.5px dashed var(--akzent); box-sizing: border-box; }
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
.m-zs-punkt { width: 10px; height: 10px; border-radius: 3px; background: var(--belegt); }
.m-zs-punkt.geplant { background: transparent; border: 1.5px dashed var(--akzent); box-sizing: border-box; }
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
.m-monat-tag { cursor: pointer; transition: background .12s; }
.m-monat-tag:hover { background: color-mix(in srgb, var(--akzent) 7%, var(--bg)); }
.m-monat-tag:focus-visible { outline: 2px solid var(--akzent); outline-offset: -2px; }
.m-monat-zk { display: flex; align-items: center; justify-content: space-between; }
.m-monat-plus { font-size: 15px; color: var(--akzent); opacity: 0; transition: opacity .12s; }
.m-monat-tag:hover .m-monat-plus, .m-monat-tag:focus-visible .m-monat-plus { opacity: 1; }
.m-monat-tag .m-chip { cursor: pointer; }
.m-monat-mehr { cursor: pointer; } .m-monat-mehr:hover { color: var(--akzent); text-decoration: underline; }
.m-monat-nav { display: flex; align-items: center; gap: 4px; flex: none; }
.m-monat-tipp { margin-left: auto; }
.m-zs-b.zieh { cursor: grab; } .m-zs-b.zieh:active { cursor: grabbing; }
body.m-zieht .m-zs-zeile.ziel { background: color-mix(in srgb, var(--akzent) 16%, transparent); outline: 1px dashed var(--akzent); outline-offset: -1px; }
.m-wechsel { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
.m-einfuegen { border: 1.5px dashed var(--rand2, var(--rand)); border-radius: 10px; min-height: 120px; padding: 14px; display: flex; align-items: center; justify-content: center; cursor: text; outline: none; overflow: hidden; margin: 10px 0; }
.m-einfuegen:focus { border-color: var(--akzent); background: color-mix(in srgb, var(--akzent) 6%, transparent); }
.m-einfuegen.liest { opacity: .6; }
.m-schalter { display: flex; align-items: center; gap: 10px; margin: 8px 0 4px; flex-wrap: wrap; }
.m-briefing { white-space: pre-wrap; font-family: inherit; font-size: 12.5px; line-height: 1.55; color: var(--text2); border: 1px solid var(--rand); border-radius: 10px; padding: 12px 14px; margin: 8px 0; max-height: 360px; overflow: auto; }
.m-glocke { position: relative; }
.m-glocke .m-zahl { position: absolute; top: -4px; right: -4px; min-width: 17px; height: 17px; padding: 0 4px; font-size: 10.5px; line-height: 17px; border-radius: 9px; background: var(--akzent); color: var(--akzent-text); }
.m-neu { display: flex; gap: 10px; align-items: flex-start; width: 100%; text-align: left; background: transparent; border: 0; border-bottom: 1px solid var(--rand); padding: 10px 4px; color: var(--text2); cursor: pointer; border-radius: 6px; }
.m-neu:hover { background: color-mix(in srgb, var(--akzent) 8%, transparent); }
.m-neu .m-neu-punkt { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex: none; background: transparent; }
.m-neu.ungelesen { color: var(--text); font-weight: 500; }
.m-neu.ungelesen .m-neu-punkt { background: var(--akzent); }
.m-neu.ungelesen.warnung .m-neu-punkt { background: var(--orange); } .m-neu.ungelesen.fehler .m-neu-punkt { background: var(--rot, #ef4444); }
.m-neu-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.m-merk { display: inline-flex; align-items: center; gap: 3px; height: 19px; padding: 0 7px 0 5px; border-radius: 10px; font-size: 11px; font-weight: 500; white-space: nowrap; cursor: help;
  background: color-mix(in srgb, var(--text3) 16%, transparent); color: var(--text2); border: 1px solid transparent; }
.m-merk .q-icon { font-size: 13px; }
.m-merk.allergie { background: color-mix(in srgb, var(--gruen) 16%, transparent); color: var(--gruen); border-color: color-mix(in srgb, var(--gruen) 40%, transparent); }
.m-merk.hilfsmittel { background: color-mix(in srgb, var(--blau) 16%, transparent); color: var(--blau); }
.m-merk.begleitung { background: color-mix(in srgb, var(--orange) 16%, transparent); color: var(--orange); }
.m-bereit-punkt { display: flex; gap: 10px; align-items: flex-start; padding: 8px 2px; border-bottom: 1px solid var(--rand); }
.m-bereit-punkt .q-icon { font-size: 18px; margin-top: 2px; color: var(--text3); }
.m-bereit-punkt.blocker .q-icon { color: var(--rot); }
.m-fl-wrap { overflow-x: auto; }
.m-fl { display: grid; grid-template-columns: 150px repeat(var(--wochen), minmax(58px, 1fr)); gap: 4px; margin: 12px 20px 20px; }
.m-fl-kopf { font-size: 11.5px; color: var(--text3); text-align: center; line-height: 1.25; }
.m-fl-kopf span { font-size: 10.5px; }
.m-fl-kopf.heute { color: var(--akzent); font-weight: 600; }
.m-fl-haus { grid-column: 1 / -1; font-size: 12px; font-weight: 600; color: var(--text2); margin-top: 8px; }
.m-fl-lab { display: flex; flex-direction: column; justify-content: center; font-size: 12.5px; color: var(--text); padding-right: 6px; }
.m-fl-lab span { font-size: 11px; color: var(--text3); }
.m-fl-z { font: inherit; position: relative; overflow: hidden; display: flex; flex-direction: column; align-items: flex-start; gap: 0;
  min-height: 48px; padding: 4px 7px; border-radius: 8px; border: 1px solid var(--rand); background: var(--bg); color: var(--text); cursor: pointer; text-align: left; }
.m-fl-z::before { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .22; }
.m-fl-z > * { position: relative; }
.m-fl-z b { font-size: 15px; font-variant-numeric: tabular-nums; }
.m-fl-z span { font-size: 10.5px; color: var(--text3); font-variant-numeric: tabular-nums; }
.m-fl-z i { font-style: normal; font-size: 10px; color: var(--text3); white-space: nowrap; }
.m-fl-z.ok::before { background: var(--gruen); } .m-fl-z.warn::before { background: var(--orange); } .m-fl-z.krit::before { background: var(--rot); opacity: .3; }
.m-fl-z.krit { border-color: color-mix(in srgb, var(--rot) 55%, transparent); }
.m-fl-z:hover { border-color: var(--akzent); }
.m-legende i.fl-ok { background: var(--gruen); } .m-legende i.fl-warn { background: var(--orange); } .m-legende i.fl-krit { background: var(--rot); }
.m-fl-p { display: grid; grid-template-columns: 64px 1fr auto; gap: 8px; align-items: baseline; padding: 4px 0; border-bottom: 1px solid var(--rand); }
.m-last { display: grid; grid-template-columns: 64px repeat(7, minmax(0, 1fr)); gap: 6px; margin: 14px 20px 20px; }
.m-last-kopf { font-size: 11.5px; color: var(--text3); padding: 0 4px; }
.m-last-kw { font-size: 12px; color: var(--text2); align-self: center; font-variant-numeric: tabular-nums; }
.m-last-tag { position: relative; overflow: hidden; text-align: left; min-height: 64px; padding: 6px 8px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--rand); color: var(--text); background: var(--bg); display: flex; flex-direction: column; gap: 1px; }
.m-last-tag::before { content: ""; position: absolute; inset: 0; background: var(--akzent); opacity: calc(var(--anteil) * .32); pointer-events: none; }
.m-last-tag > * { position: relative; }
.m-last-tag.we { background: color-mix(in srgb, var(--fl) 60%, var(--bg)); }
.m-last-tag.vorbei { opacity: .45; }
.m-last-tag.heute { outline: 2px solid var(--akzent); outline-offset: -2px; }
.m-last-tag.spitze { border-color: var(--orange); }
.m-last-tag.spitze::before { background: var(--orange); }
.m-last-datum { font-size: 11px; color: var(--text3); }
.m-last-zahl { font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.1; }
.m-last-haus { font-size: 10.5px; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-kachel-u { position: absolute; left: -5px; bottom: -5px; font-size: 13px; color: var(--orange); background: var(--bg); border-radius: 50%; padding: 1px; }
.m-aenderung { display: grid; grid-template-columns: minmax(140px, .8fr) 2fr; gap: 10px; padding: 6px 2px; border-bottom: 1px solid var(--rand); }
.m-aenderung.betroffen { border-left: 3px solid var(--orange); padding-left: 8px; }
.m-klassen { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 8px; margin: 6px 0 10px; }
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

CSS += """
/* Zimmer: Übersicht und defekte Zimmer */
.m-haeuser { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; padding: 18px 20px; align-items: start; }
.m-etage { display: grid; grid-template-columns: 56px 1fr; gap: 8px; align-items: start; padding: 4px 0; }
.m-etage-titel { padding-top: 6px; }
.m-kacheln { display: flex; flex-wrap: wrap; gap: 4px; }
.m-kachel { position: relative; width: 44px; height: 30px; border-radius: 6px; border: 1px solid transparent; font: inherit; font-size: 11.5px;
  font-variant-numeric: tabular-nums; cursor: pointer; display: grid; place-items: center; color: var(--text); padding: 0; }
.m-kachel:hover { filter: brightness(1.25); }
.m-kachel.frei, .m-legende i.frei { background: var(--frei); }
.m-kachel.teilweise, .m-legende i.teilweise { background: color-mix(in srgb, var(--gruen) 14%, var(--fl)); border: 1.5px solid var(--gruen); }
.m-kachel.belegt, .m-legende i.belegt { background: var(--belegt); color: var(--belegt-text); }
.m-kachel.geplant, .m-legende i.geplant { background: var(--fl); border: 1.5px dashed var(--akzent); color: #C7CEFF; }
.m-kachel.gesperrt, .m-legende i.gesperrt { background: repeating-linear-gradient(135deg, #2A2D34 0 5px, #22252B 5px 10px); color: var(--text3); }
.m-kachel.unbew { border: 2px solid var(--rot); }
.m-kachel.strittig { outline: 2px dashed var(--orange); outline-offset: 1px; }
.m-kachel-s { position: absolute; top: -6px; left: -4px; font-size: 10px; font-weight: 700; color: #16090A; background: var(--orange);
  border-radius: 6px; padding: 0 4px; line-height: 14px; }
.m-strittig { border: 1px solid var(--orange); border-radius: 10px; padding: 10px 12px; margin: 8px 0;
  background: color-mix(in srgb, var(--orange) 8%, transparent); }
.m-kachel-m { position: absolute; top: -6px; right: -4px; font-size: 10px; font-weight: 700; color: #16090A; background: var(--orange);
  border-radius: 7px; padding: 0 4px; line-height: 14px; }
.m-mliste { display: flex; flex-direction: column; gap: 2px; }
.m-mzeile { display: grid; grid-template-columns: minmax(0, 1fr) 70px 30px; align-items: center; gap: 6px; }
.m-mzeile .m-knopf { height: 22px; padding: 0 4px; }
"""

CSS += """
.m-np { display: grid; grid-template-columns: minmax(150px, 1.6fr) 44px 90px 60px 60px; gap: 6px 10px; align-items: center; }
.m-np .m-pille { justify-self: start; font-variant-numeric: tabular-nums; }
"""

CSS += """
.m-aw-tab.breit { grid-template-columns: minmax(170px, 1.2fr) 70px minmax(140px, 2fr) 70px 90px minmax(160px, 1.4fr); }
"""


CSS += """
/* ===== Knöpfe, Umschalter, Kennzahlen (0.5) – plastisch statt flach ===== */
.m-knopf { height: 32px; padding: 0 13px; border-radius: 8px; font-weight: 500; letter-spacing: .005em;
  border: 1px solid rgba(255,255,255,.08); background: linear-gradient(180deg, var(--k-oben), var(--k-unten));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 1px 2px rgba(0,0,0,.45);
  transition: background .15s, border-color .15s, box-shadow .15s, transform .08s; }
.m-knopf:hover { background: linear-gradient(180deg, #2E333E, #22262E); border-color: rgba(255,255,255,.15); }
.m-knopf:active { transform: translateY(1px); box-shadow: inset 0 1px 2px rgba(0,0,0,.4); }
.m-knopf .material-icons { font-size: 17px; opacity: .9; }
.m-knopf.primaer { color: #0B0D1A; font-weight: 600; border-color: rgba(148,162,255,.6);
  background: linear-gradient(180deg, var(--a-oben), var(--a-unten));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), 0 0 0 1px rgba(124,140,255,.15), 0 4px 14px rgba(124,140,255,.28); }
.m-knopf.primaer:hover { filter: brightness(1.07); box-shadow: inset 0 1px 0 rgba(255,255,255,.35), 0 0 0 1px rgba(124,140,255,.25), 0 6px 18px rgba(124,140,255,.38); }
.m-knopf.leise { background: transparent; border-color: transparent; box-shadow: none; color: var(--text2); }
.m-knopf.leise:hover { background: rgba(255,255,255,.06); color: var(--text); }
.m-knopf.gruen { height: 28px; color: #7FE0B0; border-color: rgba(76,195,138,.45);
  background: linear-gradient(180deg, rgba(76,195,138,.22), rgba(76,195,138,.10));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 2px 10px rgba(76,195,138,.15); }
.m-knopf.gruen:hover { background: linear-gradient(180deg, rgba(76,195,138,.32), rgba(76,195,138,.16)); }
.m-kopf .m-knopf { height: 32px; }

.m-segm { background: #0B0C10; border: 1px solid var(--rand); border-radius: 10px; padding: 3px; gap: 2px;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.55); }
.m-segm button { height: 28px; padding: 0 12px; border-radius: 7px; font-size: 13px; color: var(--text2); transition: background .15s, color .15s; }
.m-segm button:hover { color: var(--text); background: rgba(255,255,255,.04); }
.m-segm button.an { color: var(--text); font-weight: 600; background: linear-gradient(180deg, #2C303A, #23262E);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 1px 3px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.06); }
.m-segm button.an::after { content: ""; display: block; position: relative; }

/* Kennzahl-Kacheln (klickbar) */
.m-stats { display: flex; gap: 8px; flex-wrap: wrap; }
.m-stat { --c: var(--text2); font: inherit; color: var(--text); cursor: pointer; text-align: left; min-width: 104px;
  display: flex; flex-direction: column; gap: 2px; padding: 8px 14px 8px 12px; border-radius: 12px;
  border: 1px solid rgba(255,255,255,.07); background: linear-gradient(180deg, #1F222A, #17191F);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 1px 2px rgba(0,0,0,.4);
  transition: transform .12s, border-color .15s, box-shadow .15s, background .15s; }
.m-stat:hover { transform: translateY(-1px); border-color: color-mix(in srgb, var(--c) 45%, transparent);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 6px 16px rgba(0,0,0,.45); }
.m-stat:focus-visible { outline: 2px solid var(--akzent); outline-offset: 2px; }
.m-stat .z { font-size: 21px; font-weight: 650; line-height: 1.1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.m-stat .l { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text2); }
.m-stat .l i { width: 7px; height: 7px; border-radius: 50%; background: var(--c); box-shadow: 0 0 6px color-mix(in srgb, var(--c) 70%, transparent); }
.m-stat.an { border-color: color-mix(in srgb, var(--c) 70%, transparent);
  background: linear-gradient(180deg, color-mix(in srgb, var(--c) 20%, #1F222A), color-mix(in srgb, var(--c) 8%, #17191F));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--c) 35%, transparent), 0 6px 20px color-mix(in srgb, var(--c) 18%, transparent); }
.m-stat.ok { --c: var(--gruen); } .m-stat.warn { --c: var(--orange); } .m-stat.krit { --c: var(--rot); }
.m-stat.akzent { --c: var(--akzent); } .m-stat.blau { --c: var(--blau); } .m-stat.neutral { --c: var(--text3); }
.m-stat.ok .z { color: #8BE3B6; } .m-stat.warn .z { color: #F3BE85; } .m-stat.krit .z { color: #F7A19C; }

/* Kacheln ausblenden, die nicht zum Filter passen */
.m-kachel.aus { opacity: .14; filter: grayscale(.6); }

/* Navigation: aktiver Punkt mit Akzentleiste */
.m-navpunkt { position: relative; height: 34px; border-radius: 8px; }
.m-navpunkt.aktiv { background: linear-gradient(90deg, rgba(124,140,255,.16), rgba(124,140,255,.03)); color: var(--text); }
.m-navpunkt.aktiv::before { content: ""; position: absolute; left: -10px; top: 8px; bottom: 8px; width: 3px; border-radius: 0 3px 3px 0; background: var(--akzent); }
.m-navpunkt.aktiv .material-icons { color: var(--akzent); }
"""

CSS += """
.m-trennlinie { width: 1px; align-self: stretch; background: var(--rand); margin: 4px 4px; }
.m-leiste { padding: 12px 20px; gap: 12px; }
"""

CSS += """
/* ===== 0.6: Glas, Tiefe, Slide-over, lebendige Knöpfe, klare Zustände ===== */
:root { --glas: rgba(17,24,39,.80); --glas2: rgba(17,24,39,.62); --glasrand: rgba(255,255,255,.10);
  --r2: 16px; --mono: ui-monospace, "Cascadia Mono", "Cascadia Code", Consolas, "SF Mono", Menlo, monospace;
  --violett: #9333EA; --indigo: #4F46E5; }
html, body, .q-layout, .q-page-container { background:
  radial-gradient(900px 600px at 12% -10%, rgba(99,102,241,.16), transparent 60%),
  radial-gradient(800px 600px at 105% 110%, rgba(147,51,234,.13), transparent 60%),
  radial-gradient(600px 400px at 60% 40%, rgba(56,189,248,.04), transparent 70%), var(--bg) !important;
  background-attachment: fixed !important; }

/* Glasflächen: Navigation, Kopf, Leiste, Blöcke */
.m-nav { background: var(--glas2); backdrop-filter: blur(20px) saturate(1.3); -webkit-backdrop-filter: blur(20px) saturate(1.3);
  border-right: 1px solid var(--glasrand); }
.m-kopf, .m-leiste { background: rgba(17,24,39,.45); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--glasrand); }
.m-block { background: var(--glas2); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--glasrand); border-radius: var(--r2); box-shadow: 0 10px 30px rgba(0,0,0,.25); }
.m-logo { background: linear-gradient(135deg, var(--violett), var(--indigo)); color: #fff; border-radius: 8px;
  box-shadow: 0 4px 14px rgba(99,102,241,.4); }
.m-popup { background: rgba(17,24,39,.92) !important; backdrop-filter: blur(18px); border-color: var(--glasrand); border-radius: 12px !important; }

/* Slide-over: gleitet von rechts über den Inhalt, Hintergrund wird abgedunkelt und weichgezeichnet */
.m-schleier { position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,.40);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  opacity: 0; pointer-events: none; transition: opacity .3s ease-out; }
.m-schleier.offen { opacity: 1; pointer-events: auto; cursor: pointer; }
.m-center, .m-center.offen { position: fixed; top: 0; right: 0; bottom: 0; z-index: 45;
  width: min(420px, 100vw); overflow: hidden; background: var(--glas);
  backdrop-filter: blur(24px) saturate(1.4); -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border-left: 1px solid var(--glasrand); border-radius: var(--r2) 0 0 var(--r2);
  box-shadow: -24px 0 60px rgba(0,0,0,.5);
  transform: translateX(105%); transition: transform .3s cubic-bezier(.16,1,.3,1); }
.m-center.offen { transform: translateX(0); }
.m-center.offen.breit, .m-center.breit { width: min(520px, 100vw); }
.m-ckopf, .m-cinhalt, .m-center.breit .m-ckopf, .m-center.breit .m-cinhalt { min-width: 0; }
.m-ckopf { padding: 16px 18px; border-bottom: 1px solid var(--glasrand); }
.m-ckopf .m-titel { font-size: 16px; }
.m-cinhalt { padding: 16px; gap: 16px; flex: 1; }
.m-cgruppe { font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; padding: 6px 2px 0; }
@media (prefers-reduced-motion: reduce) { .m-center, .m-schleier { transition: none; } }

/* Aufgabenkarten: mehr Luft, Symbol je Aufgabentyp, Dringlichkeit am linken Rand */
.m-karte { padding: 16px; gap: 12px; border-radius: var(--r2); border: 1px solid var(--glasrand);
  border-left-width: 4px; background: rgba(255,255,255,.035); transition: transform .15s, box-shadow .2s, background .2s; }
.m-karte:hover { background: rgba(255,255,255,.055); transform: translateY(-1px); box-shadow: 0 10px 26px rgba(0,0,0,.35); }
.m-karte.dringend { border-left-color: #EF4444; background: linear-gradient(90deg, rgba(239,68,68,.10), rgba(255,255,255,.03) 45%);
  box-shadow: 0 0 0 1px rgba(239,68,68,.12), 0 0 22px rgba(239,68,68,.12); }
.m-karte.bald { border-left-color: #F59E0B; }
.m-karte.info { border-left-color: rgba(129,140,248,.55); }
.m-karte .k1 { gap: 12px; align-items: center; }
.m-karte .k1t { display: flex; flex-direction: column; gap: 3px; min-width: 0; font-size: 14px; }
.m-karte .k2, .m-karte .k3 { padding-left: 48px; }
.m-karte .k3 { gap: 8px; }
.m-ksymbol { --c: var(--akzent); width: 36px; height: 36px; flex: none; border-radius: 11px; display: grid; place-items: center;
  color: var(--c); background: color-mix(in srgb, var(--c) 15%, transparent); border: 1px solid color-mix(in srgb, var(--c) 30%, transparent); }
.m-ksymbol .material-icons, .m-ksymbol .q-icon { font-size: 19px; }
.m-ksymbol.krit { --c: #F87171; } .m-ksymbol.warn { --c: #FBBF24; } .m-ksymbol.ok { --c: #818CF8; }
.m-kstufe { font-size: 10.5px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--text3); }
.m-kstufe.krit { color: #F87171; } .m-kstufe.warn { color: #FBBF24; } .m-kstufe.ok { color: #A5B4FC; }
.m-karte.dringend .m-ksymbol { box-shadow: 0 0 14px rgba(239,68,68,.35); animation: m-puls 2.4s ease-in-out infinite; }
@keyframes m-puls { 50% { box-shadow: 0 0 22px rgba(239,68,68,.55); } }
@media (prefers-reduced-motion: reduce) { .m-karte.dringend .m-ksymbol { animation: none; } }

/* Knöpfe: sofort als klickbar erkennbar, mit Micro-Interactions */
.m-knopf { cursor: pointer; border-radius: 10px; border: 1px solid var(--glasrand); background: rgba(255,255,255,.06);
  box-shadow: 0 1px 2px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
  transition: transform .15s ease-out, filter .15s, background .15s, border-color .15s, box-shadow .2s; }
.m-knopf:hover { transform: scale(1.02); background: rgba(255,255,255,.11); border-color: rgba(255,255,255,.2);
  box-shadow: 0 6px 16px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.08); }
.m-knopf:active { transform: scale(.98); }
.m-knopf.primaer { color: #fff; border-color: rgba(255,255,255,.12);
  background: linear-gradient(90deg, var(--violett), var(--indigo));
  box-shadow: 0 10px 22px -6px rgba(88,28,135,.55), 0 4px 14px rgba(88,28,135,.20), inset 0 1px 0 rgba(255,255,255,.22); }
.m-knopf.primaer:hover { filter: brightness(1.12); background: linear-gradient(90deg, var(--violett), var(--indigo));
  box-shadow: 0 14px 28px -6px rgba(99,102,241,.6), inset 0 1px 0 rgba(255,255,255,.28); }
.m-knopf.leise { background: transparent; border-color: transparent; box-shadow: none; }
.m-knopf.leise:hover { background: rgba(255,255,255,.07); border-color: var(--glasrand); box-shadow: none; }
.m-knopf.gruen { color: #86EFAC; border-color: rgba(34,197,94,.4); background: rgba(34,197,94,.14); }
.m-knopf.gruen:hover { background: rgba(34,197,94,.24); border-color: rgba(34,197,94,.6); }
.m-toast .m-knopf { color: inherit; background: transparent; border-color: rgba(0,0,0,.25); box-shadow: none; }
.m-navpunkt { cursor: pointer; transition: background .15s, color .15s; }
.m-navpunkt:hover { background: rgba(255,255,255,.05); color: var(--text); }
.m-navpunkt.aktiv { background: linear-gradient(90deg, rgba(147,51,234,.22), rgba(79,70,229,.05)); }
.m-navpunkt.aktiv::before { background: linear-gradient(180deg, var(--violett), var(--indigo)); }
.m-navpunkt.aktiv .material-icons { color: #A5B4FC; }
.m-segm { background: rgba(0,0,0,.30); border-color: var(--glasrand); border-radius: 12px; }
.m-segm button { cursor: pointer; border-radius: 9px; }
.m-segm button.an { background: linear-gradient(90deg, rgba(147,51,234,.35), rgba(79,70,229,.35));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 2px 8px rgba(79,70,229,.25), 0 0 0 1px rgba(165,180,252,.25); }
.m-liste-zeile, .m-kachel, button.m-zeile { cursor: pointer; }
.m-kachel { border-radius: 8px; transition: transform .12s ease-out, box-shadow .15s; }
.m-kachel:hover { transform: scale(1.06); box-shadow: 0 4px 12px rgba(0,0,0,.4); z-index: 1; }

/* Kennzahlen: Monospace-Ziffern, Symbol, klare Hierarchie */
.m-mono, .m-kpi b, .m-pille { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.m-stat { border-radius: var(--r2); padding: 10px 16px 10px 12px; min-width: 120px; gap: 4px;
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)); border: 1px solid var(--glasrand);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
.m-stat:hover { transform: translateY(-2px) scale(1.02); }
.m-stat .k { display: inline-flex; align-items: center; gap: 8px; }
.m-stat .s { font-size: 18px; color: var(--c); width: 26px; height: 26px; border-radius: 8px; display: grid; place-items: center;
  background: color-mix(in srgb, var(--c) 16%, transparent); }
.m-stat .z { font-family: var(--mono); font-size: 24px; font-weight: 700; letter-spacing: -0.03em; }
.m-stat .l { padding-left: 0; }
.m-stat.blau .z { color: #A5B8F0; } .m-stat.akzent .z { color: #C4B5FD; } .m-stat.neutral .z { color: var(--text2); }

/* Zustands-Badges – überall gleich: frei grün ✓, belegt blau, geplant violett, gesperrt grau, Mängel orange ! */
.m-badge { --c: var(--text3); display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 8px 0 6px;
  border-radius: 999px; font-size: 11.5px; font-weight: 600; white-space: nowrap; color: color-mix(in srgb, var(--c) 80%, #fff);
  background: color-mix(in srgb, var(--c) 15%, transparent); border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }
.m-badge .q-icon, .m-badge .material-icons { font-size: 15px !important; }
.m-badge.ok { --c: var(--gruen); } .m-badge.blau { --c: var(--blau); } .m-badge.akzent { --c: #A78BFA; }
.m-badge.neutral { --c: #9CA3AF; } .m-badge.warn { --c: var(--orange); } .m-badge.krit { --c: var(--rot); }
.m-legende { gap: 6px; flex-wrap: wrap; }

/* Erste Schritte */
.m-willkommen { margin: 20px 24px 0; padding: 20px 22px; border-radius: var(--r2); border: 1px solid rgba(165,180,252,.25);
  background: linear-gradient(120deg, rgba(147,51,234,.16), rgba(79,70,229,.10) 50%, rgba(17,24,39,.6));
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); box-shadow: 0 16px 40px rgba(0,0,0,.3);
  display: flex; flex-direction: column; gap: 16px; animation: m-rein .4s ease-out; }
@keyframes m-rein { from { opacity: 0; transform: translateY(-6px); } }
.m-w-kopf { display: flex; align-items: center; gap: 14px; }
.m-w-gruss { font-size: 28px; color: #FBBF24; }
.m-w-schritte { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.m-w-schritt { display: flex; flex-direction: column; gap: 6px; padding: 14px; border-radius: 12px;
  background: rgba(255,255,255,.04); border: 1px solid var(--glasrand); }
.m-w-nr { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; color: #C4B5FD;
  background: rgba(147,51,234,.18); border: 1px solid rgba(167,139,250,.3); }
.m-w-nr .q-icon, .m-w-nr .material-icons { font-size: 18px; }
"""

CSS += """
/* ===== 0.7: Zimmer-Karten, Filter-Menü, Neu-Badge, Person ins Zimmer ===== */
.m-namezeile { display: flex; align-items: center; gap: 8px; min-width: 0; }
.m-neu-badge { flex: none; font-size: 10px; font-weight: 800; letter-spacing: .08em; padding: 2px 7px; border-radius: 999px;
  color: #DBEAFE; background: linear-gradient(90deg, rgba(59,130,246,.45), rgba(99,102,241,.45));
  border: 1px solid rgba(147,197,253,.45); box-shadow: 0 0 12px rgba(59,130,246,.35); cursor: help; }
.m-hinweisbox { margin: 16px 20px 0; padding: 10px 14px; border-radius: 12px; color: var(--text2);
  background: rgba(251,191,36,.08); border: 1px solid rgba(251,191,36,.25); }
.m-khaus { margin: 20px; padding: 18px; border-radius: var(--r2); background: var(--glas2); border: 1px solid var(--glasrand);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); }
.m-khaus-kopf { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.m-khaus-kopf .q-icon { color: #A5B4FC; font-size: 20px; }
.m-ketagen { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-start; }
.m-ketage { width: 280px; display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: 14px;
  background: rgba(0,0,0,.18); border: 1px solid var(--glasrand); }
.m-ketage-kopf { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 0 2px 2px; }
.m-zkarte { font: inherit; color: var(--text); text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px; border-radius: 12px; background: rgba(255,255,255,.04); border: 1px solid var(--glasrand);
  transition: transform .15s ease-out, border-color .15s, box-shadow .2s, background .15s; }
.m-zkarte:hover { transform: translateY(-1px) scale(1.01); border-color: rgba(165,180,252,.55); background: rgba(255,255,255,.07);
  box-shadow: 0 10px 22px rgba(0,0,0,.35); }
.m-zkarte.unbew { border-color: rgba(242,112,107,.6); box-shadow: 0 0 0 1px rgba(242,112,107,.25); }
.m-zk-kopf { display: flex; align-items: center; gap: 8px; }
.m-zk-nr { font-weight: 700; font-size: 14px; }
.m-zk-mangel { display: flex; gap: 6px; align-items: flex-start; font-size: 12px; color: var(--text2); }
.m-zk-mangel .q-icon { font-size: 15px; color: var(--orange); margin-top: 1px; }
.m-zk-mangel.warn { color: #F3BE85; } .m-zk-mangel.krit { color: #F7A19C; } .m-zk-mangel.krit .q-icon { color: var(--rot); }
.m-zk-bel { display: flex; gap: 8px; align-items: flex-start; padding-top: 4px; border-top: 1px dashed rgba(255,255,255,.07); }
.m-zk-bel .q-icon { font-size: 16px; margin-top: 2px; color: #93A8E8; }
.m-zk-bel.geplant .q-icon { color: #C4B5FD; } .m-zk-bel.gesperrt .q-icon { color: #9CA3AF; }
.m-zk-name { font-size: 12.5px; font-weight: 600; line-height: 1.3; }

.m-menue { padding: 6px 0; min-width: 260px; }
.m-mgruppe { font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--text3);
  padding: 10px 14px 4px; }
.m-mpunkt { min-height: 30px !important; padding: 2px 14px !important; display: flex; align-items: center; gap: 10px; font-size: 13px; }
.m-mhaken { font-size: 18px; color: var(--text3); } .m-mhaken.an { color: #A5B4FC; }
.m-knopf.akzent { border-color: rgba(165,180,252,.45); background: rgba(99,102,241,.18); color: #C7D2FE; }

.m-ktitelzeile { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.m-ktitelzeile .m-knopf { height: 30px; }
.m-kandidat { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 12px;
  border-radius: 12px; background: rgba(255,255,255,.04); border: 1px solid var(--glasrand); }
.m-zweispaltig { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; align-items: center; }
.m-raster .q-checkbox { margin-left: 4px; }
"""
CSS += """
.m-zwei > .m-breit { grid-column: 1 / -1; }
"""
CSS += """
.m-wo { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,.035);
  border: 1px solid var(--glasrand); }
"""
CSS += """
/* Einstellungen → Darstellung: Vorschau-Kärtchen je Design */
.m-designs { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
.m-design { font: inherit; color: var(--text); text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 4px;
  padding: 10px; border-radius: 10px; border: 1px solid var(--rand2); background: var(--fl); }
.m-design.an { border-color: var(--akzent); box-shadow: inset 0 0 0 1px var(--akzent); }
.m-design-muster { display: grid; grid-template-columns: 22% 1fr; grid-template-rows: 10px 1fr; gap: 3px; height: 54px; padding: 4px;
  border-radius: 6px; margin-bottom: 4px; }
.m-design-muster i:nth-child(1) { grid-row: 1 / span 2; border-radius: 3px; }
.m-design-muster i { border-radius: 3px; }
.d-original .m-design-muster { background: #0E0F12; } .d-original i { background: #262A33; } .d-original i:nth-child(3) { background: linear-gradient(90deg, #9333EA, #4F46E5); }
.d-inn .m-design-muster { background: #f3f5f9; } .d-inn i:nth-child(1) { background: #183861; } .d-inn i { background: #ffffff; border: 1px solid #dde3ec; }
.d-linear .m-design-muster { background: #0a0a0b; } .d-linear i { background: #18181b; border: 1px solid #2e2e33; border-radius: 1px; }
.d-obsidian .m-design-muster { background: #0c0b0a; } .d-obsidian i { background: #1d1b18; border: 1px solid #3a352f; } .d-obsidian i:nth-child(3) { background: linear-gradient(90deg, #e2c99a, #9c7a45); }
.d-nordic .m-design-muster { background: #f3efe7; } .d-nordic i:nth-child(1) { background: #e9e2d5; } .d-nordic i { background: #fbf9f5; border: 1px solid #ddd5c6; } .d-nordic i:nth-child(3) { background: #4a6878; }
"""
CSS += """
.m-badge .m-badge-n { margin-left: 3px; padding-left: 6px; border-left: 1px solid color-mix(in srgb, currentColor 35%, transparent); font-variant-numeric: tabular-nums;
  font-weight: 700; opacity: .95; }
.m-legende .m-badge { height: 24px; }
"""
CSS += """
.m-badge { gap: 5px; } .m-badge .nicegui-label, .m-badge > div { line-height: 1; }
"""
CSS += """
/* Prognose: Szenario-Regler */
.m-szenario { display: flex; flex-direction: column; gap: 6px; padding: 4px 0 10px; }
.m-sz-zeile { display: grid; grid-template-columns: 100px minmax(200px, 1fr) 96px minmax(140px, auto); gap: 14px; align-items: center; }
.m-sz-regler { min-width: 200px; }
"""
CSS += """
/* Prognose als Executive-Ansicht (seite_prognose) */
.m-ex { display: flex; flex-direction: column; gap: 16px; padding: 20px; max-width: 1480px; }
.m-xk { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.m-xk-karte { --c: var(--text3); border: 1px solid var(--rand); border-radius: 12px; background: var(--fl); padding: 14px 16px 12px;
  display: flex; flex-direction: column; gap: 4px; min-width: 0; position: relative; overflow: hidden; cursor: help; }
.m-xk-karte::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--c); opacity: .9; }
.m-xk-karte.ok { --c: var(--gruen); } .m-xk-karte.warn { --c: var(--orange); } .m-xk-karte.krit { --c: var(--rot); }
.m-xk-karte.neutral { --c: var(--text3); } .m-xk-karte.info { --c: var(--akzent); }
.m-xk-kopf { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text2); font-weight: 500; }
.m-xk-punkt { width: 8px; height: 8px; border-radius: 50%; background: var(--c); flex: none; }
.m-xk-wert { display: flex; align-items: baseline; gap: 6px; margin-top: 2px; }
.m-xk-wert .w { font-size: 30px; font-weight: 650; color: var(--text); letter-spacing: -.02em; font-variant-numeric: tabular-nums; line-height: 1.1; }
.m-xk-wert .e { font-size: 13px; color: var(--text3); }
.m-xk-bezug { font-size: 11.5px; color: var(--text3); white-space: normal; line-height: 1.35; }
.m-xk-vgl { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text2); margin-top: 2px; }
.m-xk-vgl .q-icon { font-size: 14px; color: var(--text3); }
.m-xe { border: 1px solid var(--rand); border-radius: 12px; background: var(--fl); overflow: hidden; }
.m-xe-kopf { font: inherit; color: var(--text); width: 100%; display: flex; align-items: baseline; gap: 10px; padding: 12px 16px;
  background: transparent; border: 0; cursor: pointer; text-align: left; }
.m-xe-kopf:hover { background: color-mix(in srgb, var(--text) 4%, transparent); }
.m-xe-liste { margin: 0; padding: 0 16px 14px; list-style: none; display: flex; flex-direction: column; gap: 7px; color: var(--text2); line-height: 1.5; }
.m-xe-liste li { display: grid; grid-template-columns: 118px 1fr; gap: 10px; align-items: baseline; }
.m-xe-tag { justify-self: start; font-size: 10.5px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; padding: 1px 7px;
  border-radius: 9px; border: 1px solid currentColor; color: var(--text3); }
.m-xe-tag.fakt { color: var(--text2); } .m-xe-tag.prognose { color: var(--akzent); } .m-xe-tag.einsch { color: var(--orange); }
.m-xe-tag.hinweis { color: var(--blau); }
.m-xg { gap: 6px; }
.m-xg-kopf { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.m-xg-schritte { display: flex; align-items: center; gap: 6px; }
.m-chart.m-xg-chart { height: 440px !important; }
.m-chart.m-xg-chart.gross { height: calc(100vh - 400px) !important; min-height: 360px; }
.m-xg-fuss { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 11.5px; color: var(--text3); padding: 2px 4px 0; }
.m-xg-fuss > div { display: contents; }
.m-xg-fuss span { display: inline-flex; align-items: center; gap: 6px; }
.m-xg-fuss i { display: inline-block; flex: none; }
.m-xg-fuss i.l { width: 16px; border-top: 2px dashed var(--text2); }
.m-xg-fuss i.l.ist { border-top: 2.5px solid var(--text); } .m-xg-fuss i.l.prog { border-top: 2.5px dashed var(--akzent); }
.m-xg-fuss i.l.kap { border-top: 1.5px dashed var(--rot); } .m-xg-fuss i.l.vj { border-top: 2px solid var(--blau); }
.m-xg-fuss i.l.vvj { border-top: 1.5px dotted var(--text3); }
.m-xg-fuss i.p { width: 9px; height: 9px; border-radius: 50%; border: 2px solid var(--text); }
.m-xg-fuss i.f { width: 14px; height: 9px; border-radius: 2px; background: color-mix(in srgb, var(--akzent) 30%, transparent); }
.m-xg-fuss i.f.ok { background: var(--gruen); } .m-xg-fuss i.f.warn { background: var(--orange); } .m-xg-fuss i.f.krit { background: var(--rot); }
.m-xs.aktiv { border-color: var(--orange); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--orange) 55%, transparent);
  background: repeating-linear-gradient(135deg, transparent 0 14px, color-mix(in srgb, var(--orange) 4%, transparent) 14px 28px), var(--fl); }
.m-xs-icon { color: var(--orange); font-size: 20px; }
.m-xs-banner { font-size: 11px; font-weight: 700; letter-spacing: .05em; color: var(--orange); border: 1px solid var(--orange);
  border-radius: 9px; padding: 1px 8px; }
.m-xs-tab { display: grid; grid-template-columns: minmax(160px, auto) minmax(160px, 1fr) minmax(160px, 1fr); gap: 4px 18px; max-width: 760px;
  padding: 6px 0; border-top: 1px solid var(--rand); }
.m-xv-raster { display: grid; grid-template-columns: minmax(300px, 1fr) minmax(0, 1.45fr); gap: 18px; align-items: start; }
.m-xv-raster.kompakt { grid-template-columns: 1fr; }
.m-xv-chart { height: 210px !important; width: 100%; }
.m-xv-tab { display: grid; grid-template-columns: minmax(120px, 1fr) repeat(4, minmax(64px, auto)) minmax(130px, auto) minmax(52px, auto);
  gap: 6px 10px; align-items: center; font-size: 13px; min-width: 0; }
.m-xv-name { font: inherit; color: var(--text); display: inline-flex; align-items: center; gap: 8px; background: transparent; border: 0;
  padding: 3px 6px; margin-left: -6px; border-radius: 6px; cursor: pointer; text-align: left; }
.m-xv-name:hover { background: color-mix(in srgb, var(--text) 6%, transparent); } .m-xv-name.an { font-weight: 650; }
.m-xv-farbe { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.m-xm { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; }
@media (max-width: 1100px) { .m-xv-raster { grid-template-columns: 1fr; } }
/* Präsentationsmodus: nur Inhalt – Navigation, Kopf, Leisten und Werkzeugleiste ausgeblendet */
body.praesentation .m-nav, body.praesentation .m-topnav, body.praesentation .m-prompt-zeile, body.praesentation .m-tb,
body.praesentation .m-kopf, body.praesentation .m-leiste { display: none !important; }
.m-ex.praes { max-width: none; padding: 24px 32px; gap: 18px; }
.m-ex.praes .m-xk { grid-template-columns: repeat(4, 1fr); }
.m-ex.praes .m-xk-wert .w { font-size: 40px; }
.m-ex.praes .m-xk-karte { cursor: default; }
.m-xp-kopf { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.m-xp-titel { font-size: 22px; font-weight: 650; color: var(--text); letter-spacing: -.01em; }
.m-xp-aktionen { margin-left: auto; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
"""
CSS += """
/* 0.12 – Prognose: Backtest-/Status-Schalter, Management-Szenario, Goslar-Aufteilung */
.m-xg-status { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text3); }
.m-xg-status.aus .m-segm { pointer-events: none; }
.m-xg-fuss i.l.sz { border-top: 3px dotted var(--orange); opacity: .8; } .m-xg-fuss i.l.kont { border-top: 1.5px dashed var(--text2); }
.m-xg-fuss i.f.uwt { background: #3B5BDB; } .m-xg-fuss i.f.mieter { background: #64748B; } .m-xg-fuss i.f.rest { background: #94A3B8; opacity: .55; }
.m-xs-pills { display: flex; flex-wrap: wrap; gap: 8px; padding: 2px 0 4px; }
.m-xs-pill { font: inherit; font-size: 13px; color: var(--text); display: inline-flex; align-items: center; gap: 7px; height: 34px;
  padding: 0 14px 0 11px; border-radius: 17px; border: 1px solid var(--rand2); background: var(--fl); cursor: pointer;
  transition: background .15s, border-color .15s; }
.m-xs-pill .q-icon { font-size: 17px; color: var(--text3); }
.m-xs-pill:hover:not(.aus) { border-color: var(--orange); }
.m-xs-pill.an { background: color-mix(in srgb, var(--orange) 16%, var(--fl)); border-color: var(--orange); font-weight: 600; }
.m-xs-pill.an .q-icon { color: var(--orange); }
.m-xs-pill.aus { opacity: .45; cursor: not-allowed; }
.m-xs-stepper { display: flex; flex-direction: column; gap: 8px; padding: 6px 0 4px; }
.m-xs-step { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.m-xs-step > .m-name { width: 100px; }
.m-xs-step .m-feld.klein { width: 96px; }
.m-knopf.klein { height: 30px; min-width: 40px; padding: 0 8px; justify-content: center; font-variant-numeric: tabular-nums; }
.m-xgs { gap: 10px; }
.m-xgs-balken { display: flex; height: 16px; border-radius: 6px; overflow: hidden; border: 1px solid var(--rand2); background: var(--fl2); }
.m-xgs-teil { min-width: 3px; } .m-xgs-teil.frei { background: transparent !important; }
.m-xgs-zahlen { display: flex; flex-wrap: wrap; gap: 6px 26px; }
.m-xgs-zahl { display: inline-flex; align-items: baseline; gap: 7px; font-size: 13px; color: var(--text2); }
.m-xgs-zahl .w { font-size: 18px; font-weight: 650; color: var(--text); }
.m-xgs-punkt { width: 10px; height: 10px; border-radius: 3px; flex: none; align-self: center; }
.m-xgs-punkt.frei { border: 1px dashed var(--text3); }
.m-xgs-kont { border-top: 1px solid var(--rand); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.m-xgs-herkunft { font-size: 11px; padding: 1px 8px; border-radius: 9px; border: 1px solid var(--rand2); color: var(--text3); }
.m-xgs-stepper { display: flex; flex-wrap: wrap; gap: 8px 28px; }
.m-xgs-step { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.m-xgs-step .w { min-width: 46px; text-align: center; font-weight: 650; color: var(--text); }
.m-xgs-tab { display: grid; grid-template-columns: minmax(130px, auto) repeat(4, minmax(150px, auto)); gap: 4px 22px; max-width: 980px;
  font-size: 13px; }
.m-xgs-tab .warn { color: var(--orange) !important; } .m-xgs-tab .krit { color: var(--rot) !important; font-weight: 650; }
.m-xgs.kompakt .m-xgs-zahl .w { font-size: 22px; }
"""
CSS += """
body .m-xs-step .m-knopf.klein, body .m-xgs-step .m-knopf.klein { border: 1px solid var(--rand2) !important;
  background: var(--fl) !important; color: var(--text) !important; box-shadow: none !important; }
body .m-xs-step .m-knopf.klein:hover, body .m-xgs-step .m-knopf.klein:hover { border-color: var(--akzent) !important; }
"""
CSS += """
/* 0.13 – Gruppen-Schalter über dem Graph */
.m-xg-gruppen { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; padding: 2px 0 2px; }
.m-xg-check { font: inherit; font-size: 13px; color: var(--text2); display: inline-flex; align-items: center; gap: 6px; height: 30px;
  padding: 0 12px 0 8px; border-radius: 8px; border: 1px solid var(--rand2); background: var(--fl); cursor: pointer; }
.m-xg-check .q-icon { font-size: 19px; color: var(--text3); }
.m-xg-check.an { color: var(--text); border-color: color-mix(in srgb, var(--akzent) 55%, transparent); }
.m-xg-check.an .q-icon { color: var(--akzent); }
.m-xg-check.aus { opacity: .45; cursor: not-allowed; }
.m-xg-gruppen-hinweis { font-size: 11px; font-weight: 700; letter-spacing: .04em; color: var(--blau); border: 1px solid var(--blau);
  border-radius: 9px; padding: 1px 8px; text-transform: uppercase; }
"""
CSS += """
/* 0.14 – Ansicht-Badge, weicher Diagrammwechsel */
.m-xg-gruppen-hinweis { text-transform: none; letter-spacing: .01em; font-size: 12px; font-weight: 600; padding: 3px 10px;
  border-radius: 11px; color: var(--akzent); border-color: color-mix(in srgb, var(--akzent) 55%, transparent);
  background: color-mix(in srgb, var(--akzent) 10%, transparent); transition: color .2s, background .2s, border-color .2s; }
.m-xg-gruppen-hinweis.rein { color: var(--blau); border-color: var(--blau); background: color-mix(in srgb, var(--blau) 10%, transparent); }
.m-xg-chart { animation: m-xg-ein .35s cubic-bezier(.22, .61, .36, 1) both; }
@keyframes m-xg-ein { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .m-xg-chart { animation: none; } .m-xg-gruppen-hinweis { transition: none; } }
.m-xg-kopf { row-gap: 8px; }
"""
CSS += """
/* 0.15 – Optionen-Menü mit Gruppen, Backtest-Status */
.m-menue-kopf { font-size: 10.5px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--text3);
  padding: 8px 14px 2px; }
.m-xg-status.aus { opacity: .45; cursor: not-allowed; }
.m-xg-gruppen-hinweis.bt { color: var(--orange); border-color: var(--orange); background: color-mix(in srgb, var(--orange) 10%, transparent); }
"""
CSS += """
/* 0.15 – Standortwechsel: Inhalt blendet weich aus und wieder ein */
.m-ex { animation: m-xg-ein .22s cubic-bezier(.22, .61, .36, 1) both; }
.m-ex.m-wechselt { opacity: .45; transition: opacity .12s ease-out; pointer-events: none; }
@media (prefers-reduced-motion: reduce) { .m-ex { animation: none; } .m-ex.m-wechselt { transition: none; } }
"""
CSS += """
/* 0.16 – eine Filterleiste über dem Prognosegraph, leuchtendes Ansicht-Badge */
.m-xg-filter { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding-bottom: 10px; margin-bottom: 4px;
  border-bottom: 1px solid var(--rand); }
.m-xg-filter-rechts { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.m-xg-filter-rechts .m-segm button { padding-left: 11px; padding-right: 11px; }
.m-xg-ansicht { transition: color .25s, background .25s, border-color .25s, box-shadow .25s; }
.m-xg-ansicht.leuchtet { color: var(--text); font-weight: 700; border-color: var(--akzent);
  background: color-mix(in srgb, var(--akzent) 22%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--akzent) 45%, transparent), 0 0 14px color-mix(in srgb, var(--akzent) 45%, transparent); }
.m-xg-ansicht.rein { color: var(--text3); font-weight: 600; border-color: var(--rand2); background: transparent; box-shadow: none; }
.m-ex.still, .m-ex.still .m-xg-chart { animation: none; }
@media (prefers-reduced-motion: reduce) { .m-xg-ansicht { transition: none; } }
"""
CSS += """
.m-xg-filter .m-segm, .m-xg-kopf .m-segm { margin-left: 0; }    /* Standorte und Reiter bündig links */
"""
CSS += """
/* 0.17 – Prognose in drei Bereichen: Dashboard ohne Scrollen, Szenarien, Details & Protokoll */
.m-ex.b-dashboard { gap: 12px; padding-top: 14px; padding-bottom: 12px; }
.m-ex.b-dashboard .m-xg { padding-top: 12px; padding-bottom: 10px; gap: 4px; }
.m-ex.b-dashboard .m-chart.m-xg-chart { height: max(250px, calc(100vh - 470px)) !important; }
.m-ex.b-dashboard .m-xg-filter { padding-bottom: 8px; }
.m-ex.b-dashboard .m-xk { gap: 10px; }
.m-ex.b-dashboard .m-xk-karte { padding: 9px 14px 8px; gap: 1px; }
.m-ex.b-dashboard .m-xk-wert .w { font-size: 24px; }
.m-ex.b-dashboard .m-xk-bezug, .m-ex.b-dashboard .m-xk-vgl { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-ex.b-dashboard .m-xk-vgl .q-icon { font-size: 12px; }
.m-xi { display: flex; gap: 8px; align-items: stretch; min-width: 0; border: 0; background: transparent; }
.m-xi-badge { flex: 1 1 0; min-width: 0; display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 10px;
  border: 1px solid var(--rand); background: var(--fl); font-size: 12.5px; color: var(--text2); cursor: help; }
.m-xi-badge .m-xe-tag { flex: none; font-size: 9.5px; }
.m-xi-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.m-xi-szenario { color: var(--orange) !important; border-color: var(--orange) !important; flex: none; }
.m-xi-mehr { flex: none; }
.m-xg-symbol { width: 32px; padding: 0 !important; justify-content: center; }
.m-xsz { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(430px, 1fr); gap: 16px; align-items: start; }
.m-xsz .m-xg .m-chart.m-xg-chart { height: max(320px, calc(100vh - 380px)) !important; }
.m-xsz .m-xs { position: sticky; top: 0; }
.m-xsz .m-xs-tab { grid-template-columns: minmax(130px, auto) 1fr 1fr; gap: 3px 12px; }
.m-xsz .m-xs-step > .m-name { width: 84px; }
@media (max-width: 1250px) { .m-xsz { grid-template-columns: 1fr; } }
.m-xd { display: flex; flex-direction: column; gap: 10px; }
.m-xd-teil { border: 1px solid var(--rand); border-radius: 12px; background: var(--fl); overflow: hidden; }
.m-xd-teil .q-expansion-item__container > .q-item { min-height: 48px; font-weight: 600; color: var(--text); }
.m-xd-teil .q-expansion-item__content { padding: 4px 16px 14px; }
.m-xd-teil .q-item__section--avatar .q-icon { color: var(--text3); }
.m-xd-teil .m-xt, .m-xd-teil .m-xe, .m-xd-teil .m-block { border: 0; background: transparent; padding-left: 0; padding-right: 0; }
"""
CSS += """
.m-xbereich { display: flex; } .m-xbereich .m-segm { margin-left: 0; }
.m-xsz .m-xg-kopf { gap: 6px 8px; }
.m-xsz .m-xg-ansicht { display: none; }               /* im schmalen Graph: Badge entfällt, die Ansicht steht im Titel */
.m-xsz .m-xs-tab { font-size: 12.5px; }
"""
CSS += """
.m-ex.b-dashboard .m-xi { padding-right: 56px; }       /* Platz für den Griff der Werkzeugleiste unten rechts */
"""
CSS += """
/* Dashboard füllt genau den sichtbaren Bereich – der Graph nimmt, was übrig bleibt (alle Layouts) */
.m-ex.b-dashboard { height: 100%; min-height: 0; box-sizing: border-box; display: flex; flex-direction: column; max-width: none; }
.m-ex.b-dashboard > .m-xg { flex: 1 1 auto; min-height: 330px; display: flex; flex-direction: column; }
.m-ex.b-dashboard .m-chart.m-xg-chart { flex: 1 1 auto; height: auto !important; min-height: 210px; }
.m-ex.b-dashboard > .m-xk, .m-ex.b-dashboard > .m-xi { flex: none; }
"""
CSS += """
.m-xd .m-xt .m-zeile { min-height: 36px; }
"""
CSS += """
/* 0.34: Datenstand, Rückfrage beim Schließen, sortieren per Tastatur, weitere Darstellungen */
.m-datenstand { font-size: 11.5px; color: var(--text3); white-space: nowrap; padding: 2px 8px; border-radius: 999px;
  font-variant-numeric: tabular-nums; }
.m-datenstand.neu { animation: m-stand-neu 2.4s ease-out 1; }
.m-datenstand.warten { color: var(--orange); background: color-mix(in srgb, var(--orange) 14%, transparent); }
@keyframes m-stand-neu { 0%, 40% { color: var(--text); background: color-mix(in srgb, var(--akzent) 28%, transparent); }
  100% { color: var(--text3); background: transparent; } }
@media (prefers-reduced-motion: reduce) { .m-datenstand.neu { animation: none; color: var(--text2); } }
.m-frage { width: min(420px, 92vw); background: var(--fl); color: var(--text); border: 1px solid var(--rand2);
  border-radius: 12px; box-shadow: 0 20px 50px rgba(0,0,0,.55); padding: 18px 20px 14px; display: flex; flex-direction: column; gap: 8px; }
.m-tkopf.m-sortbar > div[tabindex]:focus-visible { outline: 2px solid var(--akzent); outline-offset: -2px; border-radius: 4px; color: var(--text); }
.m-mehr { margin-top: 10px; }
.m-mehr > summary { cursor: pointer; color: var(--text2); font-size: 12.5px; list-style: none; display: inline-flex;
  align-items: center; gap: 6px; padding: 5px 12px 5px 8px; border: 1px solid var(--rand2); border-radius: var(--r); }
.m-mehr > summary::-webkit-details-marker { display: none; }
.m-mehr > summary:hover { color: var(--text); background: var(--fl2); }
.m-mehr-pfeil { font-size: 18px; transition: transform .15s; }
.m-mehr[open] .m-mehr-pfeil { transform: rotate(90deg); }
.m-mehr[open] > summary { margin-bottom: 4px; }
"""
CSS += """
/* 0.35: Standorte – Wechsel über das Logo, Auswahl beim Start */
.m-marke.m-standort { font: inherit; font-weight: 600; color: inherit; background: transparent; border: 0; width: 100%;
  text-align: left; cursor: pointer; border-radius: var(--r); margin-bottom: 8px; padding: 4px 8px 8px; }
.m-marke.m-standort:hover { background: var(--fl2); }
.m-marke-t { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; flex: 1; }
.m-standort-name { font-size: 11.5px; font-weight: 500; color: var(--akzent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-standort-pfeil { font-size: 16px; color: var(--text3); }
.m-standortwahl { width: min(560px, 94vw); }
.m-standorte { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 6px; }
.m-standort-k { font: inherit; color: var(--text); text-align: left; cursor: pointer; background: var(--fl2);
  border: 1px solid var(--rand2); border-radius: 10px; padding: 14px 14px 12px; display: grid; gap: 4px; }
.m-standort-k:hover { border-color: var(--akzent); }
.m-standort-k.an { border-color: var(--akzent); box-shadow: 0 0 0 1px var(--akzent) inset; }
.m-standort-k:focus-visible { outline: 2px solid var(--akzent); outline-offset: 2px; }
@media (max-width: 520px) { .m-standorte { grid-template-columns: 1fr; } }
"""
