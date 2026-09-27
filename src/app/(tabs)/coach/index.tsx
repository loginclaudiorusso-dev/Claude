import { Stack, router } from 'expo-router';
import { useRef } from 'react';
import { FlatList, Platform, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChatBubble, Composer } from '@/components/coach';
import { EmptyState, Icon, PressableScale } from '@/components/ui';
import { useCoachContext } from '@/hooks/useCoachContext';
import { useKeyboardHeight } from '@/hooks/useKeyboardHeight';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useCoachStore } from '@/store/coachStore';
import { useHealthStore } from '@/store/healthStore';
import { WEB_TOP_INSET, colors, radius, spacing, typography } from '@/theme';

const SUGGESTIONS = [
  'Wie hat sich mein Schlaf nach dem Training verändert?',
  'Sollte ich heute hart trainieren?',
  'Warum ist meine HRV diese Woche gesunken?',
  'Wie kann ich meine Schlafschuld abbauen?',
];
/** Height of the native tab bar (without the home-indicator inset). */
const TAB_BAR_HEIGHT = 49;

export default function CoachScreen() {
  const { hasKey, messages, sending, activeTool, send, cancel, resetChat } = useCoachStore();
  const hasData = useHealthStore((s) => s.summaries.length > 0);
  const ctx = useCoachContext();
  const insets = useSafeAreaInsets();
  const keyboard = useKeyboardHeight();
  const { isTablet } = useResponsiveLayout();
  const list = useRef<FlatList>(null);

  const headerRight = () =>
    messages.length > 0 ? (
      <PressableScale onPress={resetChat} accessibilityLabel="Neues Gespräch" hitSlop={10}>
        <Icon name="square.and.pencil" size={20} color={colors.coach} />
      </PressableScale>
    ) : null;

  if (hasKey === false) {
    return (
      <EmptyState
        symbol="key.fill"
        tint={colors.coach}
        title="Claude verbinden"
        message="Für den Coach brauchst du einen eigenen Anthropic API-Key. Er wird nur im Schlüsselbund dieses Geräts gespeichert."
        actionLabel="API-Key hinterlegen"
        onAction={() => router.navigate('/settings')}
      />
    );
  }

  const bottom = keyboard > 0 ? keyboard + spacing.sm : insets.bottom + TAB_BAR_HEIGHT + spacing.sm;
  const submit = (text: string) => void send(text, ctx);

  return (
    <View style={styles.container}>
      <Stack.Screen options={{ headerRight }} />
      <FlatList
        ref={list}
        data={messages}
        keyExtractor={(m) => m.id}
        contentInsetAdjustmentBehavior="automatic"
        keyboardDismissMode="interactive"
        contentContainerStyle={[styles.list, isTablet && styles.listTablet]}
        onContentSizeChange={() => list.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <ChatBubble message={item} activeTool={item.status === 'streaming' ? activeTool : null} />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Icon name="bubble.left.and.text.bubble.right.fill" size={36} color={colors.coach} />
            <Text style={styles.emptyTitle}>Dein AI Health & Performance Coach</Text>
            <Text style={styles.emptyText}>
              Claude kennt deine heutigen Werte und kann bei Bedarf in deinen Verlauf schauen.
            </Text>
            <View style={styles.suggestions}>
              {SUGGESTIONS.map((s) => (
                <PressableScale
                  key={s}
                  onPress={() => submit(s)}
                  disabled={!hasData}
                  style={styles.chip}
                  accessibilityRole="button"
                >
                  <Text style={styles.chipText}>{s}</Text>
                </PressableScale>
              ))}
            </View>
          </View>
        }
      />
      <View style={[styles.composer, isTablet && styles.listTablet, { paddingBottom: bottom }]}>
        <Composer sending={sending} disabled={!hasData} onSend={submit} onStop={cancel} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  list: {
    paddingHorizontal: spacing.lg,
    paddingTop: Platform.OS === 'web' ? WEB_TOP_INSET : spacing.sm,
    paddingBottom: spacing.lg,
    flexGrow: 1,
  },
  listTablet: { width: '100%', maxWidth: 760, alignSelf: 'center' },
  composer: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
    paddingVertical: spacing.xxxl,
  },
  emptyTitle: { ...typography.title3, color: colors.label, textAlign: 'center' },
  emptyText: {
    ...typography.subheadline,
    color: colors.labelSecondary,
    textAlign: 'center',
    maxWidth: 340,
  },
  suggestions: { gap: spacing.sm, marginTop: spacing.md, alignSelf: 'stretch' },
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    borderCurve: 'continuous',
    backgroundColor: colors.surfaceSolid,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  chipText: { ...typography.subheadline, color: colors.label },
});
