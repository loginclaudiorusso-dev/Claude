// Check-in-Codes.
// - Raum-Codes wechseln täglich (Hash aus Geheimnis + Ort + Datum).
// - Event-Codes sind fest pro Event, gelten aber nur im Event-Zeitraum.
// - Der QR-Code der Betreuung rotiert zusätzlich alle 30 Sekunden (Zeitfenster im Inhalt),
//   damit abfotografierte Codes schnell verfallen. Die manuelle Eingabe nutzt den Tagescode.

import { dayKey } from './time';

const ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'; // ohne verwechselbare Zeichen (0/O, 1/I/L)
export const QR_PREFIX = 'INNM1';
export const ROTATION_MS = 30_000;
/** Wie viele 30-s-Fenster ein gescannter QR-Code alt sein darf. */
export const ROTATION_TOLERANCE = 4;

function fnv1a(input: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function toCode(seed: string, length = 6): string {
  let out = '';
  let h = fnv1a(seed);
  for (let i = 0; i < length; i++) {
    out += ALPHABET[h % ALPHABET.length];
    h = fnv1a(`${seed}:${i}:${h}`);
  }
  return out;
}

export function placeCode(secret: string, placeId: string, at: Date): string {
  return toCode(`${secret}|P|${placeId}|${dayKey(at)}`);
}

export function eventCode(secret: string, eventId: string): string {
  return toCode(`${secret}|E|${eventId}`);
}

export function rotationSlot(at: Date): number {
  return Math.floor(at.getTime() / ROTATION_MS);
}

export function qrPayload(kind: 'P' | 'E', id: string, code: string, at: Date): string {
  return `${QR_PREFIX}:${kind}:${id}:${code}:${rotationSlot(at)}`;
}

export type ParsedCode =
  | { kind: 'P' | 'E'; id: string; code: string; slot: number }
  | { kind: 'manual'; code: string }
  | { kind: 'invalid' };

export function normalizeManual(input: string): string {
  return input.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

export function parseCode(raw: string): ParsedCode {
  const trimmed = raw.trim();
  if (trimmed.startsWith(`${QR_PREFIX}:`)) {
    const [, kind, id, code, slot] = trimmed.split(':');
    if ((kind === 'P' || kind === 'E') && id && code && slot && /^\d+$/.test(slot)) {
      return { kind, id, code, slot: Number(slot) };
    }
    return { kind: 'invalid' };
  }
  const code = normalizeManual(trimmed);
  return code.length === 6 ? { kind: 'manual', code } : { kind: 'invalid' };
}

/** Lesbare Form für die Anzeige: „K7Q 2MX“. */
export function prettyCode(code: string): string {
  return `${code.slice(0, 3)} ${code.slice(3)}`;
}
