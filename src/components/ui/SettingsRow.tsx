import type { SFSymbol } from 'expo-symbols';
import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/theme';

import { Icon } from './Icon';
import { PressableScale } from './PressableScale';

type RowProps = {
  symbol: SFSymbol;
  tint: string;
  title: string;
  subtitle?: string;
  accessory?: ReactNode;
  onPress?: () => void;
  destructive?: boolean;
  disabled?: boolean;
};

/** iOS grouped-list row with a tinted icon tile. */
export function SettingsRow({
  symbol,
  tint,
  title,
  subtitle,
  accessory,
  onPress,
  destructive,
  disabled,
}: RowProps) {
  const content = (
    <View style={[styles.row, disabled && styles.disabled]}>
      <View style={[styles.iconTile, { backgroundColor: tint }]}>
        <Icon name={symbol} size={15} color="#fff" />
      </View>
      <View style={styles.text}>
        <Text style={[styles.title, destructive && styles.destructive]}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      {accessory}
      {onPress && !accessory ? (
        <Icon name="chevron.right" size={13} color={colors.labelTertiary} />
      ) : null}
    </View>
  );
  return onPress ? (
    <PressableScale
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={title}
    >
      {content}
    </PressableScale>
  ) : (
    content
  );
}

/** Grouped section container with title and footer text. */
export function SettingsSection({
  title,
  footer,
  children,
}: {
  title: string;
  footer?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title.toUpperCase()}</Text>
      <View style={styles.group}>{children}</View>
      {footer ? <Text style={styles.footer}>{footer}</Text> : null}
    </View>
  );
}

export function Separator() {
  return <View style={styles.separator} />;
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    minHeight: 52,
  },
  disabled: { opacity: 0.45 },
  iconTile: {
    width: 30,
    height: 30,
    borderRadius: 8,
    borderCurve: 'continuous',
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: { flex: 1, gap: 2 },
  title: { ...typography.body, color: colors.label },
  destructive: { color: '#FF453A' },
  subtitle: { ...typography.footnote, color: colors.labelSecondary },
  section: { gap: spacing.sm },
  sectionTitle: { ...typography.footnote, color: colors.labelSecondary, marginLeft: spacing.lg },
  group: {
    borderRadius: radius.md + 2,
    borderCurve: 'continuous',
    backgroundColor: colors.surfaceSolid,
    overflow: 'hidden',
  },
  footer: { ...typography.footnote, color: colors.labelTertiary, marginHorizontal: spacing.lg },
  separator: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.separator,
    marginLeft: 58,
  },
});
