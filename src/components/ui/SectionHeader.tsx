import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/theme';

type Props = { title: string; subtitle?: string; accessory?: ReactNode };

export function SectionHeader({ title, subtitle, accessory }: Props) {
  return (
    <View style={styles.row}>
      <View style={styles.text}>
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {accessory}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: spacing.md, marginTop: spacing.sm },
  text: { flex: 1 },
  title: { ...typography.title3, color: colors.label },
  subtitle: { ...typography.footnote, color: colors.labelSecondary, marginTop: 2 },
});
