/**
 * Apple-HIG-inspired dark palette. System colours follow iOS dark-mode values;
 * semantic metric accents map scores to meaning (recovery, strain, sleep, energy).
 */
export const palette = {
  // iOS system colours (dark appearance)
  green: '#30D158',
  yellow: '#FFD60A',
  orange: '#FF9F0A',
  red: '#FF453A',
  blue: '#0A84FF',
  indigo: '#5E5CE6',
  purple: '#BF5AF2',
  teal: '#40C8E0',
  mint: '#63E6E2',
  pink: '#FF375F',
} as const;

export const colors = {
  background: '#000000',
  backgroundElevated: '#0B0B0F',
  surface: 'rgba(28, 28, 30, 0.72)',
  surfaceSolid: '#1C1C1E',
  surfaceSecondary: '#2C2C2E',
  separator: 'rgba(84, 84, 88, 0.45)',
  border: 'rgba(255, 255, 255, 0.08)',

  label: '#FFFFFF',
  labelSecondary: 'rgba(235, 235, 245, 0.62)',
  labelTertiary: 'rgba(235, 235, 245, 0.32)',

  tint: palette.green,

  // Semantic metric accents
  recovery: palette.green,
  strain: palette.orange,
  strainHigh: palette.red,
  sleep: palette.blue,
  energy: palette.yellow,
  hrv: palette.mint,
  heart: palette.pink,
  coach: palette.purple,
} as const;

/**
 * Sleep-stage palette, validated with the dataviz checker on the dark card
 * surface (#1C1C1E): lightness band, chroma, contrast ≥ 3:1, CVD ΔE ≥ 8 and
 * normal-vision ΔE ≥ 15 for adjacent pairs in stacking order deep → REM → core → awake.
 * Keep that order wherever stages sit next to each other.
 */
export const sleepStageColors = {
  deep: '#9085E9',
  rem: '#199E70',
  core: '#3987E5',
  awake: '#D95926',
} as const;

/** Recessive chart chrome. */
export const chartColors = {
  grid: 'rgba(235, 235, 245, 0.10)',
  axisText: 'rgba(235, 235, 245, 0.45)',
  crosshair: 'rgba(235, 235, 245, 0.35)',
  baseline: 'rgba(235, 235, 245, 0.30)',
  /** Ring behind markers so overlapping marks stay separable. */
  markerRing: '#1C1C1E',
  track: 'rgba(120, 120, 128, 0.24)',
} as const;

/** Map a 0–100 recovery value to its traffic-light colour. */
export function recoveryColor(score: number): string {
  if (score >= 67) return palette.green;
  if (score >= 34) return palette.yellow;
  return palette.red;
}

/** Map a 0–21 strain value to its accent colour. */
export function strainColor(strain: number): string {
  if (strain >= 18) return palette.red;
  if (strain >= 14) return palette.orange;
  if (strain >= 10) return palette.yellow;
  return palette.blue;
}
