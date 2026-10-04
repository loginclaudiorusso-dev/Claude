import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CircleCheck, Hammer, Lock, Plus, Star, ThumbsUp, Trash2 } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { BADGES, earnedBadges } from '../../domain/badges';
import { fmt } from '../../domain/time';
import type { IdeaStatus } from '../../domain/types';
import { Button, Card, Chip, Field, IconButton, inputCls, LargeTitle, Page, SectionHeader, Segmented, Sheet, cx, useToast } from '../../components/ui';
import { DynIcon } from '../../components/DynIcon';

export function BackHeader() {
  const navigate = useNavigate();
  return (
    <div className="pt-3">
      <IconButton label="Zurück" onClick={() => navigate(-1)}>
        <ArrowLeft className="size-5" />
      </IconButton>
    </div>
  );
}

// ------------------------------------------------------------------ Abzeichen

export function Badges() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const earned = earnedBadges(db, me.id, now);
  return (
    <Page>
      <BackHeader />
      <LargeTitle title="Abzeichen" subtitle={`${earned.size} von ${BADGES.length} gesammelt`} />
      <ul className="grid grid-cols-2 gap-3">
        {BADGES.map((b) => {
          const has = earned.has(b.id);
          return (
            <li key={b.id} className={cx('flex flex-col items-center rounded-card p-4 text-center shadow-card', has ? 'bg-surface' : 'bg-surface/60')}>
              <span
                className={cx('relative flex size-[72px] items-center justify-center rounded-full', has ? 'bg-gradient-to-br from-accent to-volt text-accent-ink' : 'bg-surface-2 text-muted')}
                aria-hidden
              >
                <DynIcon name={b.icon} className="size-8" />
                {!has && (
                  <span className="absolute -bottom-1 -right-1 flex size-7 items-center justify-center rounded-full border-2 border-surface bg-surface-3">
                    <Lock className="size-3.5" />
                  </span>
                )}
              </span>
              <p className={cx('mt-3 text-[15px] font-bold leading-tight', !has && 'text-ink-2')}>{b.title}</p>
              <p className="mt-1 text-[12px] leading-snug text-muted">{has ? 'Erreicht' : b.how}</p>
              <span className="sr-only">{has ? 'Abzeichen erreicht' : 'Noch nicht erreicht'}</span>
            </li>
          );
        })}
      </ul>
    </Page>
  );
}

// ------------------------------------------------------------------ Wünsch dir was

const IDEA_STATUS: Record<IdeaStatus, { label: string; tone: 'neutral' | 'accent' | 'success' }> = {
  neu: { label: 'Neu', tone: 'neutral' },
  umsetzung: { label: 'Wird umgesetzt', tone: 'accent' },
  erledigt: { label: 'Umgesetzt', tone: 'success' },
};

export function Ideas({ staffMode = false }: { staffMode?: boolean }) {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const toast = useToast();
  const [sort, setSort] = useState<'top' | 'new'>('top');
  const [scope, setScope] = useState<'site' | 'all'>('site');
  const [open, setOpen] = useState(false);
  const site = db.sites.find((s) => s.id === me.siteId)!;

  const list = useMemo(() => {
    const xs = db.ideas.filter((i) => scope === 'all' || i.siteId === me.siteId);
    return [...xs].sort((a, b) => (sort === 'top' ? b.votes.length - a.votes.length : Date.parse(b.createdAt) - Date.parse(a.createdAt)));
  }, [db.ideas, scope, sort, me.siteId]);

  return (
    <Page>
      <BackHeader />
      <LargeTitle
        title="Wünsch dir was"
        subtitle={staffMode ? 'Markiere Ideen, die ihr umsetzt – alle, die abgestimmt haben, werden benachrichtigt.' : 'Was fehlt dir? Reiche Ideen ein und stimme für die Ideen anderer.'}
      />
      {!staffMode && (
        <Button block size="lg" icon={<Plus className="size-5" />} onClick={() => setOpen(true)}>
          Idee einreichen
        </Button>
      )}
      <div className="mt-4 flex gap-2">
        <div className="flex-1">
          <Segmented label="Sortierung" value={sort} onChange={setSort} options={[{ value: 'top', label: 'Beliebt' }, { value: 'new', label: 'Neu' }]} />
        </div>
        <div className="flex-1">
          <Segmented label="Standort" value={scope} onChange={setScope} options={[{ value: 'site', label: site.name }, { value: 'all', label: 'Alle' }]} />
        </div>
      </div>
      <ul className="mt-4 space-y-3">
        {list.map((idea) => {
          const voted = idea.votes.includes(me.id);
          const s = db.sites.find((x) => x.id === idea.siteId)!;
          const st = IDEA_STATUS[idea.status];
          return (
            <li key={idea.id}>
              <Card className="flex gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Chip tone={st.tone} icon={idea.status === 'umsetzung' ? <Hammer className="size-3" aria-hidden /> : idea.status === 'erledigt' ? <CircleCheck className="size-3" aria-hidden /> : undefined}>
                      {st.label}
                    </Chip>
                    <span className="text-[12px] text-muted">
                      {s.name} · {fmt.relativeDay(idea.createdAt, now)}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[16px] font-bold leading-snug">{idea.title}</p>
                  {idea.text && <p className="mt-1 text-[14px] text-ink-2">{idea.text}</p>}
                  {staffMode && idea.siteId === me.siteId && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(['neu', 'umsetzung', 'erledigt'] as IdeaStatus[])
                        .filter((x) => x !== idea.status)
                        .map((x) => (
                          <Button
                            key={x}
                            size="sm"
                            variant={x === 'umsetzung' ? 'primary' : 'secondary'}
                            onClick={async () => {
                              await api.setIdeaStatus(idea.id, x);
                              toast(x === 'umsetzung' ? `„${idea.title}“ wird umgesetzt – ${idea.votes.length} Personen werden benachrichtigt.` : 'Status geändert.');
                            }}
                          >
                            {x === 'umsetzung' ? 'Wird umgesetzt' : x === 'erledigt' ? 'Umgesetzt' : 'Zurück auf neu'}
                          </Button>
                        ))}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  disabled={staffMode}
                  aria-pressed={voted}
                  aria-label={`${voted ? 'Daumen zurücknehmen' : 'Daumen hoch'} für „${idea.title}“, ${idea.votes.length} Stimmen`}
                  onClick={() => api.toggleVote(me.id, idea.id)}
                  className={cx('press flex h-[68px] w-14 shrink-0 flex-col items-center justify-center gap-0.5 rounded-[16px]', voted ? 'bg-accent text-accent-ink' : 'bg-surface-2 text-ink-2', staffMode && 'cursor-default')}
                >
                  <ThumbsUp className="size-5" aria-hidden fill={voted ? 'currentColor' : 'none'} />
                  <span className="tnum text-[14px] font-bold">{idea.votes.length}</span>
                </button>
              </Card>
            </li>
          );
        })}
      </ul>
      <NewIdeaSheet open={open} onClose={() => setOpen(false)} />
    </Page>
  );
}

function NewIdeaSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const me = useMe()!;
  const toast = useToast();
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Neue Idee"
      footer={
        <Button
          block
          disabled={title.trim().length < 3}
          onClick={async () => {
            await api.submitIdea(me.id, title.trim(), text.trim());
            setTitle('');
            setText('');
            toast('Danke! Deine Idee ist jetzt sichtbar.');
            onClose();
          }}
        >
          Einreichen
        </Button>
      }
    >
      <Field label="Deine Idee in wenigen Worten">
        {(id) => <input id={id} className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={60} placeholder="z. B. Lauftreff am Sonntag" />}
      </Field>
      <Field label="Beschreibung (optional)" hint="Bitte keine Namen oder Gesundheitsangaben.">
        {(id) => <textarea id={id} className={inputCls + ' min-h-28 py-3'} value={text} onChange={(e) => setText(e.target.value)} maxLength={280} />}
      </Field>
    </Sheet>
  );
}

// ------------------------------------------------------------------ Kurzumfrage

export function Survey() {
  const db = useDb();
  const me = useMe()!;
  const toast = useToast();
  const survey = db.surveys.find((s) => s.status === 'open');
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Record<string, string>>({});

  if (!survey || me.surveysAnswered.includes(survey.id)) {
    return (
      <Page>
        <BackHeader />
        <div className="flex flex-col items-center pt-10 text-center">
          <span className="flex size-20 items-center justify-center rounded-full bg-success-soft text-success">
            <CircleCheck className="size-10" aria-hidden />
          </span>
          <h1 className="mt-4 text-[26px] font-extrabold">Danke fürs Mitmachen!</h1>
          <p className="mt-2 max-w-sm text-ink-2">{survey ? 'Du hast die aktuelle Kurzumfrage schon beantwortet. Die nächste kommt im neuen Quartal.' : 'Gerade läuft keine Umfrage.'}</p>
        </div>
      </Page>
    );
  }
  const complete = survey.questions.every((q) => answers[q.id]);
  return (
    <Page>
      <BackHeader />
      <LargeTitle title="Kurzumfrage" eyebrow={survey.quarter} subtitle="Drei kurze Fragen zum Freizeitangebot. Anonym – deine Antworten werden nicht mit deinem Namen gespeichert." />
      <div className="space-y-4">
        {survey.questions.map((q, i) => (
          <Card key={q.id} as="section" aria-labelledby={`q-${q.id}`}>
            <p className="text-[12px] font-bold uppercase tracking-wide text-muted">Frage {i + 1} von 3</p>
            <h2 id={`q-${q.id}`} className="mt-1 text-[17px] font-bold leading-snug">
              {q.text}
            </h2>
            <div role="radiogroup" aria-labelledby={`q-${q.id}`} className="mt-3 flex justify-between gap-1">
              {[1, 2, 3, 4, 5].map((n) => {
                const active = (answers[q.id] ?? 0) >= n;
                return (
                  <button
                    key={n}
                    type="button"
                    role="radio"
                    aria-checked={answers[q.id] === n}
                    aria-label={`${n} von 5 Sternen`}
                    onClick={() => setAnswers({ ...answers, [q.id]: n })}
                    className="press flex size-14 items-center justify-center rounded-[16px] hover:bg-surface-2"
                  >
                    <Star className={cx('size-9', active ? 'text-warn' : 'text-surface-3')} fill={active ? 'currentColor' : 'none'} strokeWidth={1.5} aria-hidden />
                  </button>
                );
              })}
            </div>
            <div className="mt-1 flex justify-between px-2 text-[12px] text-muted" aria-hidden>
              <span>gar nicht</span>
              <span>sehr</span>
            </div>
            <label className="sr-only" htmlFor={`c-${q.id}`}>
              Kommentar zu Frage {i + 1} (optional)
            </label>
            <textarea
              id={`c-${q.id}`}
              className={inputCls + ' mt-3 min-h-12 py-3 text-[15px]'}
              placeholder="Möchtest du etwas ergänzen? (optional)"
              value={comments[q.id] ?? ''}
              maxLength={300}
              onChange={(e) => setComments({ ...comments, [q.id]: e.target.value })}
            />
          </Card>
        ))}
      </div>
      <Button
        size="lg"
        block
        className="mt-5"
        disabled={!complete}
        onClick={async () => {
          await api.submitSurvey(me.id, survey.id, answers, Object.fromEntries(Object.entries(comments).filter(([, v]) => v.trim())));
          toast('Danke! Deine Antworten wurden anonym gespeichert.');
        }}
      >
        Absenden
      </Button>
    </Page>
  );
}

// ------------------------------------------------------------------ Meine Daten

export function MyData() {
  const db = useDb();
  const me = useMe()!;
  const navigate = useNavigate();
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const site = db.sites.find((s) => s.id === me.siteId)!;
  const checkins = db.checkins.filter((c) => c.personId === me.id);
  const regs = db.events.filter((e) => e.registered.includes(me.id) || e.waitlist.includes(me.id)).length;
  const ideas = db.ideas.filter((i) => i.authorId === me.id).length;
  const votes = db.ideas.filter((i) => i.votes.includes(me.id)).length;
  const deleteAt = new Date(Date.parse(me.programEnd) + db.settings.deleteAfterDays * 86_400_000);

  const rows: [string, string][] = [
    ['Spitzname', me.nickname],
    ['Standort', site.name],
    ['Haus / Etage', me.subgroup ?? '–'],
    ['Check-ins', `${checkins.length} (Ort, Zeit, Punkte)`],
    ['Event-Anmeldungen', String(regs)],
    ['Eigene Ideen / Stimmen', `${ideas} / ${votes}`],
    ['Einzel-Rangliste', me.leaderboardOptIn ? 'sichtbar' : 'nicht sichtbar'],
    ['Benachrichtigungen', me.notifications ? 'an' : 'aus'],
  ];

  return (
    <Page>
      <BackHeader />
      <LargeTitle title="Meine Daten" subtitle="Das ist alles, was INNmotion über dich speichert." />
      <Card className="p-0">
        <dl>
          {rows.map(([k, v]) => (
            <div key={k} className="flex min-h-12 items-center justify-between gap-3 border-t border-line px-4 py-2.5 first:border-t-0">
              <dt className="text-[14px] text-muted">{k}</dt>
              <dd className="text-right text-[15px] font-semibold">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>
      <SectionHeader title="Was wir nicht speichern" />
      <Card>
        <ul className="space-y-2 text-[14px] text-ink-2">
          {['Keinen Klarnamen', 'Keine Gesundheits- oder Körperdaten (Gewicht, Puls, Schritte)', 'Keinen Standort / kein GPS', 'Keine Fotos – die Kamera liest nur den Code', 'Umfrage-Antworten nur anonym'].map((t) => (
            <li key={t} className="flex items-start gap-2">
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden /> {t}
            </li>
          ))}
        </ul>
      </Card>
      <p className="mt-4 px-1 text-[13px] text-muted">
        Dein Konto wird automatisch {db.settings.deleteAfterDays} Tage nach deinem Maßnahmeende gelöscht (voraussichtlich am {deleteAt.toLocaleDateString('de-DE')}).
      </p>
      <Button variant="danger" block size="lg" className="mt-5" icon={<Trash2 className="size-5" />} onClick={() => setConfirm(true)}>
        Konto löschen
      </Button>
      <Sheet
        open={confirm}
        onClose={() => setConfirm(false)}
        title="Konto wirklich löschen?"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" block onClick={() => setConfirm(false)}>
              Abbrechen
            </Button>
            <Button
              variant="danger"
              block
              onClick={async () => {
                await api.deleteAccount(me.id);
                setConfirm(false);
                toast('Dein Konto wurde gelöscht.');
                navigate('/profil');
              }}
            >
              Endgültig löschen
            </Button>
          </div>
        }
      >
        <p className="text-[15px] text-ink-2">Alle deine Check-ins, Anmeldungen und Stimmen werden entfernt. Deine Punkte zählen dann nicht mehr für dein Team. Das kann nicht rückgängig gemacht werden.</p>
      </Sheet>
    </Page>
  );
}

