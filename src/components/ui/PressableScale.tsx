import * as Haptics from 'expo-haptics';
import type { PropsWithChildren } from 'react';
import {
  Platform,
  Pressable,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

import { springs } from '@/theme';

type Props = PropsWithChildren<
  Omit<PressableProps, 'style' | 'children'> & { style?: StyleProp<ViewStyle>; haptic?: boolean }
>;

/** Pressable that springs down to 97 % on touch, with light haptic feedback. */
export function PressableScale({
  children,
  style,
  haptic = true,
  onPressIn,
  onPressOut,
  onPress,
  ...rest
}: Props) {
  const scale = useSharedValue(1);
  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <Pressable
      {...rest}
      onPressIn={(e) => {
        scale.set(withSpring(0.97, springs.snappy));
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.set(withSpring(1, springs.bouncy));
        onPressOut?.(e);
      }}
      onPress={(e) => {
        if (haptic && Platform.OS === 'ios') void Haptics.selectionAsync();
        onPress?.(e);
      }}
    >
      <Animated.View style={[style, animated]}>{children}</Animated.View>
    </Pressable>
  );
}
