"""Drucken bzw. als PDF speichern von HTML (QTextDocument) – gemeinsam für alle Seiten."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog

from .. import speicher


def dokument_drucken(drucker, html: str, quer: bool) -> None:
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QTextDocument

    drucker.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Landscape if quer else QPageLayout.Portrait,
                                      QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter))
    doc = QTextDocument()
    doc.setHtml(html)
    # Seitengröße in Bildschirm-Einheiten setzen – sonst nutzt Qt nur ~¾ der Seitenbreite
    dpi = QGuiApplication.primaryScreen().logicalDotsPerInchX() if QGuiApplication.primaryScreen() else 96
    flaeche = drucker.pageLayout().paintRectPoints().size()
    doc.setPageSize(QSizeF(flaeche.width() * dpi / 72, flaeche.height() * dpi / 72))
    doc.print_(drucker)


def html_ausgeben(eltern, zustand, html: str, quer: bool, pdf_name: str | None = None) -> bool:
    """Druckdialog – oder mit ``pdf_name`` als PDF speichern. Meldet das Ergebnis über ``zustand.meldung``."""
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter

    drucker = QPrinter(QPrinter.HighResolution)
    if pdf_name:
        start = speicher.einstellungen().get("export_ordner") or str(Path.home())
        pfad, _ = QFileDialog.getSaveFileName(eltern, "PDF speichern", str(Path(start) / pdf_name), "PDF (*.pdf)")
        if not pfad:
            return False
        speicher.einstellung_setzen("export_ordner", str(Path(pfad).parent))
        drucker.setOutputFormat(QPrinter.PdfFormat)
        drucker.setOutputFileName(pfad if pfad.lower().endswith(".pdf") else pfad + ".pdf")
    elif QPrintDialog(drucker, eltern).exec() != QDialog.Accepted:
        return False
    dokument_drucken(drucker, html, quer)
    zustand.meldung.emit(f"PDF gespeichert: {Path(drucker.outputFileName()).name}" if pdf_name
                         else "An den Drucker geschickt.", "ok")
    return True
