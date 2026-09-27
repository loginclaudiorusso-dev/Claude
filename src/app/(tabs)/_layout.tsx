import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { colors } from '@/theme';

/**
 * Native UITabBarController tab bar: Liquid Glass on iOS 26, and on iPad it
 * adapts to the sidebar layout (`sidebarAdaptable`) for a split-view feel.
 */
export default function TabsLayout() {
  return (
    <NativeTabs tintColor={colors.tint} minimizeBehavior="onScrollDown" sidebarAdaptable>
      <NativeTabs.Trigger name="dashboard">
        <NativeTabs.Trigger.Icon
          sf={{ default: 'heart.text.square', selected: 'heart.text.square.fill' }}
          md="favorite"
        />
        <NativeTabs.Trigger.Label>Heute</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="trends">
        <NativeTabs.Trigger.Icon sf="chart.xyaxis.line" md="insights" />
        <NativeTabs.Trigger.Label>Trends</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="coach">
        <NativeTabs.Trigger.Icon
          sf={{ default: 'sparkles', selected: 'sparkles' }}
          md="auto_awesome"
        />
        <NativeTabs.Trigger.Label>Coach</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="settings">
        <NativeTabs.Trigger.Icon
          sf={{ default: 'gearshape', selected: 'gearshape.fill' }}
          md="settings"
        />
        <NativeTabs.Trigger.Label>Einstellungen</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
