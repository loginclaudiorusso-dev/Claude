// Schlanke SVG-Diagramme ohne externe Bibliothek.
// Regeln: dünne Linien, direkte Beschriftung, Legende ab 2 Reihen, Tooltip per Tippen/Hover, Tabellenansicht für Screenreader.

import { useId, useState, type ReactNode } from 'react';
import { cx } from './ui';

export interface Series {
  id: string;
  label: string;
  color: string;
  values: number[];
}

export function LineChart({
  series,
  xLabels,
  height = 180,
  format = (v: number) => String(Math.round(v)),
  title,
  yMax,
}: {
  series: Series[];
  xLabels: string[];
  height?: number;
  format?: (v: number) => string;
  title: string;
  yMax?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const tableId = useId();
  const W = 340;
  const H = height;
  const pad = { l: 34, r: 16, t: 12, b: 24 };
  const n = xLabels.length;
  const max = yMax ?? Math.max(1, ...series.flatMap((s) => s.values)) * 1.1;
  const ticks = niceTicks(max);
  const top = ticks[ticks.length - 1];
  const x = (i: number) => pad.l + (n <= 1 ? 0 : (i / (n - 1)) * (W - pad.l - pad.r));
  const y = (v: number) => pad.t + (1 - v / top) * (H - pad.t - pad.b);
  const labelEvery = Math.ceil(n / 6);

  return (
    <figure className="w-full">
      <figcaption className="sr-only">{title}</figcaption>
      {series.length > 1 && <Legend series={series} />}
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={title} aria-describedby={tableId} onMouseLeave={() => setHover(null)}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
              <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" className="fill-muted text-[10px]">
                {format(t)}
              </text>
            </g>
          ))}
          {xLabels.map((l, i) =>
            (n - 1 - i) % labelEvery === 0 ? (
              <text key={i} x={x(i)} y={H - 6} textAnchor={i === n - 1 ? 'end' : i === 0 ? 'start' : 'middle'} className="fill-muted text-[10px]">
                {l}
              </text>
            ) : null,
          )}
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={H - pad.b} stroke="var(--muted)" strokeWidth={1} strokeDasharray="3 3" />}
          {series.map((s) => (
            <g key={s.id}>
              <path d={s.values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ')} fill="none" stroke={s.color} strokeWidth={2.25} strokeLinejoin="round" strokeLinecap="round" />
              <circle cx={x(s.values.length - 1)} cy={y(s.values[s.values.length - 1] ?? 0)} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
              {hover !== null && s.values[hover] !== undefined && <circle cx={x(hover)} cy={y(s.values[hover])} r={4.5} fill={s.color} stroke="var(--surface)" strokeWidth={2} />}
            </g>
          ))}
          {/* Große, unsichtbare Trefferflächen je x-Wert */}
          {xLabels.map((_, i) => (
            <rect
              key={i}
              x={x(i) - (W - pad.l - pad.r) / Math.max(1, n - 1) / 2}
              y={0}
              width={(W - pad.l - pad.r) / Math.max(1, n - 1)}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onClick={() => setHover(hover === i ? null : i)}
            />
          ))}
        </svg>
        {hover !== null && (
          <div
            className="pointer-events-none absolute top-0 z-10 min-w-[120px] rounded-[12px] bg-surface px-3 py-2 text-[12px] shadow-float"
            style={{ left: `${Math.min(70, Math.max(5, (x(hover) / W) * 100 - 15))}%` }}
          >
            <p className="mb-1 font-bold text-ink">{xLabels[hover]}</p>
            {series.map((s) => (
              <p key={s.id} className="flex items-center gap-2 text-ink-2">
                <span className="inline-block h-0.5 w-3 rounded" style={{ background: s.color }} aria-hidden />
                <span className="flex-1">{s.label}</span>
                <span className="tnum font-semibold text-ink">{format(s.values[hover] ?? 0)}</span>
              </p>
            ))}
          </div>
        )}
      </div>
      <DataTable
        id={tableId}
        caption={title}
        head={['', ...series.map((s) => s.label)]}
        rows={xLabels.map((l, i) => [l, ...series.map((s) => format(s.values[i] ?? 0))])}
      />
    </figure>
  );
}

export function Legend({ series }: { series: { id: string; label: string; color: string }[] }) {
  return (
    <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[12px] font-semibold text-ink-2">
      {series.map((s) => (
        <li key={s.id} className="flex items-center gap-1.5">
          <span className="inline-block h-1 w-4 rounded-full" style={{ background: s.color }} aria-hidden />
          {s.label}
        </li>
      ))}
    </ul>
  );
}

/** Horizontale Balken – gut lesbar auf schmalen Displays, Werte direkt am Balken. */
export function BarList({ items, format = (v: number) => String(v), title, color = 'var(--accent)' }: { items: { label: ReactNode; value: number; key: string; color?: string }[]; format?: (v: number) => string; title: string; color?: string }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <figure>
      <figcaption className="sr-only">{title}</figcaption>
      <ul className="space-y-2.5">
        {items.map((i) => (
          <li key={i.key} className="grid grid-cols-[minmax(0,7.5rem)_1fr_auto] items-center gap-3">
            <span className="truncate text-[14px] font-semibold text-ink">{i.label}</span>
            <span className="h-3 overflow-hidden rounded-r-[4px] bg-transparent">
              <span className="bar-progress block h-full rounded-r-[4px]" style={{ width: `${(i.value / max) * 100}%`, background: i.color ?? color }} aria-hidden />
            </span>
            <span className="tnum min-w-8 text-right text-[14px] font-bold text-ink">{format(i.value)}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export function DataTable({ id, caption, head, rows, visible }: { id?: string; caption: string; head: string[]; rows: (string | number)[][]; visible?: boolean }) {
  // Tabellen ignorieren overflow:hidden – daher für Screenreader in einen sr-only-Container legen.
  return (
    <div className={visible ? undefined : 'sr-only'}>
    <table id={id} className={cx('w-full text-[13px]', visible && 'mt-3')}>
      <caption className={visible ? 'sr-only' : undefined}>{caption}</caption>
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={i} scope="col" className="border-b border-line py-1.5 text-left font-semibold text-muted">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) =>
              j === 0 ? (
                <th key={j} scope="row" className="border-b border-line py-1.5 text-left font-semibold">
                  {c}
                </th>
              ) : (
                <td key={j} className="tnum border-b border-line py-1.5">
                  {c}
                </td>
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
}

function niceTicks(max: number): number[] {
  const raw = max / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out = [];
  for (let v = 0; v <= max + step * 0.001; v += step) out.push(Math.round(v * 100) / 100);
  if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
  return out;
}

