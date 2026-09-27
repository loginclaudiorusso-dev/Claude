import { View } from 'react-native';
import Svg, { Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import type { DailySummary, DayKey } from '@/types/health';
import { chartColors, sleepStageColors } from '@/theme';
import { formatDuration, formatShortDate, formatWeekday } from '@/utils/format';

import {
  ChartTooltip,
  Legend,
  axisTextProps,
  roundedTopBar,
  scaleLinear,
  useLayoutWidth,
  useScrub,
  scrubSurfaceStyle,
} from './chartKit';

/** Stacking order is part of the validated palette – keep it. */
export const STAGE_ORDER = ['deep', 'rem', 'core', 'awake'] as const;
export const STAGE_LABEL = { deep: 'Tief', rem: 'REM', core: 'Kern', awake: 'Wach' } as const;

type Props = { dates: DayKey[]; summaries: Map<DayKey, DailySummary>; height?: number };

const PAD = { top: 56, right: 4, bottom: 22, left: 4 };
const GAP = 2;
const SEGMENT_GAP = 2;

/** Stacked sleep architecture per night with legend and scrub tooltip. */
export function SleepStagesChart({ dates, summaries, height = 220 }: Props) {
  const [width, onLayout] = useLayoutWidth();
  const n = Math.max(1, dates.length);
  const slot = (width - PAD.left - PAD.right) / n;
  const barW = Math.max(2, slot - GAP);
  const baseY = height - PAD.bottom;
  const nights = dates.map((d) => summaries.get(d)?.sleep);
  const maxMinutes = Math.max(
    540,
    ...nights.map((s) => (s ? s.totalSleepMinutes + s.stages.awake : 0)),
  );
  const y = scaleLinear([0, maxMinutes], [baseY, PAD.top]);
  const cx = (i: number) => PAD.left + slot * i + slot / 2;
  const { index, handlers } = useScrub(dates.map((_, i) => cx(i)));
  const short = dates.length <= 10;
  const ticks = short ? dates.map((_, i) => i) : [0, Math.floor((n - 1) / 2), n - 1];
  const activeNight = index !== null ? nights[index] : undefined;

  return (
    <View>
      <View
        onLayout={onLayout}
        style={[{ height }, scrubSurfaceStyle]}
        accessible
        accessibilityLabel="Schlafphasen pro Nacht"
        {...handlers}
      >
        {width > 0 && (
          <Svg width={width} height={height}>
            {[6, 8].map((h) => (
              <Line
                key={h}
                x1={PAD.left}
                x2={width - PAD.right}
                y1={y(h * 60)}
                y2={y(h * 60)}
                stroke={chartColors.grid}
                strokeWidth={1}
              />
            ))}
            <SvgText {...axisTextProps} x={width - PAD.right} y={y(480) - 4} textAnchor="end">
              8 h
            </SvgText>
            {nights.map((s, i) => {
              if (!s) return null;
              const staged = s.stageShare !== undefined;
              const x = PAD.left + slot * i + GAP / 2;
              const dim = index === null || index === i ? 1 : 0.45;
              if (!staged) {
                return (
                  <Path
                    key={i}
                    d={roundedTopBar(x, y(s.totalSleepMinutes), barW, baseY)}
                    fill={sleepStageColors.core}
                    opacity={dim * 0.6}
                  />
                );
              }
              let cursor = baseY;
              return STAGE_ORDER.map((stage, k) => {
                const mins = s.stages[stage];
                if (mins <= 0) return null;
                const top = cursor - (baseY - y(mins));
                const isTop = STAGE_ORDER.slice(k + 1).every((st) => s.stages[st] <= 0);
                const bottom = cursor;
                cursor = top - SEGMENT_GAP;
                return isTop ? (
                  <Path
                    key={stage + i}
                    d={roundedTopBar(x, top, barW, bottom)}
                    fill={sleepStageColors[stage]}
                    opacity={dim}
                  />
                ) : (
                  <Rect
                    key={stage + i}
                    x={x}
                    y={top}
                    width={barW}
                    height={Math.max(0, bottom - top)}
                    fill={sleepStageColors[stage]}
                    opacity={dim}
                  />
                );
              });
            })}
            {ticks.map((i) => (
              <SvgText
                key={i}
                {...axisTextProps}
                x={short ? cx(i) : i === 0 ? PAD.left : i === n - 1 ? width - PAD.right : cx(i)}
                y={height - 6}
                textAnchor={short ? 'middle' : i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}
              >
                {short ? formatWeekday(dates[i]!) : formatShortDate(dates[i]!)}
              </SvgText>
            ))}
          </Svg>
        )}
        {index !== null && (
          <ChartTooltip
            x={cx(index)}
            width={width}
            title={`${formatWeekday(dates[index]!)}, ${formatShortDate(dates[index]!)}`}
            lines={
              activeNight
                ? [
                    { label: 'Gesamt', value: formatDuration(activeNight.totalSleepMinutes) },
                    ...(activeNight.stageShare
                      ? STAGE_ORDER.map((st) => ({
                          label: STAGE_LABEL[st],
                          value: formatDuration(activeNight.stages[st]),
                          color: sleepStageColors[st],
                        }))
                      : []),
                  ]
                : [{ value: 'keine Daten' }]
            }
          />
        )}
      </View>
      <Legend
        items={STAGE_ORDER.map((st) => ({ label: STAGE_LABEL[st], color: sleepStageColors[st] }))}
      />
    </View>
  );
}
