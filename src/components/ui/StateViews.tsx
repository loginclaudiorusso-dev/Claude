import type { SFSymbol } from 'expo-symbols';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/theme';

import { Icon } from './Icon';
import { PressableScale } from './PressableScale';

export function LoadingView({ label = 'Lade Gesundheitsdaten…' }: { label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.labelSecondary} />
      <Text style={styles.caption}>{label}</Text>
    </View>
  );
}

type EmptyProps = {
  symbol: SFSymbol;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  tint?: string;
};

export function EmptyState({
  symbol,
  title,
  message,
  actionLabel,
  onAction,
  tint = colors.tint,
}: EmptyProps) {
  return (
    <View style={styles.center}>
      <Icon name={symbol} size={40} color={tint} />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
      {actionLabel && onAction ? (
        <PressableScale
          onPress={onAction}
          style={[styles.button, { backgroundColor: tint }]}
          accessibilityRole="button"
        >
          <Text style={styles.buttonText}>{actionLabel}</Text>
        </PressableScale>
      ) : null}
    </View>
  );
}

export function PrimaryButton({
  label,
  onPress,
  tint = colors.tint,
  disabled,
}: {
  label: string;
  onPress: () => void;
  tint?: string;
  disabled?: boolean;
}) {
  return (
    <PressableScale
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      style={[styles.button, { backgroundColor: tint, opacity: disabled ? 0.4 : 1 }]}
    >
      <Text style={styles.buttonText}>{label}</Text>
    </PressableScale>
  );
}

const styles = StyleSheet.create({
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xxxl,
    gap: spacing.md,
  },
  caption: { ...typography.footnote, color: colors.labelSecondary },
  title: { ...typography.title3, color: colors.label, textAlign: 'center' },
  message: {
    ...typography.subheadline,
    color: colors.labelSecondary,
    textAlign: 'center',
    maxWidth: 360,
  },
  button: {
    marginTop: spacing.sm,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    borderCurve: 'continuous',
    alignItems: 'center',
  },
  buttonText: { ...typography.headline, color: '#000' },
});
