import { useWindowDimensions } from 'react-native';

import { TABLET_BREAKPOINT } from '@/theme';

export type LayoutClass = 'compact' | 'regular';

/**
 * Mirrors UIKit size classes: `regular` for iPad full-screen / large split view,
 * `compact` for iPhone and narrow iPad Split View / Slide Over.
 */
export function useResponsiveLayout() {
  const { width, height } = useWindowDimensions();
  const sizeClass: LayoutClass = width >= TABLET_BREAKPOINT ? 'regular' : 'compact';
  const columns = width >= 1100 ? 3 : sizeClass === 'regular' ? 2 : 1;
  return { width, height, sizeClass, isTablet: sizeClass === 'regular', columns };
}
