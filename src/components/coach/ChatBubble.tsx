import { StyleSheet, Text, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Icon } from '@/components/ui';
import type { CoachChatMessage } from '@/types/coach';
import { colors, palette, radius, spacing, typography } from '@/theme';

const TOOL_LABEL: Record<string, string> = {
  get_day_summary: 'Sieht sich einen Tag genauer an…',
  get_metric_series: 'Analysiert deinen Verlauf…',
  list_workouts: 'Geht deine Workouts durch…',
  compare_after_training: 'Vergleicht Trainings- und Ruhetage…',
};

type Props = { message: CoachChatMessage; activeTool?: string | null };

export function ChatBubble({ message, activeTool }: Props) {
  const isUser = message.role === 'user';
  const streaming = message.status === 'streaming';
  const isError = message.status === 'error';
  return (
    <Animated.View
      entering={FadeInDown.springify().damping(18)}
      style={[styles.row, isUser ? styles.right : styles.left]}
    >
      <View
        style={[styles.bubble, isUser ? styles.user : styles.assistant, isError && styles.error]}
      >
        {message.text ? (
          <Text style={[styles.text, isUser && styles.userText]} selectable>
            {message.text}
          </Text>
        ) : null}
        {streaming && (activeTool || !message.text) ? (
          <View style={styles.status}>
            <Icon name="sparkles" size={13} color={colors.coach} />
            <Text style={styles.statusText}>
              {activeTool ? (TOOL_LABEL[activeTool] ?? 'Analysiert…') : 'Denkt nach…'}
            </Text>
          </View>
        ) : null}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', marginVertical: spacing.xs },
  left: { justifyContent: 'flex-start' },
  right: { justifyContent: 'flex-end' },
  bubble: {
    maxWidth: '86%',
    paddingHorizontal: spacing.md + 2,
    paddingVertical: spacing.sm + 2,
    borderRadius: radius.card - 4,
    borderCurve: 'continuous',
    gap: spacing.xs,
  },
  user: { backgroundColor: colors.coach, borderBottomRightRadius: 6 },
  assistant: {
    backgroundColor: colors.surfaceSolid,
    borderBottomLeftRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  error: { borderColor: palette.red },
  text: { ...typography.body, color: colors.label },
  userText: { color: '#fff' },
  status: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  statusText: { ...typography.footnote, color: colors.labelSecondary },
});
