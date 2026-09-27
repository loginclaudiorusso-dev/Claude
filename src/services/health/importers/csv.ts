import Papa from 'papaparse';

import { HOUR_MS, startOfDay, toDayKey } from '@/utils/analytics';

import { emptyRecords, type RawHealthRecords, type ValueSample } from '../raw';
import { parseDate, parseNumber, toKcal } from './parseUtils';
import { synthesizeSleepSegments } from './sleepSynthesis';

/**
 * Importer for CSV exports (Health Auto Export and similar), one row per
 * time bucket. Columns are matched by name so column order and extra columns
 * don't matter, e.g. "Heart Rate Variability (ms)", "Active Energy (kJ)",
 * "Sleep Analysis [Deep] (hr)".
 */

type ColumnKind =
  | 'date'
  | 'hrv'
  | 'heartRate'
  | 'restingHeartRate'
  | 'steps'
  | 'activeEnergy'
  | 'basalEnergy'
  | 'vo2Max'
  | 'respiratoryRate'
  | 'sleepDeep'
  | 'sleepCore'
  | 'sleepRem'
  | 'sleepAwake'
  | 'sleepAsleep'
  | 'sleepInBed';

const COLUMN_PATTERNS: [ColumnKind, RegExp][] = [
  ['date', /^(date(\s*\/\s*time)?|start|timestamp)\b/i],
  ['hrv', /heart\s*rate\s*variability|\bhrv\b/i],
  ['restingHeartRate', /resting\s*heart\s*rate/i],
  ['heartRate', /^heart\s*rate(\s*\[avg\])?(\s*\(|$)/i],
  ['steps', /step\s*count|^steps\b/i],
  ['activeEnergy', /active\s*energy/i],
  ['basalEnergy', /(basal|resting)\s*energy/i],
  ['vo2Max', /vo2\s*max/i],
  ['respiratoryRate', /respiratory\s*rate/i],
  ['sleepDeep', /sleep.*\[deep\]/i],
  ['sleepCore', /sleep.*\[core\]/i],
  ['sleepRem', /sleep.*\[rem\]/i],
  ['sleepAwake', /sleep.*\[awake\]/i],
  ['sleepInBed', /sleep.*\[in\s*bed\]/i],
  ['sleepAsleep', /sleep.*\[(asleep|total)\]|^sleep\s*analysis(\s*\(|$)/i],
];

/** Assumed wake-up time when a CSV only provides nightly sleep totals. */
const ASSUMED_WAKE_HOUR = 7;

function mapColumns(headers: string[]): Map<ColumnKind, string> {
  const map = new Map<ColumnKind, string>();
  for (const header of headers) {
    const kind = COLUMN_PATTERNS.find(([, re]) => re.test(header.trim()))?.[0];
    if (kind && !map.has(kind)) map.set(kind, header);
  }
  return map;
}

export function looksLikeHealthCsv(text: string): boolean {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? '';
  return /date|time/i.test(firstLine) && /heart|step|energy|sleep|vo2/i.test(firstLine);
}

export function parseHealthCsv(text: string): RawHealthRecords {
  const { data, meta } = Papa.parse<Record<string, string>>(text.trim(), {
    header: true,
    skipEmptyLines: true,
    delimitersToGuess: [',', ';', '\t'],
  });
  const columns = mapColumns(meta.fields ?? []);
  const dateColumn = columns.get('date');
  if (!dateColumn) throw new Error('CSV enthält keine Datumsspalte.');

  const records = emptyRecords('import');
  const unit = (kind: ColumnKind) => columns.get(kind);

  for (const row of data) {
    const timestamp = parseDate(row[dateColumn]);
    if (timestamp === undefined) continue;
    const num = (kind: ColumnKind) => {
      const col = columns.get(kind);
      return col ? parseNumber(row[col]) : undefined;
    };
    const push = (list: ValueSample[], value: number | undefined) => {
      if (value !== undefined) list.push({ timestamp, value });
    };

    const hrv = num('hrv');
    if (hrv !== undefined) records.hrv.push({ timestamp, sdnnMs: hrv });
    const hr = num('heartRate');
    if (hr !== undefined) records.heartRate.push({ timestamp, bpm: hr });
    push(records.restingHeartRate, num('restingHeartRate'));
    push(records.steps, num('steps'));
    const active = num('activeEnergy');
    if (active !== undefined)
      records.activeEnergyKcal.push({ timestamp, value: toKcal(active, unit('activeEnergy')) });
    const basal = num('basalEnergy');
    if (basal !== undefined)
      records.basalEnergyKcal.push({ timestamp, value: toKcal(basal, unit('basalEnergy')) });
    push(records.vo2Max, num('vo2Max'));
    push(records.respiratoryRate, num('respiratoryRate'));

    const deep = num('sleepDeep');
    const core = num('sleepCore');
    const rem = num('sleepRem');
    const awake = num('sleepAwake');
    const asleep = num('sleepAsleep') ?? ((deep ?? 0) + (core ?? 0) + (rem ?? 0) || undefined);
    const inBed = num('sleepInBed');
    const totalHours = inBed ?? (asleep !== undefined ? asleep + (awake ?? 0) : undefined);
    if (totalHours && totalHours > 0) {
      // Row date is the night's day; without times we assume waking at 07:00.
      const end = startOfDay(toDayKey(timestamp)) + ASSUMED_WAKE_HOUR * HOUR_MS;
      records.sleepSegments.push(
        ...synthesizeSleepSegments({
          start: end - totalHours * HOUR_MS,
          end,
          deep,
          core,
          rem,
          awake,
          asleep,
        }),
      );
    }
  }
  return records;
}
