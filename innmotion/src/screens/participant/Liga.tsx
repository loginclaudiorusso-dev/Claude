import { useMemo, useState } from 'react';
import { ChevronDown, Crown, EyeOff, Info, Medal, Users } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { activeSeason, individualLeaderboard, seasonRange, seasonSeries, siteStandings, teamBand } from '../../domain/league';
import { fmt } from '../../domain/time';
import type { DB, Site } from '../../domain/types';
import { Avatar, Button, Card, Chip, LargeTitle, Page, SectionHeader, Segmented, TeamBadge, cx, useToast } from '../../components/ui';
import { LineChart } from '../../components/charts';
import { TournamentView } from '../../components/TournamentView';
import { TEAM_CLASSES, TEAM_VAR } from '../../theme/teams';

type Tab = 'sites' | 'tournaments' | 'people';

export function Liga() {
  const db = useDb();
  const [tab, setTab] = useState<Tab>('sites');
  const season = activeSeason(db);
  return (
    <Page>
      <LargeTitle title="Liga" subtitle={season ? `${season.name} · bis ${fmt.date(season.end)}` : 'Keine aktive Saison'} />
      <Segmented<Tab>
        label="Bereich"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'sites', label: 'Standorte' },
          { value: 'tournaments', label: 'Turniere' },
          { value: 'people', label: 'Einzel' },
        ]}
      />
      <div className="mt-5">
        {tab === 'sites' && <SiteLeague />}
        {tab === 'tournaments' && <Tournaments />}
        {tab === 'people' && <People />}
      </div>
    </Page>
  );
}

export function SiteLeague({ showArchive = true }: { showArchive?: boolean }) {
  const db = useDb();
  const me = useMe();
  const now = useNow();
  const season = activeSeason(db);
  const [from, to] = seasonRange(season, now);
  const standings = useMemo(() => siteStandings(db, from, to), [db, from.getTime(), to.getTime()]); // eslint-disable-line react-hooks/exhaustive-deps
  const series = useMemo(() => (season ? seasonSeries(db, season, now) : []), [db, season, now]);
  const [explain, setExplain] = useState(false);
  const siteById = (id: string) => db.sites.find((s) => s.id === id)!;

  return (
    <>
      <ol className="space-y-3">
        {standings.map((s) => {
          const site = siteById(s.siteId);
          const mine = me?.siteId === site.id && me.role === 'participant';
          return (
            <li key={s.siteId}>
              <Card className={cx('flex items-center gap-4', mine && 'ring-2 ring-accent')}>
                <div className="flex w-9 flex-col items-center">
                  {s.rank === 1 ? <Crown className="size-6 text-warn" aria-label="Platz 1" /> : <span className="tnum text-[22px] font-extrabold text-muted">{s.rank}</span>}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[16px]">
                    <TeamBadge site={site} />
                  </div>
                  <p className="mt-1 text-[13px] text-muted">
                    {s.active} aktiv · {s.total.toLocaleString('de-DE')} Punkte gesamt
                    {mine && <span className="font-semibold text-accent"> · Dein Team</span>}
                  </p>
                </div>
                <div className="text-right">
                  <p className="tnum text-[28px] font-extrabold leading-none">{Math.round(s.perActive)}</p>
                  <p className="mt-1 text-[11px] font-semibold text-muted">pro Kopf</p>
                </div>
              </Card>
            </li>
          );
        })}
      </ol>

      <button type="button" onClick={() => setExplain(!explain)} aria-expanded={explain} className="press mt-3 flex min-h-12 w-full items-center gap-2 rounded-[16px] bg-accent-soft px-4 text-left text-[14px] font-semibold text-accent">
        <Info className="size-4 shrink-0" aria-hidden />
        <span className="flex-1">Warum „pro Kopf“?</span>
        <ChevronDown className={cx('size-4 transition-transform', explain && 'rotate-180')} aria-hidden />
      </button>
      {explain && (
        <p className="mt-2 px-1 text-[14px] leading-relaxed text-ink-2">
          Gezählt werden die Punkte pro aktivem Teilnehmenden – also alle Punkte des Teams geteilt durch die Zahl der Personen, die in der Saison mindestens einmal dabei waren. So hat ein kleiner Standort die gleichen Chancen wie ein großer.
        </p>
      )}

      {series.length > 1 && (
        <>
          <SectionHeader title="Saisonverlauf" />
          <Card>
            <LineChart
              title="Punkte pro aktivem Teilnehmenden im Saisonverlauf"
              xLabels={series.map((p) => fmt.week(p.week).replace('KW ', 'KW'))}
              series={db.sites.map((site) => ({ id: site.id, label: site.name, color: TEAM_VAR[site.team], values: series.map((p) => p.values[site.id] ?? 0) }))}
            />
          </Card>
        </>
      )}

      {showArchive && <SeasonArchive db={db} siteById={siteById} />}
    </>
  );
}

function SeasonArchive({ db, siteById }: { db: DB; siteById: (id: string) => Site }) {
  const archived = db.seasons.filter((s) => s.status === 'archived' && s.results);
  if (!archived.length) return null;
  return (
    <>
      <SectionHeader title="Archiv" />
      {archived.map((s) => {
        const winner = [...s.results!].sort((a, b) => b.perActive - a.perActive)[0];
        return (
          <Card key={s.id} className="mb-3 flex items-center gap-3">
            <Medal className="size-6 shrink-0 text-warn" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="font-bold">{s.name}</p>
              <p className="text-[13px] text-muted">
                Sieger: {siteById(winner.siteId).teamName} · {Math.round(winner.perActive)} pro Kopf
              </p>
            </div>
          </Card>
        );
      })}
    </>
  );
}

function Tournaments() {
  const db = useDb();
  const [open, setOpen] = useState<string | undefined>(db.tournaments[0]?.id);
  return (
    <div className="space-y-3">
      {db.tournaments.map((t) => (
        <section key={t.id}>
          <button type="button" aria-expanded={open === t.id} onClick={() => setOpen(open === t.id ? undefined : t.id)} className="press flex min-h-16 w-full items-center gap-3 rounded-card bg-surface p-4 text-left shadow-card">
            <div className="min-w-0 flex-1">
              <p className="text-[17px] font-bold">{t.title}</p>
              <p className="text-[13px] text-muted">
                {t.players.length} Teilnehmende · {new Set(t.players.map((p) => p.siteId)).size} Standorte
              </p>
            </div>
            <Chip tone={t.status === 'running' ? 'success' : 'neutral'}>{t.status === 'running' ? 'Läuft' : 'Beendet'}</Chip>
            <ChevronDown className={cx('size-5 text-muted transition-transform', open === t.id && 'rotate-180')} aria-hidden />
          </button>
          {open === t.id && (
            <div className="mt-3">
              <TournamentView t={t} />
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

function People() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const toast = useToast();
  const [from, to] = seasonRange(activeSeason(db), now);
  const rows = useMemo(() => individualLeaderboard(db, from, to, 10), [db, from.getTime(), to.getTime()]); // eslint-disable-line react-hooks/exhaustive-deps
  const band = teamBand(db, me.id, from, to);
  const site = db.sites.find((s) => s.id === me.siteId)!;

  return (
    <>
      <Card className={cx('flex items-start gap-3', TEAM_CLASSES[site.team].soft)}>
        <Users className="mt-0.5 size-6 shrink-0" aria-hidden />
        <div>
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-2">Dein Platz im {site.teamName}</p>
          <p className="mt-1 text-[17px] font-bold leading-snug">{band.text}</p>
        </div>
      </Card>

      {!me.leaderboardOptIn && (
        <Card className="mt-3">
          <div className="flex items-start gap-3">
            <EyeOff className="mt-0.5 size-5 shrink-0 text-muted" aria-hidden />
            <p className="text-[14px] text-ink-2">Du bist nicht in der Einzel-Rangliste. Das ist freiwillig – dein Fortschritt zählt trotzdem voll für dein Team.</p>
          </div>
          <Button
            variant="soft"
            block
            className="mt-3"
            onClick={() => {
              void api.updateProfile(me.id, { leaderboardOptIn: true });
              toast('Du erscheinst jetzt in der Einzel-Rangliste.', 'info');
            }}
          >
            Mitmachen
          </Button>
        </Card>
      )}

      <SectionHeader title="Top 10 · freiwillige Rangliste" />
      <p className="-mt-2 mb-3 text-[13px] text-muted">Hier erscheinen nur Personen, die das selbst eingeschaltet haben.</p>
      <Card className="p-0">
        <ol>
          {rows.map((r) => {
            const s = db.sites.find((x) => x.id === r.person.siteId)!;
            const isMe = r.person.id === me.id;
            return (
              <li key={r.person.id} className={cx('flex min-h-14 items-center gap-3 border-t border-line px-4 py-2 first:border-t-0', isMe && 'bg-accent-soft')}>
                <span className="tnum w-6 text-center text-[16px] font-extrabold text-muted">{r.rank}</span>
                <Avatar name={r.person.nickname} site={s} size={36} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">
                    {r.person.nickname}
                    {isMe && ' (du)'}
                  </p>
                  <p className="text-[12px] text-muted">{s.name}</p>
                </div>
                <span className="tnum font-bold">{r.points}</span>
              </li>
            );
          })}
        </ol>
      </Card>
    </>
  );
}
