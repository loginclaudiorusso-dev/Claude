import { View } from 'react-native';
import Svg, { Line, Rect, Text as SvgText } from 'react-native-svg';

import type { SleepSession, SleepStage } from '@/types/health';
import { chartColors, sleepStageColors } from '@/theme';
import { formatClock } from '@/utils/format';

import { axisTextProps, scaleLinear, useLayoutWidth } from './chartKit';
import { STAGE_LABEL } from './SleepStagesChart';

const ROWS: { stage: keyof typeof sleepStageColors; label: string }[] = [
  { stage: 'awake', label: STAGE_LABEL.awake },
  { stage: 'rem', label: STAGE_LABEL.rem },
  { stage: 'core', label: STAGE_LABEL.core },
  { stage: 'deep', label: STAGE_LABEL.deep },
];

const LABEL_W = 40;
const ROW_H = 22;
const BAR_H = 14;
const AXIS_H = 20;

const rowOf = (stage: SleepStage) =>
  ROWS.findIndex((r) => r.stage === stage || (stage === 'asleep' && r.stage === 'core'));

/** Stage timeline for one night. Row position encodes stage, so colour is never the only cue. */
export function Hypnogram({ session }: { session: SleepSession }) {
  const [width, onLayout] = useLayoutWidth();
  const height = ROWS.length * ROW_H + AXIS_H;
  const x = scaleLinear([session.start, session.end], [LABEL_W, Math.max(LABEL_W + 1, width - 4)]);
  const segments = session.segments.filter((s) => s.stage !== 'inBed');
  const unstaged = segments.every((s) => s.stage === 'asleep' || s.stage === 'awake');

  return (
    <View
      onLayout={onLayout}
      style={{ height }}
      accessible
      accessibilityLabel={`Schlafverlauf von ${formatClock(session.start)} bis ${formatClock(session.end)}`}
    >
      {width > 0 && (
        <Svg width={width} height={height}>
          {ROWS.map((row, i) => (
            <SvgText key={row.stage} {...axisTextProps} x={0} y={i * ROW_H + ROW_H / 2 + 4}>
              {row.label}
            </SvgText>
          ))}
          {ROWS.map((_, i) => (
            <Line
              key={i}
              x1={LABEL_W}
              x2={width - 4}
              y1={i * ROW_H + ROW_H / 2}
              y2={i * ROW_H + ROW_H / 2}
              stroke={chartColors.grid}
              strokeWidth={1}
            />
          ))}
          {segments.map((seg, k) => {
            const r = rowOf(seg.stage);
            if (r < 0) return null;
            const stage = ROWS[r]!.stage;
            const w = Math.max(1.5, x(seg.end) - x(seg.start) - 1);
            return (
              <Rect
                key={k}
                x={x(seg.start)}
                y={r * ROW_H + (ROW_H - BAR_H) / 2}
                width={w}
                height={BAR_H}
                rx={Math.min(4, w / 2)}
                fill={sleepStageColors[stage]}
                opacity={unstaged && stage === 'core' ? 0.6 : 1}
              />
            );
          })}
          <SvgText {...axisTextProps} x={LABEL_W} y={height - 4} textAnchor="start">
            {formatClock(session.start)}
          </SvgText>
          <SvgText {...axisTextProps} x={width - 4} y={height - 4} textAnchor="end">
            {formatClock(session.end)}
          </SvgText>
        </Svg>
      )}
    </View>
  );
}
