import { StyleSheet, Text, View } from 'react-native';

import type { HealthDataMode } from '@/services/health';
import { colors, radius, spacing, typography } from '@/theme';

const LABEL: Record<HealthDataMode, string> = {
  healthkit: 'Apple Health',
  import: 'Importierte Daten',
  demo: 'Demo-Daten',
};

export function DataSourceBadge({ mode }: { mode: HealthDataMode | null }) {
  if (!mode) return null;
  return (
    <View style={[styles.badge, mode === 'demo' && styles.demo]}>
      <Text style={styles.text}>{LABEL[mode]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceSecondary,
  },
  demo: { backgroundColor: 'rgba(255, 159, 10, 0.18)' },
  text: { ...typography.caption1, fontWeight: '600', color: colors.labelSecondary },
});
