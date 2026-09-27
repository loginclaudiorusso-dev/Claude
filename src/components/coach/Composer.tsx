import { useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';

import { Icon, PressableScale } from '@/components/ui';
import { colors, radius, spacing, typography } from '@/theme';

type Props = {
  sending: boolean;
  disabled?: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
};

export function Composer({ sending, disabled, onSend, onStop }: Props) {
  const [text, setText] = useState('');
  const canSend = text.trim().length > 0 && !sending && !disabled;
  const submit = () => {
    if (!canSend) return;
    onSend(text);
    setText('');
  };
  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder="Frag deinen Coach…"
        placeholderTextColor={colors.labelTertiary}
        multiline
        editable={!disabled}
        accessibilityLabel="Nachricht an den Coach"
        onSubmitEditing={submit}
        submitBehavior="blurAndSubmit"
        returnKeyType="send"
      />
      {sending ? (
        <PressableScale
          onPress={onStop}
          style={[styles.button, styles.stop]}
          accessibilityLabel="Antwort stoppen"
          accessibilityRole="button"
        >
          <Icon name="stop.fill" size={14} color={colors.label} />
        </PressableScale>
      ) : (
        <PressableScale
          onPress={submit}
          disabled={!canSend}
          style={[
            styles.button,
            { backgroundColor: canSend ? colors.coach : colors.surfaceSecondary },
          ]}
          accessibilityLabel="Senden"
          accessibilityRole="button"
        >
          <Icon
            name="arrow.up"
            size={16}
            color={canSend ? '#fff' : colors.labelTertiary}
            weight="bold"
          />
        </PressableScale>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    padding: spacing.sm,
    paddingLeft: spacing.lg,
    borderRadius: radius.card,
    borderCurve: 'continuous',
    backgroundColor: colors.surfaceSolid,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  input: {
    ...typography.body,
    color: colors.label,
    flex: 1,
    maxHeight: 120,
    paddingVertical: spacing.sm,
  },
  button: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stop: { backgroundColor: colors.surfaceSecondary },
});
