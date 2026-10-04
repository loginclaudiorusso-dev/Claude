import { useMemo, useState } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { useDb, useNow } from '../../services/hooks';
import { dashboardCsv, kpiSeries, popularOffers, weekKpis } from '../../domain/stats';
import { addDays, fmt, startOfWeek } from '../../domain/time';
import { Button, Card, LargeTitle, Page, SectionHeader, TeamBadge, cx, useToast } from '../../components/ui';
import { BarList, DataTable, LineChart } from '../../components/charts';
import { TEAM_VAR } from '../../theme/teams';

export function downloadFile(name: string, content: string, type = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const pct = (v: number) => `${Math.round(v * 100)} %`;

export function Dashboard() {
  const db = useDb();
  const now = useNow();
  const toast = useToast();
  const [offset, setOffset] = useState(0);
  const [siteFilter, setSiteFilter] = useState<string>('all');
  const week = addDays(startOfWeek(now), -7 * offset);
  const prev = addDays(week, -7);

  const rows = useMemo(() => db.sites.map((s) => ({ site: s, k: weekKpis(db, s.id, week), p: weekKpis(db, s.id, prev) })), [db, week.getTime()]); // eslint-disable-line react-hooks/exhaustive-deps
  const series = useMemo(() => db.sites.map((s) => ({ site: s, list: kpiSeries(db, s.id, 12, week) })), [db, week.getTime()]); // eslint-disable-line react-hooks/exhaustive-deps
  const offers = useMemo(() => popularOffers(db, addDays(week, -21), addDays(week, 7), siteFilter === 'all' ? undefined : siteFilter), [db, week.getTime(), siteFilter]); // eslint-disable-line react-hooks/exhaustive-deps
  const total = rows.reduce(
    (a, r) => ({ active: a.active + r.k.active, occ: a.occ + r.k.occupancy, checkins: a.checkins + r.k.checkins, pActive: a.pActive + r.p.active }),
    { active: 0, occ: 0, checkins: 0, pActive: 0 },
  );
  const xLabels = series[0].list.map((k) => fmt.week(k.week).replace('KW ', ''));
  const visibleRows = rows.filter((r) => siteFilter === 'all' || r.site.id === siteFilter);
  const events = db.events
    .filter((e) => (siteFilter === 'all' || e.siteId === siteFilter) && Date.parse(e.start) >= week.getTime() && Date.parse(e.start) < addDays(week, 14).getTime())
    .sort((a, b) => Date.parse(a.start) - Date.parse(b.start));

  return (
    <Page>
      <LargeTitle
        eyebrow="Leitung"
        title="Dashboard"
        trailing={
          <Button
            variant="secondary"
            size="sm"
            icon={<Download className="size-4" />}
            onClick={() => {
              downloadFile(`innmotion-kennzahlen-${fmt.week(week).replace(' ', '')}.csv`, dashboardCsv(db, 12, week));
              toast('CSV exportiert – nur aggregierte Werte, keine Personen.');
            }}
          >
            CSV
          </Button>
        }
      />

      {/* Filter in einer Zeile */}
      <div className="mb-4 flex items-center gap-2">
        <Button variant="secondary" size="sm" className="w-10 px-0" aria-label="Vorherige Woche" onClick={() => setOffset(offset + 1)} disabled={offset >= 11}>
          <ChevronLeft className="size-5" aria-hidden />
        </Button>
        <p className="min-w-0 flex-1 text-center text-[15px] font-bold">
          {fmt.week(week)} <span className="font-medium text-muted">· {fmt.date(week)}–{fmt.date(addDays(week, 6))}</span>
        </p>
        <Button variant="secondary" size="sm" className="w-10 px-0" aria-label="Nächste Woche" onClick={() => setOffset(offset - 1)} disabled={offset <= 0}>
          <ChevronRight className="size-5" aria-hidden />
        </Button>
      </div>
      <div className="no-scrollbar -mx-4 mb-5 flex gap-2 overflow-x-auto px-4" role="group" aria-label="Standort filtern">
        {[{ id: 'all', name: 'Alle Standorte' }, ...db.sites].map((s) => (
          <button
            key={s.id}
            type="button"
            aria-pressed={siteFilter === s.id}
            onClick={() => setSiteFilter(s.id)}
            className={cx('press min-h-11 shrink-0 rounded-pill px-4 text-[14px] font-semibold', siteFilter === s.id ? 'bg-ink text-bg' : 'bg-surface text-ink-2 shadow-card')}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Kennzahlen gesamt */}
      {siteFilter === 'all' && (
        <Card className="mb-3">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-muted">Alle Standorte · {fmt.week(week)}</p>
          <div className="mt-2 flex items-end gap-6">
            <div>
              <p className="tnum text-[40px] font-extrabold leading-none tracking-tight">{pct(total.occ ? total.active / total.occ : 0)}</p>
              <p className="mt-1 text-[13px] text-muted">Teilnahmequote</p>
            </div>
            <div className="pb-1">
              <p className="tnum text-[22px] font-bold leading-none">
                {total.active}
                <span className="text-[14px] font-medium text-muted"> / {total.occ}</span>
              </p>
              <p className="mt-1 text-[13px] text-muted">aktiv / Belegung</p>
            </div>
            <div className="pb-1">
              <p className="tnum text-[22px] font-bold leading-none">{total.checkins}</p>
              <p className="mt-1 text-[13px] text-muted">Check-ins</p>
            </div>
          </div>
          <Delta now={total.active} before={total.pActive} label="aktive Teilnehmende ggü. Vorwoche" />
        </Card>
      )}

      <div className="space-y-3">
        {visibleRows.map(({ site, k, p }) => (
          <Card key={site.id}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[16px]">
                <TeamBadge site={site} />
              </span>
              <Delta now={k.active} before={p.active} label="ggü. Vorwoche" compact />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
              <Kpi label="Aktive TN" value={`${k.active}`} sub={`von ${k.occupancy} Plätzen`} />
              <Kpi label="Teilnahmequote" value={pct(k.rate)} sub="aktive ÷ Belegung" />
              <Kpi label="Check-ins" value={`${k.checkins}`} sub={topOffers(k.byOffer)} />
              <Kpi label="Event-Auslastung" value={k.events ? pct(k.eventUtilisation) : '–'} sub={k.events ? `${k.eventRegistered}/${k.eventSeats} Plätze · ${k.events} Events` : 'keine Events'} />
            </dl>
          </Card>
        ))}
      </div>

      <SectionHeader title="Teilnahmequote · 12 Wochen" />
      <Card>
        <LineChart
          title="Teilnahmequote je Standort in den letzten 12 Wochen"
          xLabels={xLabels.map((l) => `KW${l}`)}
          yMax={1}
          format={(v) => `${Math.round(v * 100)}%`}
          series={series.filter((s) => siteFilter === 'all' || s.site.id === siteFilter).map((s) => ({ id: s.site.id, label: s.site.name, color: TEAM_VAR[s.site.team], values: s.list.map((k) => k.rate) }))}
        />
      </Card>

      <SectionHeader title="Check-ins · 12 Wochen" />
      <Card>
        <LineChart
          title="Check-ins je Standort in den letzten 12 Wochen"
          xLabels={xLabels.map((l) => `KW${l}`)}
          series={series.filter((s) => siteFilter === 'all' || s.site.id === siteFilter).map((s) => ({ id: s.site.id, label: s.site.name, color: TEAM_VAR[s.site.team], values: s.list.map((k) => k.checkins) }))}
        />
      </Card>

      <SectionHeader title="Beliebteste Angebote" />
      <Card>
        <p className="mb-3 text-[13px] text-muted">Check-ins der letzten 4 Wochen</p>
        <BarList title="Beliebteste Angebote nach Check-ins" items={offers.slice(0, 8).map((o) => ({ key: o.offer, label: o.offer, value: o.count }))} />
      </Card>

      <SectionHeader title="Event-Auslastung" />
      <Card className="p-0">
        {events.length === 0 ? (
          <p className="p-4 text-[14px] text-muted">Keine Events in diesem Zeitraum.</p>
        ) : (
          <ul>
            {events.map((e) => {
              const u = e.capacity ? Math.min(1, e.registered.length / e.capacity) : 0;
              return (
                <li key={e.id} className="border-t border-line px-4 py-3 first:border-t-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="min-w-0 truncate text-[15px] font-semibold">{e.title}</p>
                    <p className="tnum shrink-0 text-[14px] font-bold">{pct(u)}</p>
                  </div>
                  <p className="text-[12px] text-muted">
                    {db.sites.find((s) => s.id === e.siteId)?.name} · {fmt.dateTime(e.start)} · {e.registered.length}/{e.capacity}
                    {e.waitlist.length ? ` · ${e.waitlist.length} Warteliste` : ''}
                  </p>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                    <div className="h-full rounded-full bg-accent" style={{ width: `${u * 100}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <SectionHeader title="Tabelle" />
      <Card>
        <DataTable
          visible
          caption={`Kennzahlen ${fmt.week(week)}`}
          head={['Standort', 'Aktiv', 'Quote', 'Check-ins', 'Events']}
          rows={rows.map(({ site, k }) => [site.name, k.active, pct(k.rate), k.checkins, k.events ? pct(k.eventUtilisation) : '–'])}
        />
      </Card>
    </Page>
  );
}

function topOffers(byOffer: Record<string, number>) {
  return (
    Object.entries(byOffer)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([o, n]) => `${o} ${n}`)
      .join(' · ') || 'keine'
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[12px] font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd>
        <span className="tnum block text-[24px] font-extrabold leading-tight">{value}</span>
        <span className="block truncate text-[12px] text-muted">{sub}</span>
      </dd>
    </div>
  );
}

function Delta({ now, before, label, compact }: { now: number; before: number; label: string; compact?: boolean }) {
  const d = now - before;
  const Icon = d > 0 ? ArrowUpRight : d < 0 ? ArrowDownRight : ArrowRight;
  const text = d > 0 ? `+${d}` : `${d}`;
  return (
    <p className={cx('flex items-center gap-1 text-[13px] font-semibold', d > 0 ? 'text-success' : d < 0 ? 'text-warn' : 'text-muted', !compact && 'mt-3')}>
      <Icon className="size-4" aria-hidden />
      <span>
        {d === 0 ? '±0' : text} {compact ? '' : label}
      </span>
      {compact && <span className="sr-only">{label}</span>}
    </p>
  );
}
