import { PlaceholderCard, Screen } from '@/components/ui';
import { colors } from '@/theme';

export default function CoachScreen() {
  return (
    <Screen keyboardDismissMode="interactive">
      <PlaceholderCard
        symbol="bubble.left.and.text.bubble.right.fill"
        title="AI Health & Performance Coach"
        subtitle="Frag z. B.: „Wie hat sich mein Schlaf nach dem Training verändert?“"
        tint={colors.coach}
      />
    </Screen>
  );
}
