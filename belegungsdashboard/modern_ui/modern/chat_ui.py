"""1.43: Chat-Fenster unten rechts – bleibt offen, während man weiterarbeitet (wie ein Chatfenster in Teams).

* Öffnen: Titelleiste (Sprechblase mit Zahl ungelesener Beiträge) oder Übersicht → Kommunikation → Chat.
* Oben die Kanäle „Alle Standorte“ und der eigene Standort, darunter der Verlauf (eigene Beiträge rechts), unten
  Eingabe – Enter sendet, Umschalt+Enter macht eine neue Zeile.
* Offen: alle ``OFFEN_S`` Sekunden nachsehen (nur wenn sich die Datei geändert hat). Zu: alle ``ZU_S`` Sekunden die
  Zahl der ungelesenen Beiträge prüfen, bei Neuem ein Hinweis im Programm und als Windows-Meldung.
"""

from __future__ import annotations

from datetime import date

from nicegui import run, ui

from . import chat_kern as ck
from .ui_bausteine import attr

OFFEN_S = 3.0
ZU_S = 20.0


def einrichten(a) -> None:
    """Einmal je Seite (nach dem Rahmen): Fenster anlegen (zu) und die beiden Zeitgeber starten."""
    a.chat = {"offen": False, "kanal": ck.ALLE, "stempel": -1.0, "gemeldet": set(), "ungelesen": 0}
    with ui.element("section").classes("m-chat") as fenster:
        attr(fenster, aria_label="Chat")
        with ui.element("div").classes("m-chat-kopf"):
            ui.icon("forum").classes("m-chat-sym")
            ui.label("Chat").classes("m-chat-titel")
            a._chat_kanaele = ui.element("div").classes("m-chat-kanaele")
            zu = ui.element("button").classes("m-chat-zu")
            attr(zu, title="Chat schließen (Esc)", aria_label="Chat schließen")
            with zu:
                ui.icon("close")
            zu.on("click", lambda: umschalten(a, False))
        a._chat_verlauf = ui.element("div").classes("m-chat-verlauf")
        with ui.element("div").classes("m-chat-eingabe"):
            feld = ui.textarea(placeholder="Nachricht … (Enter sendet)").props("autogrow outlined dense").classes(
                "m-chat-feld")
            senden = ui.element("button").classes("m-chat-senden")
            attr(senden, title="Senden (Enter)", aria_label="Senden")
            with senden:
                ui.icon("send")

            async def abschicken():
                text = (feld.value or "").strip()
                if not text:
                    return
                feld.value = ""
                try:
                    await run.io_bound(ck.senden, a.chat["kanal"], text)
                except Exception as exc:                # noqa: BLE001 – Netz weg o. Ä.: Text zurückgeben, Grund zeigen
                    feld.value = text
                    a.toast(f"Nicht gesendet: {exc}", fehler=True)
                    return
                await auffrischen(a, erzwingen=True)
            senden.on("click", abschicken)
            feld.on("keydown.enter", abschicken, js_handler="(e) => { if (!e.shiftKey) { e.preventDefault(); emit(); } }")
    fenster.set_visibility(False)
    a._chat_fenster = fenster
    async def offen_takt():
        if a.chat["offen"]:
            await auffrischen(a)

    async def zu_takt():
        await zaehlen(a)

    async def start_takt():                         # Stand beim Start: alte Beiträge nicht melden
        await zaehlen(a, melden=False)
    ui.timer(OFFEN_S, offen_takt)
    ui.timer(ZU_S, zu_takt)
    ui.timer(2.0, start_takt, once=True)


async def umschalten(a, an: bool | None = None) -> None:
    a.chat["offen"] = (not a.chat["offen"]) if an is None else an
    a._chat_fenster.set_visibility(a.chat["offen"])
    if a.chat["offen"]:
        await auffrischen(a, erzwingen=True)
        ui.run_javascript("setTimeout(() => document.querySelector('.m-chat-feld textarea')?.focus(), 80)")


async def kanal_waehlen(a, kanal: str) -> None:
    a.chat["kanal"] = kanal
    await auffrischen(a, erzwingen=True)


def _kanaele_zeichnen(a, ungelesen: dict) -> None:
    a._chat_kanaele.clear()
    with a._chat_kanaele:
        for k, name in ck.kanaele().items():
            b = ui.element("button").classes("m-chat-kanal" + (" an" if k == a.chat["kanal"] else ""))
            with b:
                ui.label(name)
                if ungelesen.get(k) and k != a.chat["kanal"]:
                    ui.label(str(len(ungelesen[k]))).classes("m-chat-zahl")
            b.on("click", lambda k=k: kanal_waehlen(a, k))


async def auffrischen(a, erzwingen: bool = False) -> None:
    """Verlauf neu zeichnen – nur, wenn sich die Datei geändert hat (oder ``erzwingen``)."""
    st = await run.io_bound(ck.stempel)
    if st == a.chat["stempel"] and not erzwingen:
        return
    a.chat["stempel"] = st
    kanal = a.chat["kanal"]
    bs = await run.io_bound(ck.beitraege, kanal)
    ich = await run.io_bound(ck.ich)
    if bs:
        await run.io_bound(ck.gelesen, kanal, bs[-1].zeit)
    ungelesen = await run.io_bound(ck.ungelesen, ich)
    _kanaele_zeichnen(a, ungelesen)
    a._chat_verlauf.clear()
    with a._chat_verlauf:
        if not bs:
            ui.label("Noch nichts geschrieben. Fragen an alle hier hinein – wer gerade im Programm ist, sieht sie sofort.").classes(
                "m-chat-leer")
        for trenner, b in ck.tagestrenner(bs, date.today().isoformat()):
            if b is None:
                ui.label(trenner).classes("m-chat-tag")
                continue
            eigen = b.von == ich
            with ui.element("div").classes("m-chat-b" + (" eigen" if eigen else "")):
                if not eigen:
                    ui.label(b.von).classes("m-chat-von")
                ui.label(b.text).classes("m-chat-text")
                ui.label(b.uhr).classes("m-chat-uhr")
    ui.run_javascript("(() => { const v = document.querySelector('.m-chat-verlauf'); if (v) v.scrollTop = v.scrollHeight; })()")
    _zahl_setzen(a, sum(len(x) for x in ungelesen.values()))


def _zahl_setzen(a, n: int) -> None:
    if n != a.chat.get("ungelesen"):
        a.chat["ungelesen"] = n
        from . import menueband_ui

        menueband_ui.fuellen(a, erzwingen=True)


async def zaehlen(a, melden: bool = True) -> None:
    """Fenster zu: neue Beiträge anderer zählen; Neues einmal melden (im Programm und als Windows-Meldung)."""
    if a.chat["offen"]:
        return
    try:
        ungelesen = await run.io_bound(ck.ungelesen)
    except Exception:                                  # noqa: BLE001 – Netz kurz weg: beim nächsten Mal
        return
    neu = [b for bs in ungelesen.values() for b in bs if b.id not in a.chat["gemeldet"]]
    a.chat["gemeldet"] |= {b.id for b in neu}
    _zahl_setzen(a, sum(len(x) for x in ungelesen.values()))
    if not neu or not melden:
        return
    b = neu[-1]
    text = f"{b.von}: {b.text[:80]}" + (f" (+{len(neu) - 1} weitere)" if len(neu) > 1 else "")
    a.toast(f"Chat – {text}", rueck=False, extra=("Chat öffnen", lambda: umschalten(a, True)))
    try:
        from . import melder

        if await run.io_bound(melder.an):
            melder.windows_zeigen("INNternat – Chat", text)
    except Exception:                                  # noqa: BLE001 – Meldung ist Komfort
        pass


CSS = r"""
.m-chat { position: fixed; right: 16px; bottom: 34px; width: 380px; max-width: calc(100vw - 32px); height: 520px;
  max-height: calc(100vh - 120px); z-index: 60; display: flex; flex-direction: column; background: var(--fls, var(--fl));
  border: 1px solid var(--rand); border-radius: 10px; box-shadow: 0 12px 32px rgba(0,0,0,.22); overflow: hidden; }
.m-chat-kopf { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 1px solid var(--rand);
  background: var(--ob-band, var(--fl2)); flex-wrap: wrap; }
.m-chat-sym { color: var(--akzent); font-size: 20px; }
.m-chat-titel { font-weight: 600; }
.m-chat-kanaele { display: flex; gap: 4px; flex: 1; justify-content: flex-end; flex-wrap: wrap; }
.m-chat-kanal { font: inherit; font-size: 12px; padding: 3px 8px; border-radius: 12px; border: 1px solid var(--rand);
  background: transparent; color: var(--text2); cursor: pointer; display: inline-flex; gap: 4px; align-items: center; }
.m-chat-kanal.an { background: var(--akzent); border-color: var(--akzent); color: var(--fls, #fff); font-weight: 600; }
.m-chat-zahl { background: var(--rot, #B42318); color: #fff; border-radius: 9px; padding: 0 6px; font-size: 11px; }
.m-chat-zu { border: 0; background: transparent; color: var(--text2); cursor: pointer; border-radius: 4px; }
.m-chat-zu:hover { background: var(--fl2); }
.m-chat-verlauf { flex: 1; overflow-y: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; }
.m-chat-leer { color: var(--text3); font-size: 13px; margin: auto 0; text-align: center; }
.m-chat-tag { align-self: center; font-size: 11px; color: var(--text3); padding: 2px 8px; border-radius: 10px;
  background: var(--fl2); margin: 4px 0; }
.m-chat-b { align-self: flex-start; max-width: 82%; padding: 6px 10px 4px; border-radius: 10px 10px 10px 2px;
  background: var(--fl2); display: flex; flex-direction: column; gap: 1px; }
.m-chat-b.eigen { align-self: flex-end; border-radius: 10px 10px 2px 10px;
  background: color-mix(in srgb, var(--akzent) 18%, var(--fls, #fff)); }
.m-chat-von { font-size: 11.5px; font-weight: 600; color: var(--akzent); }
.m-chat-text { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13.5px; color: var(--text); }
.m-chat-uhr { align-self: flex-end; font-size: 10.5px; color: var(--text3); }
.m-chat-eingabe { display: flex; gap: 6px; align-items: flex-end; padding: 8px 10px; border-top: 1px solid var(--rand); }
.m-chat-feld { flex: 1; }
.m-chat-feld textarea { max-height: 120px; }
.m-chat-senden { border: 0; background: var(--akzent); color: var(--fls, #fff); border-radius: 6px; width: 38px; height: 38px;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center; }
.m-ob-chat { position: relative; }
.m-ob-chat .m-ob-zahl { position: static !important; margin-left: 2px; }
"""
