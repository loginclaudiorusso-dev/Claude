import type { SFSymbol } from 'expo-symbols';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/theme';

import { GlassCard } from './GlassCard';
import { Icon } from './Icon';

type Props = {
  symbol: SFSymbol;
  tint: string;
  label: string;
  value: string;
  unit?: string;
  /** Secondary line, e.g. deviation from baseline. */
  detail?: string;
  style?: object;
};

/** Compact metric tile: label, big number, optional detail. */
export function StatTile({ symbol, tint, label, value, unit, detail, style }: Props) {
  return (
    <GlassCard style={[styles.card, style]}>
      <View style={styles.header}>
        <Icon name={symbol} size={13} color={tint} />
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
      </View>
      <Text style={styles.value} accessibilityLabel={`${label}: ${value} ${unit ?? ''}`}>
        {value}
        {unit ? <Text style={styles.unit}> {unit}</Text> : null}
      </Text>
      {detail ? (
        <Text style={styles.detail} numberOfLines={1}>
          {detail}
        </Text>
      ) : null}
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  card: { minWidth: 0 },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs + 2 },
  label: { ...typography.footnote, fontWeight: '600', color: colors.labelSecondary, flexShrink: 1 },
  value: {
    ...typography.title2,
    color: colors.label,
    marginTop: spacing.sm,
    fontVariant: ['tabular-nums'],
  },
  unit: { ...typography.footnote, color: colors.labelSecondary, fontWeight: '500' },
  detail: { ...typography.caption1, color: colors.labelTertiary, marginTop: 2 },
});
