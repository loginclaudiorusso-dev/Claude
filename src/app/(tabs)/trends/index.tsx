import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DailyBarChart, SleepStagesChart, TrendLineChart } from '@/components/charts';
import {
  CardHeader,
  EmptyState,
  GlassCard,
  LoadingView,
  Screen,
  SegmentedControl,
  StatTile,
} from '@/components/ui';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useHealthStore } from '@/store/healthStore';
import type { MetricTrend, TrendDirection, TrendWindow } from '@/types/health';
import { colors, spacing, typography } from '@/theme';
import { buildTrendReport, dayRange } from '@/utils/analytics';
import { formatDuration, formatNumber, formatSigned } from '@/utils/format';

const DIRECTION: Record<TrendDirection, string> = {
  up: 'steigend',
  down: 'fallend',
  flat: 'stabil',
};

function trendCaption(t: MetricTrend, unit: string, digits = 0) {
  const avg =
    t.average === null ? '–' : `${formatNumber(t.average, digits)}${unit ? ` ${unit}` : ''}`;
  const change = t.changePct === null ? '' : ` · ${formatSigned(t.changePct, 1)} %`;
  return `Ø ${avg} · ${DIRECTION[t.direction]}${change}`;
}

function acwrLabel(r: number | null) {
  if (r === null) return 'Zu wenig Daten (≥ 14 Tage nötig)';
  if (r > 1.5) return 'Überlastungsrisiko – Umfang reduzieren';
  if (r > 1.3) return 'Erhöht – Erholung im Blick behalten';
  if (r < 0.8) return 'Unter gewohnter Last – Formverlust möglich';
  return 'Im optimalen Bereich (0,8–1,3)';
}

export default function TrendsScreen() {
  const { status, summaries } = useHealthStore();
  const [window, setWindow] = useState<TrendWindow>(7);
  const { isTablet } = useResponsiveLayout();

  const report = useMemo(() => buildTrendReport(summaries, window), [summaries, window]);
  const byDate = useMemo(() => new Map(summaries.map((s) => [s.date, s])), [summaries]);
  const dates = useMemo(
    () => (summaries.length ? dayRange(summaries.at(-1)!.date, window) : []),
    [summaries, window],
  );

  if (status === 'idle' || (status === 'loading' && !report)) return <LoadingView />;
  if (!report)
    return (
      <EmptyState
        symbol="chart.xyaxis.line"
        title="Noch keine Trends"
        message="Sobald Daten vorliegen, erscheinen hier deine Verläufe."
      />
    );

  const readinessAvg = report.readiness.average;
  const cards = [
    <GlassCard key="readiness">
      <CardHeader symbol="heart.circle.fill" title="Erholung" tint={colors.recovery} />
      <Text style={styles.caption}>{trendCaption(report.readiness, '%')}</Text>
      <TrendLineChart
        points={report.readiness.points}
        color={colors.recovery}
        reference={
          readinessAvg !== null
            ? { value: readinessAvg, label: `Ø ${formatNumber(readinessAvg)} %` }
            : null
        }
        formatValue={(v) => `${formatNumber(v)} %`}
        accessibilityLabel={`Erholung, ${window} Tage, ${DIRECTION[report.readiness.direction]}`}
      />
    </GlassCard>,
    <GlassCard key="hrv">
      <CardHeader symbol="waveform.path.ecg" title="Herzfrequenzvariabilität" tint={colors.hrv} />
      <Text style={styles.caption}>{trendCaption(report.hrv, 'ms')}</Text>
      <TrendLineChart
        points={report.hrv.points}
        color={colors.hrv}
        reference={
          report.hrv.average !== null
            ? { value: report.hrv.average, label: `Ø ${formatNumber(report.hrv.average)} ms` }
            : null
        }
        formatValue={(v) => `${formatNumber(v, 1)} ms`}
        accessibilityLabel={`HRV, ${window} Tage, ${DIRECTION[report.hrv.direction]}`}
      />
    </GlassCard>,
    <GlassCard key="rhr">
      <CardHeader symbol="heart.fill" title="Ruhepuls" tint={colors.heart} />
      <Text style={styles.caption}>{trendCaption(report.restingHeartRate, 'bpm')}</Text>
      <TrendLineChart
        points={report.restingHeartRate.points}
        color={colors.heart}
        reference={
          report.restingHeartRate.average !== null
            ? {
                value: report.restingHeartRate.average,
                label: `Ø ${formatNumber(report.restingHeartRate.average)} bpm`,
              }
            : null
        }
        formatValue={(v) => `${formatNumber(v)} bpm`}
        accessibilityLabel={`Ruhepuls, ${window} Tage, ${DIRECTION[report.restingHeartRate.direction]}`}
      />
    </GlassCard>,
    <GlassCard key="strain">
      <CardHeader symbol="flame.fill" title="Trainingsbelastung" tint={colors.strain} />
      <Text style={styles.caption}>{trendCaption(report.strain, '', 1)} · Band: moderat 10–14</Text>
      <DailyBarChart
        points={report.strain.points}
        color={colors.strain}
        maxValue={21}
        band={{ min: 10, max: 14 }}
        formatValue={(v) => `Strain ${formatNumber(v, 1)}`}
        accessibilityLabel={`Tagesbelastung, ${window} Tage`}
      />
    </GlassCard>,
    <GlassCard key="sleep">
      <CardHeader symbol="moon.stars.fill" title="Schlafarchitektur" tint={colors.sleep} />
      <Text style={styles.caption}>
        Ø {report.sleepMinutes.average !== null ? formatDuration(report.sleepMinutes.average) : '–'}{' '}
        · Tief Ø{' '}
        {report.deepSleepMinutes.average !== null
          ? formatDuration(report.deepSleepMinutes.average)
          : '–'}{' '}
        · REM Ø{' '}
        {report.remSleepMinutes.average !== null
          ? formatDuration(report.remSleepMinutes.average)
          : '–'}
      </Text>
      <SleepStagesChart dates={dates} summaries={byDate} />
    </GlassCard>,
  ];

  return (
    <Screen>
      <SegmentedControl
        options={[
          { value: 7, label: '7 Tage' },
          { value: 30, label: '30 Tage' },
        ]}
        value={window}
        onChange={setWindow}
        accessibilityLabel="Zeitraum"
        style={styles.segmented}
      />
      <StatTile
        symbol="gauge.with.dots.needle.67percent"
        tint={colors.strain}
        label="Akut : Chronisch (7 T / 28 T)"
        value={report.acuteChronicRatio === null ? '–' : formatNumber(report.acuteChronicRatio, 2)}
        detail={acwrLabel(report.acuteChronicRatio)}
      />
      {isTablet ? (
        <View style={styles.grid}>
          {cards.map((c, i) => (
            <View key={i} style={styles.gridCell}>
              {c}
            </View>
          ))}
        </View>
      ) : (
        cards
      )}
      <Text style={styles.hint}>
        Tipp: Finger über ein Diagramm ziehen, um einzelne Tage anzuzeigen.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  caption: {
    ...typography.footnote,
    color: colors.labelSecondary,
    marginTop: -spacing.xs,
    marginBottom: spacing.xs,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -spacing.sm },
  gridCell: { width: '50%', padding: spacing.sm },
  segmented: { width: '100%', maxWidth: 420, alignSelf: 'center' },
  hint: { ...typography.caption1, color: colors.labelTertiary, textAlign: 'center' },
});
