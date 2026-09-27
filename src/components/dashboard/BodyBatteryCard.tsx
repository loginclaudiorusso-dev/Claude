import { StyleSheet, Text, View } from 'react-native';

import { BodyBatteryChart } from '@/components/charts';
import { CardHeader, GlassCard, cardTextStyles } from '@/components/ui';
import type { BodyBatteryResult } from '@/types/health';
import { colors, spacing } from '@/theme';

export function BodyBatteryCard({ battery }: { battery: BodyBatteryResult }) {
  return (
    <GlassCard>
      <CardHeader symbol="bolt.heart.fill" title="Body Battery" tint={colors.energy} />
      <View style={styles.row}>
        <Text style={cardTextStyles.value}>
          {Math.round(battery.currentLevel)}
          <Text style={cardTextStyles.unit}> / 100</Text>
        </Text>
        <Text style={cardTextStyles.caption}>
          Morgens {Math.round(battery.startLevel)} · verbraucht {Math.round(battery.drained)}
        </Text>
      </View>
      <View style={styles.chart}>
        <BodyBatteryChart points={battery.points} color={colors.energy} />
      </View>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  row: { gap: 2 },
  chart: { marginTop: spacing.sm },
});
