import type { RawHealthRecords } from '../raw';
import { parseHealthAutoExport, isHealthAutoExportJson } from './healthAutoExport';
import { looksLikeHealthCsv, parseHealthCsv } from './csv';

export { parseHealthAutoExport, parseHealthCsv };

export class UnsupportedImportError extends Error {}

/** Detects the format of an exported file and parses it into raw records. */
export function parseHealthExport(text: string, fileName = ''): RawHealthRecords {
  const trimmed = text.trimStart();
  if (trimmed.startsWith('{') || /\.json$/i.test(fileName)) {
    let json: unknown;
    try {
      json = JSON.parse(trimmed);
    } catch {
      throw new UnsupportedImportError('Die JSON-Datei ist beschädigt.');
    }
    if (!isHealthAutoExportJson(json)) {
      throw new UnsupportedImportError(
        'Unbekanntes JSON-Format. Erwartet wird ein Health-Auto-Export-JSON.',
      );
    }
    return parseHealthAutoExport(json);
  }
  if (looksLikeHealthCsv(trimmed)) return parseHealthCsv(trimmed);
  throw new UnsupportedImportError(
    'Dateiformat nicht erkannt. Unterstützt: Health Auto Export JSON oder CSV.',
  );
}
