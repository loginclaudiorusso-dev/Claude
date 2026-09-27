import { View } from 'react-native';
import Svg, { Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import type { TrendPoint } from '@/types/health';
import { chartColors } from '@/theme';
import { formatShortDate, formatWeekday } from '@/utils/format';

import {
  ChartTooltip,
  axisTextProps,
  roundedTopBar,
  scaleLinear,
  useLayoutWidth,
  useScrub,
  scrubSurfaceStyle,
} from './chartKit';

type Props = {
  points: TrendPoint[];
  color: string;
  maxValue: number;
  height?: number;
  /** Shaded target band (name it in the card caption, not inside the plot). */
  band?: { min: number; max: number } | null;
  formatValue: (v: number) => string;
  accessibilityLabel: string;
};

const PAD = { top: 44, right: 4, bottom: 22, left: 4 };
const GAP = 2;

/** Daily bars with rounded 4px data-ends, 2px gaps and a scrub tooltip. */
export function DailyBarChart({
  points,
  color,
  maxValue,
  height = 180,
  band,
  formatValue,
  accessibilityLabel,
}: Props) {
  const [width, onLayout] = useLayoutWidth();
  const n = Math.max(1, points.length);
  const slot = (width - PAD.left - PAD.right) / n;
  const barW = Math.max(2, slot - GAP);
  const baseY = height - PAD.bottom;
  const y = scaleLinear([0, maxValue], [baseY, PAD.top]);
  const cx = (i: number) => PAD.left + slot * i + slot / 2;
  const { index, handlers } = useScrub(points.map((_, i) => cx(i)));
  const short = points.length <= 10;
  const ticks = short ? points.map((_, i) => i) : [0, Math.floor((n - 1) / 2), n - 1];
  const active = index !== null ? points[index] : undefined;

  return (
    <View
      onLayout={onLayout}
      style={[{ height }, scrubSurfaceStyle]}
      accessible
      accessibilityLabel={accessibilityLabel}
      {...handlers}
    >
      {width > 0 && (
        <Svg width={width} height={height}>
          {band && (
            <Rect
              x={PAD.left}
              width={width - PAD.left - PAD.right}
              y={y(band.max)}
              height={Math.max(1, y(band.min) - y(band.max))}
              fill={color}
              opacity={0.12}
            />
          )}
          <Line
            x1={PAD.left}
            x2={width - PAD.right}
            y1={baseY}
            y2={baseY}
            stroke={chartColors.grid}
            strokeWidth={1}
          />
          {points.map((p, i) =>
            p.value === null || p.value <= 0 ? null : (
              <Path
                key={p.date}
                d={roundedTopBar(
                  PAD.left + slot * i + GAP / 2,
                  y(Math.min(p.value, maxValue)),
                  barW,
                  baseY,
                )}
                fill={color}
                opacity={index === null || index === i ? 1 : 0.45}
              />
            ),
          )}
          {ticks.map((i) => (
            <SvgText
              key={i}
              {...axisTextProps}
              x={short ? cx(i) : i === 0 ? PAD.left : i === n - 1 ? width - PAD.right : cx(i)}
              y={height - 6}
              textAnchor={short ? 'middle' : i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}
            >
              {short ? formatWeekday(points[i]!.date) : formatShortDate(points[i]!.date)}
            </SvgText>
          ))}
        </Svg>
      )}
      {active && index !== null && (
        <ChartTooltip
          x={cx(index)}
          width={width}
          title={`${formatWeekday(active.date)}, ${formatShortDate(active.date)}`}
          lines={[{ value: active.value === null ? 'keine Daten' : formatValue(active.value) }]}
        />
      )}
    </View>
  );
}
