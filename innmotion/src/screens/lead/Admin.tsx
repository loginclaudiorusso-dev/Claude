import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, CalendarRange, Flag, MapPin, Plus, Power, Printer, Target } from 'lucide-react';
import { api, uid } from '../../services/mock/mockApi';
import { useDb, useNow } from '../../services/hooks';
import { placeCode, prettyCode } from '../../domain/codes';
import { activeSeason } from '../../domain/league';
import { addDays, fmt, startOfWeek } from '../../domain/time';
import type { Challenge, ChallengeMetric, ChallengeScope } from '../../domain/types';
import { Button, Card, Chip, Field, inputCls, LargeTitle, Page, SectionHeader, Segmented, Sheet, TeamBadge, cx, useToast } from '../../components/ui';
import { DynIcon, ICON_NAMES } from '../../components/DynIcon';
import { SiteLeague } from '../participant/Liga';
import { BackHeader } from '../participant/ProfilePages';

type Tab = 'sites' | 'challenges' | 'seasons' | 'rules';

export function Admin() {
  const [tab, setTab] = useState<Tab>('sites');
  return (
    <Page>
      <LargeTitle eyebrow="Leitung" title="Verwaltung" />
      <Segmented<Tab>
        label="Bereich"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'sites', label: 'Orte' },
          { value: 'challenges', label: 'Challenges' },
          { value: 'seasons', label: 'Saisons' },
          { value: 'rules', label: 'Regeln' },
        ]}
      />
      <div className="mt-5">
        {tab === 'sites' && <Sites />}
        {tab === 'challenges' && <ChallengesAdmin />}
        {tab === 'seasons' && <Seasons />}
        {tab === 'rules' && <Rules />}
      </div>
    </Page>
  );
}

function Sites() {
  const db = useDb();
  const navigate = useNavigate();
  const now = useNow();
  const toast = useToast();
  const [addFor, setAddFor] = useState<string | null>(null);
  const [name, setName] = useState('');
  return (
    <div className="space-y-4">
      {db.sites.map((site) => (
        <Card key={site.id} className="p-0">
          <div className="flex items-center justify-between gap-3 p-4">
            <span className="text-[17px]">
              <TeamBadge site={site} />
            </span>
            <label className="flex items-center gap-2 text-[13px] text-muted">
              Belegung
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={300}
                value={site.occupancy}
                onChange={(e) => api.updateSite(site.id, { occupancy: Math.max(1, Number(e.target.value) || 1) })}
                className="tnum h-11 w-20 rounded-[12px] border border-line bg-surface-2 text-center text-[16px] font-bold text-ink focus:border-accent focus:outline-none"
                aria-label={`Belegung ${site.name}`}
              />
            </label>
          </div>
          <ul>
            {db.places
              .filter((p) => p.siteId === site.id)
              .map((p) => (
                <li key={p.id} className={cx('flex min-h-14 items-center gap-3 border-t border-line px-4 py-2', !p.active && 'opacity-55')}>
                  <MapPin className="size-5 shrink-0 text-muted" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{p.name}</p>
                    <p className="tnum font-mono text-[13px] text-muted">{p.active ? `Heute: ${prettyCode(placeCode(db.codeSecret, p.id, now))}` : 'deaktiviert'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => api.togglePlace(p.id)}
                    aria-label={`${p.name} ${p.active ? 'deaktivieren' : 'aktivieren'}`}
                    aria-pressed={p.active}
                    className={cx('press flex size-11 items-center justify-center rounded-full', p.active ? 'bg-success-soft text-success' : 'bg-surface-2 text-muted')}
                  >
                    <Power className="size-4" aria-hidden />
                  </button>
                </li>
              ))}
          </ul>
          <div className="flex gap-2 border-t border-line p-3">
            <Button variant="ghost" size="sm" icon={<Plus className="size-4" />} onClick={() => setAddFor(site.id)}>
              Ort hinzufügen
            </Button>
            <Button variant="ghost" size="sm" icon={<Printer className="size-4" />} onClick={() => navigate(`/aushang/${site.id}`)}>
              Aushang
            </Button>
          </div>
        </Card>
      ))}
      <p className="px-1 text-[13px] text-muted">Die Belegung ist die Basis der Teilnahmequote (aktive Teilnehmende ÷ Belegung).</p>
      <Sheet
        open={!!addFor}
        onClose={() => setAddFor(null)}
        title="Ort hinzufügen"
        footer={
          <Button
            block
            disabled={name.trim().length < 2}
            onClick={async () => {
              await api.addPlace(addFor!, name.trim(), /halle/i.test(name) ? 'hall' : 'gym');
              toast('Ort angelegt – der QR-Code ist sofort verfügbar.');
              setName('');
              setAddFor(null);
            }}
          >
            Anlegen
          </Button>
        }
      >
        <Field label="Name des Ortes">{(id) => <input id={id} className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. Tischtennisraum" />}</Field>
      </Sheet>
    </div>
  );
}

const METRICS: { value: ChallengeMetric; label: string; scope: ChallengeScope[] }[] = [
  { value: 'activities', label: 'Aktivitäten (Check-ins)', scope: ['week', 'season'] },
  { value: 'newOffer', label: 'Neue Angebote ausprobieren', scope: ['week', 'season'] },
  { value: 'buddy', label: 'Zu zweit einchecken', scope: ['week', 'season'] },
  { value: 'activeWeeks', label: 'Aktive Wochen (mind. 2×)', scope: ['season'] },
  { value: 'teamCheckins', label: 'Team-Check-ins', scope: ['team'] },
  { value: 'teamEvents', label: 'Team-Event-Teilnahmen', scope: ['team'] },
];
const SCOPE_LABEL: Record<ChallengeScope, string> = { week: 'Woche', team: 'Team', season: 'Saison' };

function ChallengesAdmin() {
  const db = useDb();
  const [edit, setEdit] = useState<Challenge | null>(null);
  const now = useNow();
  const blank = (): Challenge => ({
    id: uid('ch'),
    scope: 'week',
    title: '',
    description: '',
    metric: 'activities',
    target: 3,
    start: startOfWeek(now).toISOString(),
    end: addDays(startOfWeek(now), 7).toISOString(),
    icon: 'Activity',
    active: true,
  });
  return (
    <>
      <Button block icon={<Plus className="size-5" />} onClick={() => setEdit(blank())}>
        Challenge anlegen
      </Button>
      <ul className="mt-4 space-y-2">
        {db.challenges.map((c) => (
          <li key={c.id}>
            <Card className={cx('flex items-center gap-3', !c.active && 'opacity-60')}>
              <span className="flex size-11 shrink-0 items-center justify-center rounded-[12px] bg-accent-soft text-accent">
                <DynIcon name={c.icon} className="size-5" />
              </span>
              <button type="button" className="min-w-0 flex-1 text-left" onClick={() => setEdit(c)}>
                <p className="truncate font-bold">{c.title}</p>
                <p className="text-[12px] text-muted">
                  {SCOPE_LABEL[c.scope]} · Ziel {c.targetBySite ? Object.values(c.targetBySite).join('/') : c.target}
                  {c.scope !== 'week' && ` · ${fmt.date(c.start)}–${fmt.date(c.end)}`}
                </p>
              </button>
              <Chip tone={c.active ? 'success' : 'neutral'}>{c.active ? 'Aktiv' : 'Pausiert'}</Chip>
            </Card>
          </li>
        ))}
      </ul>
      {edit && <ChallengeSheet value={edit} onClose={() => setEdit(null)} />}
    </>
  );
}

function ChallengeSheet({ value, onClose }: { value: Challenge; onClose: () => void }) {
  const db = useDb();
  const toast = useToast();
  const [c, setC] = useState(value);
  const exists = db.challenges.some((x) => x.id === c.id);
  const set = <K extends keyof Challenge>(k: K, v: Challenge[K]) => setC({ ...c, [k]: v });
  const dateVal = (iso: string) => iso.slice(0, 10);
  return (
    <Sheet
      open
      onClose={onClose}
      title={exists ? 'Challenge bearbeiten' : 'Neue Challenge'}
      footer={
        <div className="flex gap-3">
          {exists && (
            <Button
              variant="secondary"
              onClick={async () => {
                await api.toggleChallenge(c.id);
                onClose();
              }}
            >
              {c.active ? 'Pausieren' : 'Aktivieren'}
            </Button>
          )}
          <Button
            block
            disabled={c.title.trim().length < 3 || c.target < 1}
            onClick={async () => {
              await api.saveChallenge({ ...c, title: c.title.trim() });
              toast('Challenge gespeichert.');
              onClose();
            }}
          >
            Speichern
          </Button>
        </div>
      }
    >
      <div className="mb-4">
        <p className="mb-1.5 text-[14px] font-semibold text-ink-2">Art</p>
        <Segmented<ChallengeScope>
          label="Art"
          value={c.scope}
          onChange={(scope) => setC({ ...c, scope, metric: METRICS.find((m) => m.scope.includes(scope))!.value, targetBySite: undefined })}
          options={[
            { value: 'week', label: 'Woche' },
            { value: 'team', label: 'Team' },
            { value: 'season', label: 'Saison' },
          ]}
        />
      </div>
      <Field label="Titel">{(id) => <input id={id} className={inputCls} value={c.title} onChange={(e) => set('title', e.target.value)} />}</Field>
      <Field label="Beschreibung">{(id) => <textarea id={id} className={inputCls + ' min-h-20 py-3'} value={c.description} onChange={(e) => set('description', e.target.value)} />}</Field>
      <Field label="Was wird gezählt?">
        {(id) => (
          <select id={id} className={inputCls} value={c.metric} onChange={(e) => set('metric', e.target.value as ChallengeMetric)}>
            {METRICS.filter((m) => m.scope.includes(c.scope)).map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        )}
      </Field>
      {c.scope === 'team' ? (
        <div className="grid grid-cols-3 gap-2">
          {db.sites.map((s) => (
            <Field key={s.id} label={`Ziel ${s.short}`}>
              {(id) => (
                <input
                  id={id}
                  type="number"
                  inputMode="numeric"
                  className={inputCls}
                  value={c.targetBySite?.[s.id] ?? c.target}
                  onChange={(e) => set('targetBySite', { ...Object.fromEntries(db.sites.map((x) => [x.id, c.targetBySite?.[x.id] ?? c.target])), [s.id]: Number(e.target.value) || 1 })}
                />
              )}
            </Field>
          ))}
        </div>
      ) : (
        <Field label="Ziel">{(id) => <input id={id} type="number" inputMode="numeric" min={1} className={inputCls} value={c.target} onChange={(e) => set('target', Number(e.target.value) || 1)} />}</Field>
      )}
      {c.scope !== 'week' ? (
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start">{(id) => <input id={id} type="date" className={inputCls} value={dateVal(c.start)} onChange={(e) => set('start', new Date(e.target.value).toISOString())} />}</Field>
          <Field label="Ende">{(id) => <input id={id} type="date" className={inputCls} value={dateVal(c.end)} onChange={(e) => set('end', new Date(e.target.value).toISOString())} />}</Field>
        </div>
      ) : (
        <p className="mb-4 text-[13px] text-muted">Wochen-Challenges starten jeden Montag automatisch neu.</p>
      )}
      <p className="mb-1.5 text-[14px] font-semibold text-ink-2">Symbol</p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Symbol">
        {ICON_NAMES.map((n) => (
          <button key={n} type="button" role="radio" aria-checked={c.icon === n} aria-label={n} onClick={() => set('icon', n)} className={cx('press flex size-12 items-center justify-center rounded-[12px]', c.icon === n ? 'bg-accent text-accent-ink' : 'bg-surface-2 text-ink-2')}>
            <DynIcon name={n} className="size-5" />
          </button>
        ))}
      </div>
    </Sheet>
  );
}

function Seasons() {
  const db = useDb();
  const toast = useToast();
  const season = activeSeason(db);
  const [confirm, setConfirm] = useState<'end' | 'start' | null>(null);
  const [name, setName] = useState('Winter-Saison 2026/27');
  const [weeks, setWeeks] = useState(12);
  return (
    <>
      <Card>
        <div className="flex items-start gap-3">
          <CalendarRange className="mt-0.5 size-6 text-accent" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-bold uppercase tracking-wider text-muted">Aktive Saison</p>
            <p className="text-[18px] font-extrabold">{season ? season.name : 'Keine'}</p>
            {season && <p className="text-[13px] text-muted">{fmt.date(season.start)} – {fmt.date(season.end)}</p>}
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <Button variant="secondary" disabled={!season} icon={<Flag className="size-4" />} onClick={() => setConfirm('end')}>
            Beenden
          </Button>
          <Button icon={<Plus className="size-4" />} onClick={() => setConfirm('start')}>
            Neue Saison
          </Button>
        </div>
      </Card>
      <SectionHeader title="Aktueller Stand" />
      <SiteLeague showArchive />
      <Sheet
        open={confirm === 'end'}
        onClose={() => setConfirm(null)}
        title="Saison beenden?"
        footer={
          <Button
            block
            variant="danger"
            onClick={async () => {
              await api.endSeason();
              toast('Saison beendet und ins Archiv verschoben.');
              setConfirm(null);
            }}
          >
            Beenden und archivieren
          </Button>
        }
      >
        <p className="text-[15px] text-ink-2">Der aktuelle Stand wird als Endergebnis ins Archiv übernommen. Danach zählt keine Saisonwertung, bis eine neue Saison startet.</p>
      </Sheet>
      <Sheet
        open={confirm === 'start'}
        onClose={() => setConfirm(null)}
        title="Neue Saison starten"
        footer={
          <Button
            block
            disabled={name.trim().length < 3}
            onClick={async () => {
              if (season) await api.endSeason();
              await api.startSeason(name.trim(), weeks);
              toast('Neue Saison gestartet – alle Teams beginnen bei null.');
              setConfirm(null);
            }}
          >
            Starten (Punkte zurücksetzen)
          </Button>
        }
      >
        <Field label="Name">{(id) => <input id={id} className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Dauer in Wochen">{(id) => <input id={id} type="number" inputMode="numeric" min={2} max={26} className={inputCls} value={weeks} onChange={(e) => setWeeks(Number(e.target.value) || 12)} />}</Field>
        <p className="text-[14px] text-ink-2">{season ? 'Die laufende Saison wird vorher beendet und archiviert. ' : ''}Abzeichen und Verlauf bleiben erhalten, die Liga startet bei null.</p>
      </Sheet>
    </>
  );
}

function Rules() {
  const db = useDb();
  const s = db.settings;
  return (
    <Card>
      <div className="flex items-center gap-2">
        <Target className="size-5 text-accent" aria-hidden />
        <h2 className="text-[17px] font-bold">Punkte & Regeln</h2>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Field label="Wochenziel (Aktivitäten)">
          {(id) => <input id={id} type="number" inputMode="numeric" min={1} max={7} className={inputCls} value={s.weeklyGoal} onChange={(e) => api.updateSettings({ weeklyGoal: Math.max(1, Number(e.target.value) || 1) })} />}
        </Field>
        <Field label="Tagesobergrenze (Punkte)">
          {(id) => <input id={id} type="number" inputMode="numeric" min={10} max={200} className={inputCls} value={s.dailyPointCap} onChange={(e) => api.updateSettings({ dailyPointCap: Math.max(10, Number(e.target.value) || 10) })} />}
        </Field>
      </div>
      <ul className="mt-1 space-y-1.5 text-[14px] text-ink-2">
        <li>• Check-in Fitnessraum/Halle: 10 Punkte</li>
        <li>• Event: laut Event (Standard 15, Turnier 20)</li>
        <li>• Neues Angebot ausprobiert: +5</li>
        <li>• Zu zweit eingecheckt (10 Min.): +5 für beide</li>
        <li>• Wochenziel erreicht: +10</li>
        <li>• Pro Ort höchstens ein Check-in je 3 Stunden</li>
      </ul>
      <p className="mt-3 flex items-center gap-2 text-[13px] text-muted">
        <Building2 className="size-4" aria-hidden /> Gilt für alle Standorte gleich.
      </p>
    </Card>
  );
}

export function Privacy() {
  const db = useDb();
  const now = useNow();
  const days = db.settings.deleteAfterDays;
  const participants = db.persons.filter((p) => p.role === 'participant');
  const due = participants.filter((p) => Date.parse(p.programEnd) + days * 86_400_000 < now.getTime() + 30 * 86_400_000);
  return (
    <Page>
      <BackHeader />
      <LargeTitle eyebrow="Leitung" title="Datenschutz" subtitle="Datensparsam von Anfang an. Im Prototyp sind die Einstellungen sichtbar, aber ohne echte Personendaten." />
      <Card>
        <h2 className="text-[17px] font-bold">Automatische Löschung</h2>
        <p className="mt-1 text-[14px] text-ink-2">Konten werden nach Maßnahmeende automatisch gelöscht. Anonyme Umfrage-Antworten und aggregierte Kennzahlen bleiben erhalten.</p>
        <div className="mt-4">
          <Segmented
            label="Löschfrist"
            value={String(days)}
            onChange={(v) => api.updateSettings({ deleteAfterDays: Number(v) })}
            options={['0', '14', '30', '90'].map((d) => ({ value: d, label: d === '0' ? 'Sofort' : `${d} Tage` }))}
          />
        </div>
        <p className="mt-3 text-[14px] font-semibold">
          {due.length} {due.length === 1 ? 'Konto wird' : 'Konten werden'} in den nächsten 30 Tagen gelöscht.
        </p>
      </Card>
      <SectionHeader title="Was gespeichert wird" />
      <Card>
        <ul className="space-y-2 text-[14px] text-ink-2">
          <li>• Spitzname, Standort, optional Haus/Etage</li>
          <li>• Check-ins (Ort/Event, Zeitpunkt, Punkte)</li>
          <li>• Event-Anmeldungen, Ideen und Stimmen</li>
          <li>• Opt-in Einzel-Rangliste, Benachrichtigungen an/aus</li>
          <li>• Voraussichtliches Maßnahmeende (für die Löschfrist)</li>
        </ul>
      </Card>
      <SectionHeader title="Was nie gespeichert wird" />
      <Card>
        <ul className="space-y-2 text-[14px] text-ink-2">
          <li>• Klarnamen, Gesundheits- oder Körperdaten</li>
          <li>• Standortverlauf / GPS, Sensordaten des Handys</li>
          <li>• Kamerabilder (der Scanner liest nur den Code)</li>
          <li>• Tracker, Analytics oder Werbe-IDs</li>
        </ul>
      </Card>
      <p className="mt-4 px-1 text-[13px] text-muted">Exporte enthalten ausschließlich aggregierte Werte je Standort und Woche.</p>
    </Page>
  );
}

export function LeadLiga() {
  return (
    <Page>
      <LargeTitle eyebrow="Leitung" title="Standort-Liga" subtitle="Fairer Vergleich: Punkte pro aktivem Teilnehmenden." />
      <SiteLeague />
    </Page>
  );
}
