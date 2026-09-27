import * as Haptics from 'expo-haptics';
import { useEffect, useState } from 'react';
import {
  Platform,
  Pressable,
  type StyleProp,
  StyleSheet,
  Text,
  View,
  type ViewStyle,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

import { colors, radius, springs, typography } from '@/theme';

type Props<T extends string | number> = {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  accessibilityLabel?: string;
  style?: StyleProp<ViewStyle>;
};

/** iOS-style segmented control with a sliding, spring-animated thumb. */
export function SegmentedControl<T extends string | number>({
  options,
  value,
  onChange,
  accessibilityLabel,
  style,
}: Props<T>) {
  const [width, setWidth] = useState(0);
  const index = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );
  const segment = width / options.length;
  const x = useSharedValue(index * segment);

  useEffect(() => {
    x.set(withSpring(index * segment, springs.snappy));
  }, [index, segment, x]);

  const thumb = useAnimatedStyle(() => ({ transform: [{ translateX: x.value }] }));

  return (
    <View
      style={[styles.track, style]}
      onLayout={(e) => setWidth(e.nativeEvent.layout.width - 4)}
      accessibilityRole="tablist"
      accessibilityLabel={accessibilityLabel}
    >
      {width > 0 && <Animated.View style={[styles.thumb, { width: segment }, thumb]} />}
      {options.map((o) => (
        <Pressable
          key={String(o.value)}
          style={styles.segment}
          accessibilityRole="tab"
          accessibilityState={{ selected: o.value === value }}
          onPress={() => {
            if (o.value === value) return;
            if (Platform.OS === 'ios') void Haptics.selectionAsync();
            onChange(o.value);
          }}
        >
          <Text style={[styles.label, o.value === value && styles.labelActive]}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    flexDirection: 'row',
    padding: 2,
    borderRadius: radius.sm,
    backgroundColor: 'rgba(118, 118, 128, 0.24)',
  },
  thumb: {
    position: 'absolute',
    top: 2,
    bottom: 2,
    left: 2,
    borderRadius: radius.sm - 2,
    backgroundColor: '#636366',
  },
  segment: { flex: 1, paddingVertical: 6, alignItems: 'center' },
  label: { ...typography.footnote, fontWeight: '500', color: colors.labelSecondary },
  labelActive: { color: colors.label, fontWeight: '600' },
});
