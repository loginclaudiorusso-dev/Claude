import { BlurView } from 'expo-blur';
import type { PropsWithChildren } from 'react';
import { Platform, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radius, spacing } from '@/theme';

type Props = PropsWithChildren<{
  style?: StyleProp<ViewStyle>;
  /** Blur intensity 0–100; ignored on Android where a translucent fill is used. */
  intensity?: number;
  padded?: boolean;
}>;

/** Frosted-glass card container (iOS `systemMaterialDark` look). */
export function GlassCard({ children, style, intensity = 40, padded = true }: Props) {
  return (
    <View style={[styles.container, style]}>
      {Platform.OS === 'ios' ? (
        <BlurView tint="systemMaterialDark" intensity={intensity} style={StyleSheet.absoluteFill} />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.fallbackFill]} />
      )}
      <View style={padded && styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: radius.card,
    borderCurve: 'continuous',
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  fallbackFill: {
    backgroundColor: colors.surfaceSolid,
  },
  content: {
    padding: spacing.lg,
  },
});
