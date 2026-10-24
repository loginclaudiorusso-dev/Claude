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
.m-mono { font-variant-numeric: tabular-nums; color: var(--text2); white-space: nowrap; }
.m-ampel { width: 7px; height: 7px; border-radius: 50%; margin-left: 14px; }
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
