import { StyleSheet, Text, View } from 'react-native';

import { ScoreRing } from '@/components/charts';
import { GlassCard } from '@/components/ui';
import type { DailySummary } from '@/types/health';
import { colors, recoveryColor, spacing, strainColor, typography } from '@/theme';
import { STRAIN_LABEL, ZONE_LABEL, formatNumber } from '@/utils/format';

type Props = { summary: DailySummary; compact?: boolean };

/** Hero card: readiness and strain rings side by side. */
export function RecoveryStrainCard({ summary, compact }: Props) {
  const { readiness, strain, strainTarget } = summary;
  const size = compact ? 128 : 148;
  const rColor = readiness ? recoveryColor(readiness.score) : colors.labelTertiary;
  const sColor = strainColor(strain.score);

  return (
    <GlassCard>
      <View style={styles.row}>
        <View style={styles.col}>
          <ScoreRing
            progress={(readiness?.score ?? 0) / 100}
            color={rColor}
            size={size}
            accessibilityLabel={
              readiness
                ? `Erholung ${readiness.score} Prozent, ${ZONE_LABEL[readiness.zone]}`
                : 'Erholung: keine Daten'
            }
          >
            <Text style={styles.value}>{readiness ? readiness.score : '–'}</Text>
            <Text style={styles.unit}>%</Text>
          </ScoreRing>
          <Text style={styles.title}>Erholung</Text>
          <Text style={[styles.status, { color: rColor }]}>
            {readiness
              ? readiness.confidence === 'calibrating'
                ? 'Kalibriert…'
                : ZONE_LABEL[readiness.zone]
              : 'Keine Daten'}
          </Text>
        </View>
        <View style={styles.col}>
          <ScoreRing
            progress={strain.score / 21}
            color={sColor}
            size={size}
            accessibilityLabel={`Belastung ${formatNumber(strain.score, 1)} von 21, ${STRAIN_LABEL[strain.level]}`}
          >
            <Text style={styles.value}>{formatNumber(strain.score, 1)}</Text>
            <Text style={styles.unit}>von 21</Text>
          </ScoreRing>
          <Text style={styles.title}>Belastung</Text>
          <Text style={[styles.status, { color: sColor }]}>{STRAIN_LABEL[strain.level]}</Text>
        </View>
      </View>
      {strainTarget ? (
        <Text style={styles.footer}>
          Empfohlene Belastung heute: {formatNumber(strainTarget.min, 1)}–
          {formatNumber(strainTarget.max, 1)}
        </Text>
      ) : null}
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-around', gap: spacing.lg },
  col: { alignItems: 'center', gap: 2 },
  value: { ...typography.metric, color: colors.label },
  unit: { ...typography.caption1, color: colors.labelSecondary, marginTop: -4 },
  title: { ...typography.headline, color: colors.label, marginTop: spacing.md },
  status: { ...typography.subheadline, fontWeight: '600' },
  footer: {
    ...typography.footnote,
    color: colors.labelSecondary,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
