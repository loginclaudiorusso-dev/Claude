import type { PropsWithChildren } from 'react';
import { Platform, ScrollView, StyleSheet, View, type ScrollViewProps } from 'react-native';

import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { WEB_TOP_INSET, colors, spacing } from '@/theme';

type Props = PropsWithChildren<Omit<ScrollViewProps, 'children'>>;

/**
 * Scrollable screen body that cooperates with the transparent large-title
 * header and native tab bar, and caps content width on iPad for readability.
 */
export function Screen({ children, contentContainerStyle, ...rest }: Props) {
  const { isTablet } = useResponsiveLayout();
  return (
    <ScrollView
      style={styles.scroll}
      contentInsetAdjustmentBehavior="automatic"
      contentContainerStyle={[
        styles.content,
        isTablet && styles.contentTablet,
        contentContainerStyle,
      ]}
      {...rest}
    >
      <View style={[styles.inner, isTablet && styles.innerTablet]}>{children}</View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: colors.background },
  content: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxxl,
    paddingTop: Platform.OS === 'web' ? WEB_TOP_INSET : spacing.sm,
  },
  contentTablet: { paddingHorizontal: spacing.xxxl },
  inner: { gap: spacing.lg },
  innerTablet: { width: '100%', maxWidth: 1200, alignSelf: 'center', gap: spacing.xl },
});
