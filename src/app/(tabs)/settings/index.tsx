import { PlaceholderCard, Screen } from '@/components/ui';
import { colors } from '@/theme';

export default function SettingsScreen() {
  return (
    <Screen>
      <PlaceholderCard
        symbol="key.fill"
        title="Claude API-Key"
        subtitle="Sicher im iOS-Schlüsselbund gespeichert"
        tint={colors.coach}
      />
      <PlaceholderCard
        symbol="heart.text.square.fill"
        title="Apple Health"
        subtitle="Berechtigungen verwalten"
        tint={colors.heart}
      />
      <PlaceholderCard
        symbol="square.and.arrow.down.fill"
        title="Daten importieren"
        subtitle="JSON/CSV (z. B. Health Auto Export)"
        tint={colors.sleep}
      />
    </Screen>
  );
}
