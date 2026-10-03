# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller belegungsdashboard_gui.spec
# Ergebnis: dist/Belegungsdashboard.exe (eine Datei, ohne Konsole) und
#           dist/Belegungsdashboard-Export.exe (Konsole, schreibt Belegungsdashboard.html)
#
# llama_cpp wird nicht mehr gebündelt: lokale Modelle laufen jetzt über Ollama/LM Studio
# (OpenAI-kompatible Schnittstelle). Die exe wird dadurch deutlich kleiner und startet schneller.

from PyInstaller.utils.hooks import collect_submodules

versteckt = (
    collect_submodules("belegung")
    + ["keyring.backends.Windows", "win32com.client", "pythoncom", "pywintypes", "pypdf"]
    + ["statsmodels.tsa.holtwinters", "statsmodels.tsa.statespace._filters"]
)
ausschluesse = ["tkinter", "PyQt5", "PyQt6", "IPython", "jupyter", "sklearn", "llama_cpp", "pytest"]


def analyse(skript):
    return Analysis(
        [skript], pathex=[], binaries=[], datas=[], hiddenimports=versteckt, hookspath=[],
        hooksconfig={}, runtime_hooks=[], excludes=ausschluesse, noarchive=False, optimize=1,
    )


gui = analyse("belegungsdashboard_gui.py")
exe_gui = EXE(
    PYZ(gui.pure), gui.scripts, gui.binaries, gui.datas, [],
    name="Belegungsdashboard", debug=False, strip=False, upx=False, console=False,
    icon="assets/icon.ico" if __import__("os").path.exists("assets/icon.ico") else None,
)

export = analyse("belegungsdashboard_export.py")
exe_export = EXE(
    PYZ(export.pure), export.scripts, export.binaries, export.datas, [],
    name="Belegungsdashboard-Export", debug=False, strip=False, upx=False, console=True,
)
