import { StyleSheet, Text, View } from 'react-native';

import { Hypnogram } from '@/components/charts';
import { CardHeader, GlassCard, cardTextStyles } from '@/components/ui';
import type { SleepAnalysis, SleepSession } from '@/types/health';
import { colors, spacing, typography } from '@/theme';
import { formatDuration } from '@/utils/format';

type Props = { analysis: SleepAnalysis; session: SleepSession };

export function SleepCard({ analysis, session }: Props) {
  const deficit = analysis.sleepNeedMinutes - analysis.totalSleepMinutes;
  return (
    <GlassCard>
      <CardHeader
        symbol="bed.double.fill"
        title="Schlaf"
        tint={colors.sleep}
        accessory={<Text style={styles.score}>{analysis.score} Punkte</Text>}
      />
      <View style={styles.row}>
        <View style={styles.stat}>
          <Text style={cardTextStyles.value}>{formatDuration(analysis.totalSleepMinutes)}</Text>
          <Text style={cardTextStyles.caption}>
            von {formatDuration(analysis.sleepNeedMinutes)} Bedarf · {analysis.performancePct} %
          </Text>
        </View>
      </View>
      <View style={styles.chips}>
        <Chip label="Effizienz" value={`${Math.round(analysis.efficiency * 100)} %`} />
        <Chip label="Defizit heute" value={deficit > 0 ? formatDuration(deficit) : '–'} />
        <Chip label="Schlafschuld" value={formatDuration(analysis.debtMinutes)} />
      </View>
      <View style={styles.chart}>
        <Hypnogram session={session} />
      </View>
    </GlassCard>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.chip}>
      <Text style={styles.chipLabel}>{label}</Text>
      <Text style={styles.chipValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  stat: { gap: 2 },
  score: { ...typography.footnote, fontWeight: '600', color: colors.labelSecondary },
  chips: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  chip: {
    flex: 1,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: 12,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm + 2,
  },
  chipLabel: { ...typography.caption2, color: colors.labelSecondary },
  chipValue: { ...typography.subheadline, fontWeight: '600', color: colors.label, marginTop: 2 },
  chart: { marginTop: spacing.lg },
});
