import * as DocumentPicker from 'expo-document-picker';
import { File } from 'expo-file-system';

import type { DailyHealthData } from '@/types/health';

import { buildDailyHealthData } from './buildDays';
import { parseHealthExport } from './importers';

export interface ImportResult {
  fileName: string;
  days: DailyHealthData[];
}

/**
 * Lets the user pick a Health Auto Export JSON/CSV file (Files app, iCloud
 * Drive, AirDrop …) and normalises it. Returns null if the picker is cancelled.
 */
export async function pickAndImportHealthFile(): Promise<ImportResult | null> {
  const result = await DocumentPicker.getDocumentAsync({
    type: [
      'application/json',
      'text/csv',
      'text/comma-separated-values',
      'text/plain',
      'public.json',
    ],
    copyToCacheDirectory: true,
    multiple: false,
  });
  if (result.canceled) return null;
  const asset = result.assets[0];
  if (!asset) return null;

  const file = new File(asset.uri);
  try {
    const text = await file.text();
    return {
      fileName: asset.name,
      days: buildDailyHealthData(parseHealthExport(text, asset.name)),
    };
  } finally {
    // The picker copied the file into our cache; don't keep a second copy of health data around.
    try {
      if (file.exists) file.delete();
    } catch {
      // Best effort only.
    }
  }
}
