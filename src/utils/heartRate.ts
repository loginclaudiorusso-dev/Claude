import type { BiologicalSex, HeartRateZone, UserProfile } from '@/types/health';

import { clamp } from './stats';

export const DEFAULT_MAX_HEART_RATE = 190;
export const DEFAULT_RESTING_HEART_RATE = 60;

/** Max HR: measured value, else Tanaka et al. (2001): 208 − 0.7 × age. */
export function estimateMaxHeartRate(profile: UserProfile, now: Date = new Date()): number {
  if (profile.maxHeartRate) return profile.maxHeartRate;
  if (profile.birthYear) {
    const age = now.getFullYear() - profile.birthYear;
    return Math.round(208 - 0.7 * age);
  }
  return DEFAULT_MAX_HEART_RATE;
}

/** Heart-rate reserve fraction (Karvonen), clamped to 0–1. */
export function heartRateReserve(bpm: number, restingHr: number, maxHr: number): number {
  if (maxHr <= restingHr) return 0;
  return clamp((bpm - restingHr) / (maxHr - restingHr), 0, 1);
}

/**
 * Zones on %HRR: Z1 50–60, Z2 60–70, Z3 70–80, Z4 80–90, Z5 ≥ 90.
 * Returns null below 50 % HRR (not training).
 */
export function heartRateZone(hrr: number): HeartRateZone | null {
  if (hrr >= 0.9) return 5;
  if (hrr >= 0.8) return 4;
  if (hrr >= 0.7) return 3;
  if (hrr >= 0.6) return 2;
  if (hrr >= 0.5) return 1;
  return null;
}

/**
 * Banister TRIMP load per minute at a given heart-rate reserve fraction:
 * HRr × a × e^(b × HRr), with sex-specific constants (Banister 1991).
 */
export function banisterTrimpPerMinute(hrr: number, sex?: BiologicalSex): number {
  const [a, b] = sex === 'female' ? [0.86, 1.67] : [0.64, 1.92];
  return hrr * a * Math.exp(b * hrr);
}
