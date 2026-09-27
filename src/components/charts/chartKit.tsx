import * as Haptics from 'expo-haptics';
import { useCallback, useRef, useState } from 'react';
import {
  type LayoutChangeEvent,
  Platform,
  StyleSheet,
  Text,
  View,
  type GestureResponderEvent,
} from 'react-native';

import { chartColors, colors, radius, spacing, typography } from '@/theme';

/** Linear scale factory. */
export function scaleLinear(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** "Nice" padded domain for a set of values. */
export function paddedDomain(values: number[], padRatio = 0.12, floor?: number): [number, number] {
  if (values.length === 0) return [0, 1];
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= Math.abs(min) * 0.1 || 1;
    max += Math.abs(max) * 0.1 || 1;
  }
  const pad = (max - min) * padRatio;
  return [floor !== undefined ? Math.max(floor, min - pad) : min - pad, max + pad];
}

/** SVG path through points, breaking the line at null values. */
export function linePath(points: ({ x: number; y: number } | null)[]): string {
  let d = '';
  let pen = false;
  for (const p of points) {
    if (!p) {
      pen = false;
      continue;
    }
    d += `${pen ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    pen = true;
  }
  return d;
}

/** Bar with 4px rounded data-end and a square base anchored at `baseY`. */
export function roundedTopBar(x: number, y: number, w: number, baseY: number, r = 4): string {
  const h = baseY - y;
  if (h <= 0 || w <= 0) return '';
  const rr = Math.min(r, w / 2, h);
  return `M${x},${baseY}V${y + rr}Q${x},${y} ${x + rr},${y}H${x + w - rr}Q${x + w},${y} ${x + w},${y + rr}V${baseY}Z`;
}

export function useLayoutWidth(): [number, (e: LayoutChangeEvent) => void] {
  const [width, setWidth] = useState(0);
  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const w = Math.round(e.nativeEvent.layout.width);
    setWidth((prev) => (prev === w ? prev : w));
  }, []);
  return [width, onLayout];
}

/**
 * Touch scrubbing (the mobile equivalent of hover): drag across the plot to
 * select the mark nearest to the finger. `positions` are the marks' x-coords.
 * Releases the gesture to a parent ScrollView when it asks, so vertical
 * scrolling still works.
 */
export function useScrub(positions: readonly number[]) {
  const [index, setIndex] = useState<number | null>(null);
  const last = useRef<number | null>(null);

  const pick = useCallback(
    (e: GestureResponderEvent) => {
      if (positions.length === 0) return;
      const x = e.nativeEvent.locationX;
      let best = 0;
      for (let i = 1; i < positions.length; i++) {
        if (Math.abs(positions[i]! - x) < Math.abs(positions[best]! - x)) best = i;
      }
      if (best !== last.current) {
        last.current = best;
        if (Platform.OS === 'ios') void Haptics.selectionAsync();
        setIndex(best);
      }
    },
    [positions],
  );

  const end = useCallback(() => {
    last.current = null;
    setIndex(null);
  }, []);

  const handlers = {
    onStartShouldSetResponder: () => true,
    onMoveShouldSetResponder: () => true,
    onResponderGrant: pick,
    onResponderMove: pick,
    onResponderRelease: end,
    onResponderTerminate: end,
    onResponderTerminationRequest: () => true,
  };
  return { index, handlers };
}

type TooltipProps = {
  x: number;
  width: number;
  title: string;
  lines: { label?: string; value: string; color?: string }[];
};

/** Floating tooltip above the plot, clamped inside the chart width. */
export function ChartTooltip({ x, width, title, lines }: TooltipProps) {
  const [w, setW] = useState(120);
  const left = Math.max(0, Math.min(width - w, x - w / 2));
  return (
    <View
      pointerEvents="none"
      style={[styles.tooltip, { left }]}
      onLayout={(e) => setW(e.nativeEvent.layout.width)}
      accessibilityLiveRegion="polite"
    >
      <Text style={styles.tooltipTitle}>{title}</Text>
      {lines.map((l, i) => (
        <View key={i} style={styles.tooltipRow}>
          {l.color ? <View style={[styles.swatch, { backgroundColor: l.color }]} /> : null}
          {l.label ? <Text style={styles.tooltipLabel}>{l.label}</Text> : null}
          <Text style={styles.tooltipValue}>{l.value}</Text>
        </View>
      ))}
    </View>
  );
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <View style={styles.legend} accessibilityRole="summary">
      {items.map((it) => (
        <View key={it.label} style={styles.legendItem}>
          <View style={[styles.swatch, { backgroundColor: it.color }]} />
          <Text style={styles.legendLabel}>{it.label}</Text>
        </View>
      ))}
    </View>
  );
}

/** Prevents text selection while scrubbing with a mouse on web. */
export const scrubSurfaceStyle = Platform.OS === 'web' ? ({ userSelect: 'none' } as object) : null;

export const axisTextProps = {
  fill: chartColors.axisText,
  fontFamily: Platform.select({
    web: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    default: undefined,
  }),
  fontSize: 11,
  fontWeight: '500' as const,
};

const styles = StyleSheet.create({
  tooltip: {
    position: 'absolute',
    top: 0,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 2,
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    zIndex: 10,
    minWidth: 90,
  },
  tooltipTitle: { ...typography.caption1, color: colors.labelSecondary, marginBottom: 2 },
  tooltipRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  tooltipLabel: { ...typography.caption1, color: colors.labelSecondary, flex: 1 },
  tooltipValue: {
    ...typography.footnote,
    color: colors.label,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  swatch: { width: 8, height: 8, borderRadius: 2 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendLabel: { ...typography.caption1, color: colors.labelSecondary },
});
