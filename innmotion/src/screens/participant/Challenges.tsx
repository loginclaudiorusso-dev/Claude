import { useMemo } from 'react';
import { CircleCheck, Clock, Hourglass, Play } from 'lucide-react';
import { useDb, useMe, useNow } from '../../services/hooks';
import { challengeProgress, currentWindow, STATUS_LABEL, type ChallengeProgress } from '../../domain/challenges';
import { DAY, fmt } from '../../domain/time';
import type { ChallengeScope } from '../../domain/types';
import { Card, Chip, LargeTitle, Page, ProgressBar, SectionHeader, cx } from '../../components/ui';
import { DynIcon } from '../../components/DynIcon';

const SCOPES: { scope: ChallengeScope; title: string; hint: string }[] = [
  { scope: 'week', title: 'Diese Woche', hint: 'Starten jeden Montag neu.' },
  { scope: 'team', title: 'Team-Challenges', hint: 'Jeder Check-in zählt für alle an deinem Standort.' },
  { scope: 'season', title: 'Saison', hint: 'Für alle, die länger dranbleiben wollen.' },
];

export function Challenges() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const site = db.sites.find((s) => s.id === me.siteId)!;

  const list = useMemo(
    () =>
      db.challenges
        .filter((c) => c.active)
        .map((c) => currentWindow(c, now))
        .filter((c) => Date.parse(c.end) > now.getTime())
        .map((c) => challengeProgress(db, c, me.id, now)),
    [db, me.id, now],
  );
  const done = list.filter((p) => p.status === 'geschafft').length;
  const running = list.filter((p) => p.status !== 'bald').length;

  return (
    <Page>
      <LargeTitle title="Challenges" subtitle={`${done} von ${running} laufenden Challenges geschafft`} />
      {SCOPES.map(({ scope, title, hint }) => {
        const items = list.filter((p) => p.challenge.scope === scope);
        if (!items.length) return null;
        return (
          <section key={scope} aria-labelledby={`sec-${scope}`}>
            <SectionHeader id={`sec-${scope}`} title={scope === 'team' ? `${title} · ${site.name}` : title} />
            <p className="-mt-2 mb-3 text-[14px] text-muted">{hint}</p>
            <div className="space-y-3">
              {items.map((p) => (
                <ChallengeCard key={p.challenge.id} p={p} now={now} />
              ))}
            </div>
          </section>
        );
      })}
    </Page>
  );
}

function ChallengeCard({ p, now }: { p: ChallengeProgress; now: Date }) {
  const { challenge: c, status } = p;
  const daysLeft = Math.max(0, Math.ceil((Date.parse(c.end) - now.getTime()) / DAY));
  const statusIcon = {
    bald: <Hourglass className="size-3" aria-hidden />,
    offen: <Clock className="size-3" aria-hidden />,
    läuft: <Play className="size-3" aria-hidden />,
    geschafft: <CircleCheck className="size-3" aria-hidden />,
    beendet: <Clock className="size-3" aria-hidden />,
  }[status];
  const tone = status === 'geschafft' ? 'success' : status === 'läuft' ? 'accent' : 'neutral';
  return (
    <Card as="article" className={cx(status === 'bald' && 'opacity-80')}>
      <div className="flex items-start gap-3">
        <span className={cx('flex size-12 shrink-0 items-center justify-center rounded-[14px]', status === 'geschafft' ? 'bg-success-soft text-success' : 'bg-accent-soft text-accent')}>
          <DynIcon name={c.icon} className="size-6" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-[17px] font-bold leading-snug">{c.title}</h3>
            <Chip tone={tone} icon={statusIcon}>
              {STATUS_LABEL[status]}
            </Chip>
          </div>
          <p className="mt-1 text-[14px] leading-snug text-ink-2">{c.description}</p>
        </div>
      </div>
      {status === 'bald' ? (
        <p className="mt-3 text-[14px] font-semibold text-muted">Startet am {fmt.date(c.start)}</p>
      ) : (
        <div className="mt-4">
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="tnum text-[15px] font-bold">
              {p.current} <span className="font-medium text-muted">/ {p.target}</span>
            </span>
            <span className="text-[13px] text-muted">{daysLeft === 0 ? 'endet heute' : `noch ${daysLeft} ${daysLeft === 1 ? 'Tag' : 'Tage'}`}</span>
          </div>
          <ProgressBar value={p.current} max={p.target} label={`${c.title}: ${p.current} von ${p.target}`} tone={status === 'geschafft' ? 'success' : 'accent'} />
        </div>
      )}
    </Card>
  );
}
