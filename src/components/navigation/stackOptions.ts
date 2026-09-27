import type { Stack } from 'expo-router';
import type { ComponentProps } from 'react';

import { colors } from '@/theme';

type StackScreenOptions = Exclude<
  ComponentProps<typeof Stack>['screenOptions'],
  ((...args: never[]) => unknown) | undefined
>;

/** iOS large-title header with a frosted-glass blur once content scrolls under it. */
export const largeTitleStackOptions: StackScreenOptions = {
  headerLargeTitle: true,
  headerTransparent: true,
  headerBlurEffect: 'systemChromeMaterialDark',
  headerLargeTitleShadowVisible: false,
  headerShadowVisible: false,
  headerTintColor: colors.tint,
  headerTitleStyle: { color: colors.label },
  headerLargeTitleStyle: { color: colors.label },
  contentStyle: { backgroundColor: colors.background },
};
