"""Bildschirmfoto (0.96) – das INNternat-Fenster mit einem Klick als Bild.

* **Fenster aufnehmen:** nimmt das aktive Fenster (das ist INNternat, denn dort wurde gerade geklickt) so auf, wie es auf
  dem Bildschirm steht, legt das Bild in die **Zwischenablage** (Strg+V im Chat, in Outlook, Word …) und speichert es
  zusätzlich als PNG in ``Bilder\\INNternat``.
* **Ausschnitt wählen:** öffnet das Ausschneidewerkzeug von Windows (wie Win+Umschalt+S).

Nur Windows-Bordmittel (ctypes) – keine zusätzliche Bibliothek. Der PNG-Kodierer ist rein und getestet.
Gespeichert wird lokal beim Benutzer, NIE im Netzwerk- oder Datenordner.
"""

from __future__ import annotations

import datetime as _dt
import os
import struct
import sys
import zlib
from pathlib import Path

ORDNER_NAME = "INNternat"


# --------------------------------------------------------------------------------------------------------------------
# rein: PNG aus BGRA-Zeilen (oben nach unten)
# --------------------------------------------------------------------------------------------------------------------
def png(breite: int, hoehe: int, bgra: bytes) -> bytes:
    """PNG (RGB, 8 Bit) aus BGRA-Pixeln, Zeilen von oben nach unten."""
    if breite <= 0 or hoehe <= 0 or len(bgra) < breite * hoehe * 4:
        raise ValueError("Bildgröße passt nicht zu den Pixeln")
    zeile = breite * 4
    roh = bytearray()
    for y in range(hoehe):
        z = bgra[y * zeile:(y + 1) * zeile]
        rgb = bytearray(breite * 3)
        rgb[0::3] = z[2::4]
        rgb[1::3] = z[1::4]
        rgb[2::3] = z[0::4]
        roh += b"\x00" + rgb                                      # Filter „keiner“ je Zeile

    def block(art: bytes, daten: bytes) -> bytes:
        return struct.pack(">I", len(daten)) + art + daten + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)

    kopf = struct.pack(">IIBBBBB", breite, hoehe, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + block(b"IHDR", kopf) + block(b"IDAT", zlib.compress(bytes(roh), 6)) + block(b"IEND", b"")


def dib(breite: int, hoehe: int, bgra: bytes) -> bytes:
    """Geräteunabhängige Bitmap (CF_DIB) für die Zwischenablage – 32 Bit, oben nach unten."""
    kopf = struct.pack("<IiiHHIIiiII", 40, breite, -hoehe, 1, 32, 0, breite * hoehe * 4, 2835, 2835, 0, 0)
    return kopf + bytes(bgra[:breite * hoehe * 4])


def dateiname(jetzt: _dt.datetime | None = None, seite: str = "") -> str:
    jetzt = jetzt or _dt.datetime.now()
    sauber = "".join(c for c in seite if c.isalnum() or c in "-_ ").strip().replace(" ", "_")[:40]
    return f"INNternat_{jetzt:%Y-%m-%d_%H-%M-%S}" + (f"_{sauber}" if sauber else "") + ".png"


def ordner() -> Path:
    basis = Path(os.environ.get("USERPROFILE") or Path.home())
    for name in ("Pictures", "Bilder"):
        if (basis / name).is_dir():
            return basis / name / ORDNER_NAME
    return basis / ORDNER_NAME


def verfuegbar() -> bool:
    return sys.platform == "win32"


# --------------------------------------------------------------------------------------------------------------------
# Windows: aufnehmen, Zwischenablage, Ausschneidewerkzeug
# --------------------------------------------------------------------------------------------------------------------
def _aufnehmen_win() -> tuple[int, int, bytes]:
    import ctypes
    from ctypes import wintypes

    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    try:
        u32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))     # echte Pixel, auch bei 125 %/150 % Skalierung
    except Exception:
        pass
    hwnd = u32.GetForegroundWindow()
    r = wintypes.RECT()
    try:                                                          # ohne unsichtbaren Schattenrand
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r))
    except Exception:
        r = wintypes.RECT()
    if r.right - r.left <= 0:
        u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        raise OSError("Kein Fenster gefunden")
    bild_dc = u32.GetDC(0)                                        # vom Bildschirm – zeigt genau, was man sieht
    mem = g32.CreateCompatibleDC(bild_dc)
    bmp = g32.CreateCompatibleBitmap(bild_dc, w, h)
    alt = g32.SelectObject(mem, bmp)
    try:
        if not g32.BitBlt(mem, 0, 0, w, h, bild_dc, r.left, r.top, 0x00CC0020 | 0x40000000):   # SRCCOPY|CAPTUREBLT
            raise OSError("Aufnahme fehlgeschlagen")

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]
        bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        puffer = ctypes.create_string_buffer(w * h * 4)
        g32.SelectObject(mem, alt)
        if not g32.GetDIBits(mem, bmp, 0, h, puffer, ctypes.byref(bih), 0):
            raise OSError("Bild konnte nicht gelesen werden")
        return w, h, puffer.raw
    finally:
        g32.DeleteObject(bmp)
        g32.DeleteDC(mem)
        u32.ReleaseDC(0, bild_dc)


def _zwischenablage_win(dib_daten: bytes, png_daten: bytes) -> bool:
    import ctypes

    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

    def ablegen(fmt: int, daten: bytes) -> None:
        h = k32.GlobalAlloc(0x0002, len(daten))                  # GMEM_MOVEABLE
        p = k32.GlobalLock(h)
        ctypes.memmove(p, daten, len(daten))
        k32.GlobalUnlock(h)
        u32.SetClipboardData(fmt, h)                              # gehört danach der Zwischenablage

    for _ in range(10):
        if u32.OpenClipboard(0):
            break
        import time
        time.sleep(.05)
    else:
        return False
    try:
        u32.EmptyClipboard()
        ablegen(8, dib_daten)                                     # CF_DIB – Word, Outlook, Paint, Browser
        ablegen(u32.RegisterClipboardFormatW("PNG"), png_daten)   # verlustfrei für Programme, die PNG kennen
        return True
    finally:
        u32.CloseClipboard()


def aufnehmen(seite: str = "", speichern: bool = True) -> dict:
    """Fenster aufnehmen → Zwischenablage und (optional) PNG-Datei. Gibt {ok, pfad, ablage, fehler} zurück."""
    if not verfuegbar():
        return {"ok": False, "fehler": "Bildschirmfotos gehen nur unter Windows."}
    try:
        w, h, bgra = _aufnehmen_win()
        p_daten = png(w, h, bgra)
        ablage = _zwischenablage_win(dib(w, h, bgra), p_daten)
        pfad = ""
        if speichern:
            ziel = ordner()
            ziel.mkdir(parents=True, exist_ok=True)
            pfad = str(ziel / dateiname(seite=seite))
            Path(pfad).write_bytes(p_daten)
        return {"ok": True, "pfad": pfad, "ablage": ablage, "groesse": (w, h)}
    except Exception as e:                                        # noqa: BLE001 – nie das Programm stören
        return {"ok": False, "fehler": f"Bildschirmfoto nicht möglich: {e}"}


def ausschnitt() -> dict:
    """Ausschneidewerkzeug von Windows öffnen (Bereich mit der Maus wählen, landet in der Zwischenablage)."""
    if not verfuegbar():
        return {"ok": False, "fehler": "Nur unter Windows."}
    try:
        os.startfile("ms-screenclip:")                            # type: ignore[attr-defined]
        return {"ok": True}
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "fehler": f"Ausschneidewerkzeug nicht verfügbar: {e}"}
