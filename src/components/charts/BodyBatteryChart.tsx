import { View } from 'react-native';
import Svg, {
  Circle,
  Defs,
  Line,
  LinearGradient,
  Path,
  Stop,
  Text as SvgText,
} from 'react-native-svg';

import type { BodyBatteryPoint } from '@/types/health';
import { chartColors } from '@/theme';
import { formatClock } from '@/utils/format';

import {
  ChartTooltip,
  axisTextProps,
  linePath,
  scaleLinear,
  useLayoutWidth,
  useScrub,
  scrubSurfaceStyle,
} from './chartKit';

type Props = { points: BodyBatteryPoint[]; color: string; height?: number };

const PAD = { top: 44, right: 10, bottom: 22, left: 28 };

/** Energy level over the day (0–100) as a gradient area with scrub tooltip. */
export function BodyBatteryChart({ points, color, height = 170 }: Props) {
  const [width, onLayout] = useLayoutWidth();
  const x0 = PAD.left;
  const x1 = Math.max(x0 + 1, width - PAD.right);
  const t0 = points[0]?.timestamp ?? 0;
  const t1 = points.at(-1)?.timestamp ?? t0 + 1;
  const x = scaleLinear([t0, Math.max(t1, t0 + 1)], [x0, x1]);
  const y = scaleLinear([0, 100], [height - PAD.bottom, PAD.top]);
  const coords = points.map((p) => ({ x: x(p.timestamp), y: y(p.level) }));
  const line = linePath(coords);
  const area =
    coords.length > 1 ? `${line}L${coords.at(-1)!.x},${y(0)}L${coords[0]!.x},${y(0)}Z` : '';
  const { index, handlers } = useScrub(coords.map((c) => c.x));
  const active = index !== null ? points[index] : undefined;
  const last = coords.at(-1);

  return (
    <View
      onLayout={onLayout}
      style={[{ height }, scrubSurfaceStyle]}
      accessible
      accessibilityLabel="Body-Battery-Verlauf des Tages"
      {...handlers}
    >
      {width > 0 && points.length > 0 && (
        <Svg width={width} height={height}>
          <Defs>
            <LinearGradient id="bb" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={color} stopOpacity={0.35} />
              <Stop offset="1" stopColor={color} stopOpacity={0.02} />
            </LinearGradient>
          </Defs>
          {[25, 50, 75, 100].map((v) => (
            <Line
              key={v}
              x1={x0}
              x2={x1}
              y1={y(v)}
              y2={y(v)}
              stroke={chartColors.grid}
              strokeWidth={1}
            />
          ))}
          {[50, 100].map((v) => (
            <SvgText key={v} {...axisTextProps} x={x0 - 6} y={y(v) + 4} textAnchor="end">
              {v}
            </SvgText>
          ))}
          <Path d={area} fill="url(#bb)" />
          <Path d={line} stroke={color} strokeWidth={2} fill="none" strokeLinejoin="round" />
          {active && (
            <>
              <Line
                x1={x(active.timestamp)}
                x2={x(active.timestamp)}
                y1={PAD.top - 6}
                y2={y(0)}
                stroke={chartColors.crosshair}
                strokeWidth={1}
              />
              <Circle
                cx={x(active.timestamp)}
                cy={y(active.level)}
                r={5}
                fill={color}
                stroke={chartColors.markerRing}
                strokeWidth={2}
              />
            </>
          )}
          {!active && last && (
            <Circle
              cx={last.x}
              cy={last.y}
              r={5}
              fill={color}
              stroke={chartColors.markerRing}
              strokeWidth={2}
            />
          )}
          <SvgText {...axisTextProps} x={x0} y={height - 6} textAnchor="start">
            {formatClock(t0)}
          </SvgText>
          <SvgText {...axisTextProps} x={x1} y={height - 6} textAnchor="end">
            {formatClock(t1)}
          </SvgText>
        </Svg>
      )}
      {active && (
        <ChartTooltip
          x={x(active.timestamp)}
          width={width}
          title={formatClock(active.timestamp)}
          lines={[{ value: `${Math.round(active.level)} %` }]}
        />
      )}
    </View>
  );
}
