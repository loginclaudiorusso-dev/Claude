import { StyleSheet, View } from 'react-native';

import { StatTile } from '@/components/ui';
import type { DailySummary } from '@/types/health';
import { colors, spacing } from '@/theme';
import { formatNumber, formatSigned } from '@/utils/format';

type Props = { summary: DailySummary; columns: number };

/** Key vitals grid; wraps to 2 or 3 columns depending on width. */
export function MetricTiles({ summary, columns }: Props) {
  const { metrics, readiness } = summary;
  const tiles = [
    {
      symbol: 'waveform.path.ecg' as const,
      tint: colors.hrv,
      label: 'HRV',
      value: metrics.hrvMs !== undefined ? formatNumber(metrics.hrvMs) : '–',
      unit: 'ms',
      detail:
        readiness?.hrvDeviationPct !== undefined
          ? `${formatSigned(readiness.hrvDeviationPct)} % vs. Ø 7 T`
          : undefined,
    },
    {
      symbol: 'heart.fill' as const,
      tint: colors.heart,
      label: 'Ruhepuls',
      value: metrics.restingHeartRate !== undefined ? formatNumber(metrics.restingHeartRate) : '–',
      unit: 'bpm',
      detail:
        readiness?.restingHeartRateDeviationBpm !== undefined
          ? `${formatSigned(readiness.restingHeartRateDeviationBpm)} bpm vs. Ø`
          : undefined,
    },
    {
      symbol: 'figure.walk' as const,
      tint: colors.recovery,
      label: 'Schritte',
      value: formatNumber(metrics.steps),
    },
    {
      symbol: 'flame.fill' as const,
      tint: colors.strain,
      label: 'Aktive Energie',
      value: formatNumber(metrics.activeEnergyKcal),
      unit: 'kcal',
    },
    {
      symbol: 'lungs.fill' as const,
      tint: colors.sleep,
      label: 'VO₂max',
      value: metrics.vo2Max !== undefined ? formatNumber(metrics.vo2Max, 1) : '–',
      unit: 'ml/kg/min',
    },
    {
      symbol: 'figure.run' as const,
      tint: colors.strain,
      label: 'Training',
      value: String(metrics.workoutMinutes),
      unit: 'min',
      detail: metrics.workoutCount
        ? `${metrics.workoutCount} Workout${metrics.workoutCount > 1 ? 's' : ''}`
        : 'Ruhetag',
    },
  ];
  const basis = `${100 / Math.max(2, columns)}%` as const;
  return (
    <View style={styles.grid}>
      {tiles.map((t) => (
        <View key={t.label} style={[styles.cell, { flexBasis: basis }]}>
          <StatTile {...t} style={styles.tile} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -spacing.xs - 2 },
  cell: { padding: spacing.xs + 2 },
  tile: { minWidth: 0 },
});
