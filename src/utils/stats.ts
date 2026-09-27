/** Small, dependency-free statistics helpers used by the scoring models. */

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function round(value: number, decimals = 0): number {
  const f = 10 ** decimals;
  return Math.round(value * f) / f;
}

export function sum(values: readonly number[]): number {
  let total = 0;
  for (const v of values) total += v;
  return total;
}

export function mean(values: readonly number[]): number | null {
  return values.length === 0 ? null : sum(values) / values.length;
}

/** Sample standard deviation (n − 1). Returns 0 for fewer than two values. */
export function standardDeviation(values: readonly number[]): number {
  if (values.length < 2) return 0;
  const m = sum(values) / values.length;
  let sq = 0;
  for (const v of values) sq += (v - m) ** 2;
  return Math.sqrt(sq / (values.length - 1));
}

export function median(values: readonly number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1]! + sorted[mid]!) / 2 : sorted[mid]!;
}

/** Standard logistic function 1 / (1 + e^-x). */
export function logistic(x: number): number {
  return 1 / (1 + Math.exp(-x));
}

/** Linear interpolation of `value` from [inMin, inMax] to [0, 1], clamped. */
export function normalize(value: number, inMin: number, inMax: number): number {
  if (inMax === inMin) return value >= inMax ? 1 : 0;
  return clamp((value - inMin) / (inMax - inMin), 0, 1);
}

/** Least-squares slope of y over x = 0..n-1, skipping null values. */
export function linearSlope(values: readonly (number | null)[]): number | null {
  const pts: [number, number][] = [];
  values.forEach((y, x) => {
    if (y !== null && Number.isFinite(y)) pts.push([x, y]);
  });
  if (pts.length < 2) return null;
  const mx = sum(pts.map(([x]) => x)) / pts.length;
  const my = sum(pts.map(([, y]) => y)) / pts.length;
  let num = 0;
  let den = 0;
  for (const [x, y] of pts) {
    num += (x - mx) * (y - my);
    den += (x - mx) ** 2;
  }
  return den === 0 ? 0 : num / den;
}

/** Weighted average that ignores undefined entries and renormalises weights. */
export function weightedAverage(
  entries: readonly { value: number | undefined; weight: number }[],
): number | null {
  let total = 0;
  let weights = 0;
  for (const { value, weight } of entries) {
    if (value === undefined || !Number.isFinite(value)) continue;
    total += value * weight;
    weights += weight;
  }
  return weights === 0 ? null : total / weights;
}
