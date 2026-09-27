import type { SFSymbol } from 'expo-symbols';
import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/theme';

import { Icon } from './Icon';

type Props = { symbol: SFSymbol; title: string; tint: string; accessory?: ReactNode };

/** Small caps-style card title with a tinted SF Symbol, as in the Health app. */
export function CardHeader({ symbol, title, tint, accessory }: Props) {
  return (
    <View style={styles.row}>
      <Icon name={symbol} size={15} color={tint} />
      <Text style={[styles.title, { color: tint }]}>{title}</Text>
      <View style={styles.spacer} />
      {accessory}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs + 2,
    marginBottom: spacing.md,
  },
  title: { ...typography.subheadline, fontWeight: '600' },
  spacer: { flex: 1 },
});

export const cardTextStyles = StyleSheet.create({
  value: { ...typography.title1, color: colors.label, fontVariant: ['tabular-nums'] },
  unit: { ...typography.subheadline, color: colors.labelSecondary },
  caption: { ...typography.footnote, color: colors.labelSecondary },
});
