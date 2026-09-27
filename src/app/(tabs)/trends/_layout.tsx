import { Stack } from 'expo-router';

import { largeTitleStackOptions } from '@/components/navigation/stackOptions';

export default function TrendsLayout() {
  return (
    <Stack screenOptions={largeTitleStackOptions}>
      <Stack.Screen name="index" options={{ title: 'Trends' }} />
    </Stack>
  );
}
