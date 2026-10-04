import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Swords, Trash2, Trophy } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe } from '../../services/hooks';
import { champion, isPlayed } from '../../domain/tournament';
import type { Tournament } from '../../domain/types';
import { Button, Card, Chip, EmptyState, Field, inputCls, LargeTitle, Page, Segmented, Sheet, useToast } from '../../components/ui';
import { TournamentView } from '../../components/TournamentView';
import { BackHeader } from '../participant/ProfilePages';

export function StaffTournaments() {
  const db = useDb();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  return (
    <Page>
      <LargeTitle
        title="Turniere"
        subtitle="Standortübergreifend. Ergebnisse eintragen – die Tabelle rechnet sich selbst."
        trailing={
          <Button icon={<Plus className="size-5" />} onClick={() => setOpen(true)}>
            Neu
          </Button>
        }
      />
      {db.tournaments.length === 0 && <EmptyState icon={<Swords />} title="Noch keine Turniere" />}
      <ul className="space-y-3">
        {db.tournaments.map((t) => {
          const played = t.matches.filter(isPlayed).length;
          const champ = t.players.find((p) => p.id === champion(t));
          return (
            <li key={t.id}>
              <button type="button" onClick={() => navigate(`/betreuung/turnier/${t.id}`)} className="press block w-full text-left">
                <Card className="flex items-center gap-3">
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-[14px] bg-accent-soft text-accent">
                    {t.status === 'done' ? <Trophy className="size-6" aria-hidden /> : <Swords className="size-6" aria-hidden />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-bold">{t.title}</p>
                    <p className="text-[13px] text-muted">
                      {t.players.length} Teilnehmende · {played}/{t.matches.length} Spiele
                      {champ ? ` · Sieg: ${champ.name}` : ''}
                    </p>
                  </div>
                  <Chip tone={t.status === 'running' ? 'success' : 'neutral'}>{t.status === 'running' ? 'Läuft' : 'Beendet'}</Chip>
                </Card>
              </button>
            </li>
          );
        })}
      </ul>
      <NewTournamentSheet open={open} onClose={() => setOpen(false)} />
    </Page>
  );
}

export function StaffTournamentDetail() {
  const { id } = useParams();
  const db = useDb();
  const toast = useToast();
  const t = db.tournaments.find((x) => x.id === id);
  if (!t) return <Page><BackHeader /><EmptyState icon={<Swords />} title="Turnier nicht gefunden" /></Page>;
  const done = !!champion(t);
  return (
    <Page>
      <BackHeader />
      <LargeTitle title={t.title} subtitle={`${t.sport} · ${t.format === 'groups' ? 'Gruppen + K.-o.' : 'K.-o.-System'} · Tippe auf ein Spiel, um das Ergebnis einzutragen.`} />
      <TournamentView t={t} editable={t.status === 'running'} />
      {t.status === 'running' && (
        <Button
          size="lg"
          block
          className="mt-5"
          disabled={!done}
          onClick={async () => {
            await api.finishTournament(t.id);
            toast('Turnier abgeschlossen. Abzeichen wurden vergeben.');
          }}
        >
          {done ? 'Turnier abschließen' : 'Abschließen, sobald das Finale gespielt ist'}
        </Button>
      )}
    </Page>
  );
}

function NewTournamentSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const db = useDb();
  const me = useMe()!;
  const navigate = useNavigate();
  const toast = useToast();
  const [title, setTitle] = useState('');
  const [sport, setSport] = useState('Darts');
  const [format, setFormat] = useState<Tournament['format']>('knockout');
  const [players, setPlayers] = useState<{ name: string; personId?: string; siteId: string }[]>([]);
  const [pick, setPick] = useState('');
  const candidates = db.persons.filter((p) => p.role === 'participant' && !players.some((x) => x.personId === p.id));

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Neues Turnier"
      footer={
        <Button
          block
          disabled={title.trim().length < 3 || players.length < 3}
          onClick={async () => {
            const t = await api.createTournament({ title: title.trim(), sport: sport.trim(), format, scoreUnit: sport === 'Darts' ? 'Legs' : 'Sätze', players, groupCount: players.length >= 8 ? 2 : 1 });
            toast('Turnier angelegt. Spielplan ist erstellt.');
            onClose();
            navigate(`/betreuung/turnier/${t.id}`);
          }}
        >
          Spielplan erstellen ({players.length} Teilnehmende)
        </Button>
      }
    >
      <Field label="Titel">{(id) => <input id={id} className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z. B. Darts-Wintercup" />}</Field>
      <Field label="Sportart">{(id) => <input id={id} className={inputCls} value={sport} onChange={(e) => setSport(e.target.value)} />}</Field>
      <div className="mb-4">
        <p className="mb-1.5 text-[14px] font-semibold text-ink-2">Modus</p>
        <Segmented label="Modus" value={format} onChange={setFormat} options={[{ value: 'knockout', label: 'K.-o.-Baum' }, { value: 'groups', label: 'Gruppen + K.-o.' }]} />
      </div>
      <Field label="Teilnehmende hinzufügen" hint="Aus allen Standorten. Auch Teams sind möglich – dann einen Teamnamen vergeben.">
        {(id) => (
          <div className="flex gap-2">
            <select id={id} className={inputCls} value={pick} onChange={(e) => setPick(e.target.value)}>
              <option value="">Person wählen …</option>
              {db.sites.map((s) => (
                <optgroup key={s.id} label={s.name}>
                  {candidates
                    .filter((p) => p.siteId === s.id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nickname}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            <Button
              variant="soft"
              aria-label="Hinzufügen"
              disabled={!pick}
              onClick={() => {
                const p = db.persons.find((x) => x.id === pick)!;
                setPlayers([...players, { name: p.nickname, personId: p.id, siteId: p.siteId }]);
                setPick('');
              }}
            >
              <Plus className="size-5" aria-hidden />
            </Button>
          </div>
        )}
      </Field>
      <Button
        variant="secondary"
        size="sm"
        className="mb-3"
        onClick={() => setPlayers([...players, { name: `Team ${players.length + 1}`, siteId: me.siteId }])}
      >
        Team ohne Personenbezug hinzufügen
      </Button>
      <ul className="space-y-1.5">
        {players.map((p, i) => (
          <li key={i} className="flex min-h-12 items-center gap-2 rounded-[14px] bg-surface-2 pl-3">
            <span className="tnum text-[13px] text-muted">{i + 1}.</span>
            <span className="flex-1 truncate font-semibold">{p.name}</span>
            <span className="text-[12px] text-muted">{db.sites.find((s) => s.id === p.siteId)?.short}</span>
            <button type="button" aria-label={`${p.name} entfernen`} onClick={() => setPlayers(players.filter((_, j) => j !== i))} className="press flex size-11 items-center justify-center text-muted">
              <Trash2 className="size-4" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </Sheet>
  );
}
