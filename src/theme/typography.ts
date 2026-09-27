import { Platform, type TextStyle } from 'react-native';

/**
 * iOS Dynamic Type text styles (default "Large" size). On iOS the system font
 * resolves to SF Pro / SF Pro Rounded automatically.
 */
const family = Platform.select({ ios: 'System', default: undefined });
const rounded = Platform.select({
  ios: 'ui-rounded',
  web: 'ui-rounded, system-ui',
  default: undefined,
});

const style = (
  fontSize: number,
  lineHeight: number,
  fontWeight: TextStyle['fontWeight'],
): TextStyle => ({
  fontFamily: family,
  fontSize,
  lineHeight,
  fontWeight,
});

export const typography = {
  largeTitle: style(34, 41, '700'),
  title1: style(28, 34, '700'),
  title2: style(22, 28, '700'),
  title3: style(20, 25, '600'),
  headline: style(17, 22, '600'),
  body: style(17, 22, '400'),
  callout: style(16, 21, '400'),
  subheadline: style(15, 20, '400'),
  footnote: style(13, 18, '400'),
  caption1: style(12, 16, '400'),
  caption2: style(11, 13, '400'),
  /** Big numeric read-outs (scores, rings) – SF Pro Rounded, tabular digits. */
  metric: {
    fontFamily: rounded,
    fontSize: 44,
    lineHeight: 50,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  } satisfies TextStyle,
} as const;
