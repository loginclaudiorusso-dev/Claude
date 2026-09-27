import { PlaceholderCard, Screen } from '@/components/ui';
import { colors } from '@/theme';

export default function DashboardScreen() {
  return (
    <Screen>
      <PlaceholderCard
        symbol="heart.circle.fill"
        title="Erholung"
        subtitle="Readiness-Score 0–100 % (HRV, Ruhepuls, Schlaf)"
        tint={colors.recovery}
      />
      <PlaceholderCard
        symbol="flame.fill"
        title="Belastung"
        subtitle="Strain-Score 0–21 (HF-Zonen, aktive Kalorien)"
        tint={colors.strain}
      />
      <PlaceholderCard
        symbol="bed.double.fill"
        title="Schlaf"
        subtitle="Phasen, Schlafbedarf & Defizit"
        tint={colors.sleep}
      />
      <PlaceholderCard
        symbol="bolt.heart.fill"
        title="Body Battery"
        subtitle="Energieverlauf über den Tag"
        tint={colors.energy}
      />
      <PlaceholderCard
        symbol="sparkles"
        title="Dein Coach sagt…"
        subtitle="Tägliches Briefing von Claude"
        tint={colors.coach}
      />
    </Screen>
  );
}
