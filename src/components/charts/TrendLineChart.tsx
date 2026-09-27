import { View } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText } from 'react-native-svg';

import type { TrendPoint } from '@/types/health';
import { formatShortDate, formatWeekday } from '@/utils/format';
import { chartColors } from '@/theme';

import {
  ChartTooltip,
  axisTextProps,
  linePath,
  paddedDomain,
  scaleLinear,
  useLayoutWidth,
  useScrub,
  scrubSurfaceStyle,
} from './chartKit';

type Props = {
  points: TrendPoint[];
  color: string;
  height?: number;
  /** Dashed reference line, e.g. the period average. */
  reference?: { value: number; label: string } | null;
  formatValue: (v: number) => string;
  /** Accessible summary, e.g. "HRV, 30 Tage, steigend". */
  accessibilityLabel: string;
};

const PAD = { top: 44, right: 12, bottom: 22, left: 8 };

/** Single-series trend line (2px) with scrub crosshair, reference line and end marker. */
export function TrendLineChart({
  points,
  color,
  height = 190,
  reference,
  formatValue,
  accessibilityLabel,
}: Props) {
  const [width, onLayout] = useLayoutWidth();
  const x0 = PAD.left;
  const x1 = Math.max(x0 + 1, width - PAD.right);
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);
  const domain = paddedDomain(reference ? [...values, reference.value] : values);
  const y = scaleLinear(domain, [height - PAD.bottom, PAD.top]);
  const x = scaleLinear([0, Math.max(1, points.length - 1)], [x0, x1]);
  const coords = points.map((p, i) => (p.value === null ? null : { x: x(i), y: y(p.value) }));
  const { index, handlers } = useScrub(points.map((_, i) => x(i)));
  const lastIdx = coords.reduce<number>((acc, c, i) => (c ? i : acc), -1);
  const short = points.length <= 10;
  const labelFor = (i: number) =>
    short ? formatWeekday(points[i]!.date) : formatShortDate(points[i]!.date);
  const xTicks = short
    ? points.map((_, i) => i)
    : [0, Math.floor((points.length - 1) / 2), points.length - 1];
  const gridYs = [0.25, 0.5, 0.75].map((f) => PAD.top + (height - PAD.top - PAD.bottom) * f);
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
          {gridYs.map((gy) => (
            <Line
              key={gy}
              x1={x0}
              x2={x1}
              y1={gy}
              y2={gy}
              stroke={chartColors.grid}
              strokeWidth={1}
            />
          ))}
          {reference && (
            <>
              <Line
                x1={x0}
                x2={x1}
                y1={y(reference.value)}
                y2={y(reference.value)}
                stroke={chartColors.baseline}
                strokeWidth={1}
                strokeDasharray="4 4"
              />
              <SvgText {...axisTextProps} x={x1} y={y(reference.value) - 5} textAnchor="end">
                {reference.label}
              </SvgText>
            </>
          )}
          <Path
            d={linePath(coords)}
            stroke={color}
            strokeWidth={2}
            fill="none"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {index !== null && coords[index] && (
            <Line
              x1={coords[index]!.x}
              x2={coords[index]!.x}
              y1={PAD.top - 6}
              y2={height - PAD.bottom}
              stroke={chartColors.crosshair}
              strokeWidth={1}
            />
          )}
          {(index !== null ? [index] : lastIdx >= 0 ? [lastIdx] : []).map((i) =>
            coords[i] ? (
              <Circle
                key={i}
                cx={coords[i]!.x}
                cy={coords[i]!.y}
                r={5}
                fill={color}
                stroke={chartColors.markerRing}
                strokeWidth={2}
              />
            ) : null,
          )}
          {xTicks.map((i) => (
            <SvgText
              key={i}
              {...axisTextProps}
              x={x(i)}
              y={height - 6}
              textAnchor={
                i === 0 && !short ? 'start' : i === points.length - 1 && !short ? 'end' : 'middle'
              }
            >
              {labelFor(i)}
            </SvgText>
          ))}
        </Svg>
      )}
      {active && index !== null && (
        <ChartTooltip
          x={x(index)}
          width={width}
          title={`${formatWeekday(active.date)}, ${formatShortDate(active.date)}`}
          lines={[{ value: active.value === null ? 'keine Daten' : formatValue(active.value) }]}
        />
      )}
    </View>
  );
}
