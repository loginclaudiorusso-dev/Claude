import { router } from 'expo-router';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { CardHeader, GlassCard, Icon, PressableScale } from '@/components/ui';
import { useCoachStore } from '@/store/coachStore';
import type { CoachFocus } from '@/types/coach';
import { colors, palette, radius, spacing, typography } from '@/theme';

const FOCUS: Record<CoachFocus, { label: string; color: string }> = {
  recover: { label: 'Regeneration', color: palette.red },
  maintain: { label: 'Halten', color: palette.yellow },
  build: { label: 'Aufbauen', color: palette.green },
  peak: { label: 'Vollgas', color: palette.mint },
};

type Props = { onRefresh: () => void };

/** „Dein Coach sagt…“ – Claude's daily briefing with loading, error and no-key states. */
export function BriefingCard({ onRefresh }: Props) {
  const { hasKey, briefing, briefingStatus, briefingError } = useCoachStore();

  const refresh = (
    <PressableScale
      onPress={onRefresh}
      disabled={briefingStatus === 'loading'}
      accessibilityLabel="Briefing neu erstellen"
      hitSlop={10}
    >
      <Icon name="arrow.clockwise" size={15} color={colors.labelSecondary} />
    </PressableScale>
  );

  return (
    <GlassCard>
      <CardHeader
        symbol="sparkles"
        title="Dein Coach sagt…"
        tint={colors.coach}
        accessory={hasKey ? refresh : undefined}
      />
      {hasKey === false ? (
        <View style={styles.block}>
          <Text style={styles.body}>
            Hinterlege deinen Claude API-Key, um tägliche, persönliche Empfehlungen zu erhalten.
          </Text>
          <PressableScale
            onPress={() => router.navigate('/settings')}
            style={styles.link}
            accessibilityRole="button"
          >
            <Text style={styles.linkText}>API-Key hinzufügen</Text>
            <Icon name="chevron.right" size={12} color={colors.coach} />
          </PressableScale>
        </View>
      ) : briefingStatus === 'loading' && !briefing ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.coach} />
          <Text style={styles.muted}>Claude analysiert deine Daten…</Text>
        </View>
      ) : briefingStatus === 'error' && briefingError ? (
        <View style={styles.block}>
          <Text style={styles.body}>{briefingError.message}</Text>
          <PressableScale onPress={onRefresh} style={styles.link} accessibilityRole="button">
            <Text style={styles.linkText}>Erneut versuchen</Text>
          </PressableScale>
        </View>
      ) : briefing ? (
        <Animated.View entering={FadeIn.duration(350)} style={styles.block}>
          <View style={[styles.focus, { backgroundColor: `${FOCUS[briefing.focus].color}26` }]}>
            <View style={[styles.dot, { backgroundColor: FOCUS[briefing.focus].color }]} />
            <Text style={styles.focusText}>Fokus: {FOCUS[briefing.focus].label}</Text>
          </View>
          <Text style={styles.headline}>{briefing.headline}</Text>
          <Text style={styles.body}>{briefing.summary}</Text>
          <View style={styles.list}>
            {briefing.recommendations.map((r, i) => (
              <View key={i} style={styles.item}>
                <Icon name="checkmark.circle.fill" size={16} color={colors.coach} />
                <Text style={styles.itemText}>{r}</Text>
              </View>
            ))}
          </View>
          {briefingStatus === 'loading' ? (
            <Text style={styles.muted}>Wird aktualisiert…</Text>
          ) : null}
        </Animated.View>
      ) : (
        <Text style={styles.muted}>Noch kein Briefing für heute.</Text>
      )}
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  block: { gap: spacing.sm },
  loading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  headline: { ...typography.title3, color: colors.label },
  body: { ...typography.callout, color: colors.labelSecondary },
  muted: { ...typography.footnote, color: colors.labelTertiary },
  list: { gap: spacing.sm, marginTop: spacing.xs },
  item: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  itemText: { ...typography.subheadline, color: colors.label, flex: 1 },
  focus: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
    borderRadius: radius.pill,
  },
  dot: { width: 7, height: 7, borderRadius: 4 },
  focusText: { ...typography.caption1, fontWeight: '600', color: colors.label },
  link: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    paddingVertical: 4,
  },
  linkText: { ...typography.subheadline, fontWeight: '600', color: colors.coach },
});
