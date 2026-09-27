export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const radius = {
  sm: 10,
  md: 14,
  card: 22,
  sheet: 28,
  pill: 999,
} as const;

/** Width at which layouts switch to the iPad multi-column dashboard. */
export const TABLET_BREAKPOINT = 768;

/** Spring presets for react-native-reanimated (`withSpring`). */
export const springs = {
  gentle: { damping: 18, stiffness: 140, mass: 1 },
  snappy: { damping: 20, stiffness: 260, mass: 0.8 },
  bouncy: { damping: 11, stiffness: 180, mass: 0.9 },
} as const;

/**
 * On web the native tab bar renders as a floating bar at the top and the
 * transparent large-title header does not inset content, so screens add this.
 */
export const WEB_TOP_INSET = 96;
