import { useState } from 'react';
import { Crown, Minus, Plus, Trophy } from 'lucide-react';
import { useDb } from '../services/hooks';
import { api } from '../services/mock/mockApi';
import { champion, groupTable, isPlayed, matchWinner, resolveSlot, slotLabel } from '../domain/tournament';
import type { Match, Tournament } from '../domain/types';
import { Button, Card, Chip, Sheet, TeamBadge, cx, useToast } from './ui';
import { TEAM_CLASSES } from '../theme/teams';

/** Gruppen-Tabellen und K.-o.-Runde. Mit `editable` kann die Betreuung Ergebnisse eintragen. */
export function TournamentView({ t, editable }: { t: Tournament; editable?: boolean }) {
  const db = useDb();
  const [edit, setEdit] = useState<Match | null>(null);
  const champ = champion(t);
  const champPlayer = t.players.find((p) => p.id === champ);
  const siteOf = (playerId: string | null | 'bye') => db.sites.find((s) => s.id === t.players.find((p) => p.id === playerId)?.siteId);
  const rounds = [...new Set(t.matches.filter((m) => m.stage === 'ko').map((m) => m.round ?? 0))].sort((a, b) => a - b);

  return (
    <div className="space-y-4">
      {champPlayer && (
        <Card className="flex items-center gap-3 bg-gradient-to-r from-warn-soft to-surface">
          <span className="flex size-12 items-center justify-center rounded-full bg-warn text-white dark:text-black">
            <Crown className="size-6" aria-hidden />
          </span>
          <div>
            <p className="text-[12px] font-bold uppercase tracking-wider text-warn">Turniersieg</p>
            <p className="text-[18px] font-extrabold">{champPlayer.name}</p>
          </div>
          {siteOf(champPlayer.id) && (
            <span className="ml-auto">
              <TeamBadge site={siteOf(champPlayer.id)!} size="sm" withName={false} />
            </span>
          )}
        </Card>
      )}

      {t.groups.map((g) => {
        const table = groupTable(t, g.name);
        const matches = t.matches.filter((m) => m.stage === 'group' && m.group === g.name);
        return (
          <Card key={g.name} className="p-0">
            <h3 className="px-4 pb-1 pt-4 text-[16px] font-bold">Gruppe {g.name}</h3>
            <table className="w-full text-[14px]">
              <caption className="sr-only">Tabelle Gruppe {g.name}</caption>
              <thead>
                <tr className="text-[12px] text-muted">
                  <th scope="col" className="w-8 py-2 pl-4 text-left font-semibold">#</th>
                  <th scope="col" className="py-2 text-left font-semibold">Name</th>
                  <th scope="col" className="py-2 text-center font-semibold" title="Spiele"><abbr title="Spiele" className="no-underline">Sp</abbr></th>
                  <th scope="col" className="py-2 text-center font-semibold">{t.scoreUnit}</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold"><abbr title="Punkte" className="no-underline">Pkt</abbr></th>
                </tr>
              </thead>
              <tbody>
                {table.map((r) => {
                  const site = siteOf(r.player.id);
                  return (
                    <tr key={r.player.id} className="border-t border-line">
                      <td className="tnum py-2.5 pl-4 font-bold text-muted">{r.rank}</td>
                      <th scope="row" className="py-2.5 text-left font-semibold">
                        <span className="flex min-w-0 items-center gap-2">
                          {site && <span className={cx('inline-block size-2.5 shrink-0 rounded-full', TEAM_CLASSES[site.team].bg)} aria-hidden />}
                          <span className="truncate">{r.player.name}</span>
                          {site && <span className="text-[11px] font-semibold text-muted">{site.short}</span>}
                        </span>
                      </th>
                      <td className="tnum py-2.5 text-center">{r.played}</td>
                      <td className="tnum py-2.5 text-center">
                        {r.scoreFor}:{r.scoreAgainst}
                      </td>
                      <td className="tnum py-2.5 pr-4 text-right font-bold">{r.points}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <ul className="border-t border-line px-2 py-2">
              {matches.map((m) => (
                <MatchRow key={m.id} t={t} m={m} onEdit={editable ? () => setEdit(m) : undefined} />
              ))}
            </ul>
          </Card>
        );
      })}

      {rounds.length > 0 && (
        <Card className="p-0">
          <h3 className="flex items-center gap-2 px-4 pb-1 pt-4 text-[16px] font-bold">
            <Trophy className="size-4 text-muted" aria-hidden /> K.-o.-Runde
          </h3>
          {rounds.map((r) => (
            <ul key={r} className="border-t border-line px-2 py-2 first-of-type:border-t-0">
              {t.matches
                .filter((m) => m.stage === 'ko' && m.round === r)
                .map((m) => (
                  <MatchRow key={m.id} t={t} m={m} showLabel onEdit={editable ? () => setEdit(m) : undefined} />
                ))}
            </ul>
          ))}
        </Card>
      )}
      {edit && <ResultSheet t={t} m={edit} onClose={() => setEdit(null)} />}
    </div>
  );
}

function MatchRow({ t, m, onEdit, showLabel }: { t: Tournament; m: Match; onEdit?: () => void; showLabel?: boolean }) {
  const a = resolveSlot(t, m.a);
  const b = resolveSlot(t, m.b);
  const ready = a && b && a !== 'bye' && b !== 'bye';
  const winner = matchWinner(t, m);
  const played = isPlayed(m);
  const content = (
    <>
      {showLabel && <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-muted">{m.label}</span>}
      <span className="flex items-center gap-2">
        <span className={cx('min-w-0 flex-1 truncate text-right text-[14px]', winner && winner === a ? 'font-bold text-ink' : 'text-ink-2')}>{slotLabel(t, m.a)}</span>
        <span className={cx('tnum shrink-0 rounded-[8px] px-2 py-0.5 text-[14px] font-bold', played ? 'bg-surface-2 text-ink' : 'text-muted')}>{played ? `${m.scoreA} : ${m.scoreB}` : '– : –'}</span>
        <span className={cx('min-w-0 flex-1 truncate text-[14px]', winner && winner === b ? 'font-bold text-ink' : 'text-ink-2')}>{slotLabel(t, m.b)}</span>
      </span>
    </>
  );
  if (onEdit && ready) {
    return (
      <li>
        <button type="button" onClick={onEdit} className="press block min-h-12 w-full rounded-[12px] px-2 py-2 text-left hover:bg-surface-2" aria-label={`Ergebnis eintragen: ${slotLabel(t, m.a)} gegen ${slotLabel(t, m.b)}`}>
          {content}
        </button>
      </li>
    );
  }
  return <li className="px-2 py-2">{content}</li>;
}

function ResultSheet({ t, m, onClose }: { t: Tournament; m: Match; onClose: () => void }) {
  const [a, setA] = useState(m.scoreA ?? 0);
  const [b, setB] = useState(m.scoreB ?? 0);
  const toast = useToast();
  const isKo = m.stage === 'ko';
  return (
    <Sheet
      open
      onClose={onClose}
      title="Ergebnis eintragen"
      footer={
        <div className="flex gap-3">
          {isPlayed(m) && (
            <Button
              variant="secondary"
              onClick={async () => {
                await api.recordResult(t.id, m.id, undefined, undefined);
                onClose();
              }}
            >
              Löschen
            </Button>
          )}
          <Button
            block
            disabled={isKo && a === b}
            onClick={async () => {
              await api.recordResult(t.id, m.id, a, b);
              toast('Ergebnis gespeichert. Die Tabelle ist aktualisiert.');
              onClose();
            }}
          >
            Speichern
          </Button>
        </div>
      }
    >
      {m.label && <Chip className="mb-3">{m.label}</Chip>}
      <div className="grid grid-cols-2 gap-3">
        <Stepper label={slotLabel(t, m.a)} value={a} onChange={setA} />
        <Stepper label={slotLabel(t, m.b)} value={b} onChange={setB} />
      </div>
      <p className="mt-3 text-center text-[13px] text-muted">
        {t.scoreUnit}
        {isKo && a === b ? ' · In der K.-o.-Runde braucht es einen Sieger.' : ''}
      </p>
    </Sheet>
  );
}

function Stepper({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex flex-col items-center rounded-[20px] bg-surface-2 p-3">
      <p className="w-full truncate text-center text-[15px] font-bold">{label}</p>
      <p className="tnum my-2 text-[44px] font-extrabold leading-none" aria-live="polite">
        {value}
      </p>
      <div className="flex gap-2">
        <button type="button" aria-label={`${label}: weniger`} onClick={() => onChange(Math.max(0, value - 1))} className="press flex size-12 items-center justify-center rounded-full bg-surface text-ink">
          <Minus className="size-5" aria-hidden />
        </button>
        <button type="button" aria-label={`${label}: mehr`} onClick={() => onChange(Math.min(99, value + 1))} className="press flex size-12 items-center justify-center rounded-full bg-accent text-accent-ink">
          <Plus className="size-5" aria-hidden />
        </button>
      </div>
    </div>
  );
}
