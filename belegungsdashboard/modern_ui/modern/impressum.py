"""1.50: Wer INNternat erstellt hat – steht unten in der Statusleiste und unter Informationen & Sicherung."""

AUTOR = "Claudio Russo"
ROLLE = "Konzept und Entwicklung"
JAHR = "2026"


def zeile() -> str:
    return f"{ROLLE}: {AUTOR}"


def kurz() -> str:
    return f"erstellt von {AUTOR}"
