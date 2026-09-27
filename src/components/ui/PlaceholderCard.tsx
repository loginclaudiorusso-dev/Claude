import { SymbolView, type SFSymbol } from 'expo-symbols';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/theme';

import { GlassCard } from './GlassCard';

type Props = {
  symbol: SFSymbol;
  title: string;
  subtitle: string;
  tint?: string;
};

/** Temporary card used by the scaffold screens until the real modules land. */
export function PlaceholderCard({ symbol, title, subtitle, tint = colors.tint }: Props) {
  return (
    <GlassCard>
      <View style={styles.row}>
        <SymbolView name={symbol} tintColor={tint} size={28} type="hierarchical" />
        <View style={styles.text}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
      </View>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  text: { flex: 1, gap: spacing.xxs },
  title: { ...typography.headline, color: colors.label },
  subtitle: { ...typography.subheadline, color: colors.labelSecondary },
});
