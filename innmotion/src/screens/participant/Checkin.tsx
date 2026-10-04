import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CircleAlert, Keyboard, ScanLine, X } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useMe, useReducedMotion } from '../../services/hooks';
import type { CheckinResponse, CheckinSuccess } from '../../services/api';
import { normalizeManual } from '../../domain/codes';
import { QrScanner } from '../../components/QrScanner';
import { Button, cx } from '../../components/ui';
import { DynIcon } from '../../components/DynIcon';

/** Check-in: QR-Code scannen oder Code eintippen. Erreichbar mit einem Tap von „Start“. */
export function Checkin() {
  const me = useMe()!;
  const navigate = useNavigate();
  const [mode, setMode] = useState<'scan' | 'code'>('scan');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<CheckinSuccess | null>(null);
  const lastScan = useRef<{ text: string; at: number } | null>(null);

  const submit = useCallback(
    async (raw: string, source: 'qr' | 'code') => {
      setBusy(true);
      const r: CheckinResponse = await api.checkIn(me.id, raw, source);
      setBusy(false);
      if (r.ok) {
        setError(null);
        setSuccess(r);
        navigator.vibrate?.(30);
      } else setError(r.reason);
    },
    [me.id],
  );

  const onScan = useCallback(
    (text: string) => {
      // Denselben Code nicht mehrfach hintereinander auswerten
      const now = Date.now();
      if (busy || success || (lastScan.current && lastScan.current.text === text && now - lastScan.current.at < 4000)) return;
      lastScan.current = { text, at: now };
      void submit(text, 'qr');
    },
    [busy, success, submit],
  );

  if (success) return <Celebration result={success} onDone={() => navigate('/')} />;

  return (
    <div className="dark min-h-dvh bg-[#06080a] pt-safe text-white">
      <div className="mx-auto flex min-h-dvh max-w-xl flex-col px-4 pb-6">
        <header className="flex items-center justify-between py-3">
          <button type="button" onClick={() => navigate(-1)} aria-label="Schließen" className="press flex size-12 items-center justify-center rounded-full bg-white/10">
            <X className="size-6" aria-hidden />
          </button>
          <h1 className="text-[18px] font-bold">Einchecken</h1>
          <span className="size-12" aria-hidden />
        </header>

        <div role="tablist" aria-label="Art des Check-ins" className="mb-5 flex gap-1 rounded-pill bg-white/10 p-1">
          {(
            [
              ['scan', 'QR scannen', ScanLine],
              ['code', 'Code eingeben', Keyboard],
            ] as const
          ).map(([m, label, Icon]) => (
            <button
              key={m}
              role="tab"
              type="button"
              aria-selected={mode === m}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={cx('press flex min-h-12 flex-1 items-center justify-center gap-2 rounded-pill text-[15px] font-semibold', mode === m ? 'bg-white text-black' : 'text-white/75')}
            >
              <Icon className="size-[18px]" aria-hidden /> {label}
            </button>
          ))}
        </div>

        {mode === 'scan' ? (
          <>
            <QrScanner onResult={onScan} paused={busy} />
            <p className="mt-4 text-center text-[15px] leading-relaxed text-white/80">
              Halte die Kamera auf den QR-Code am Fitnessraum, an der Halle oder auf dem Handy der Betreuung.
            </p>
          </>
        ) : (
          <form
            className="flex flex-col"
            onSubmit={(e) => {
              e.preventDefault();
              if (code.length === 6) void submit(code, 'code');
            }}
          >
            <label htmlFor="manual-code" className="mb-3 text-center text-[15px] text-white/80">
              Gib den 6-stelligen Code ein. Er steht unter dem QR-Code.
            </label>
            <input
              id="manual-code"
              value={code.length > 3 ? `${code.slice(0, 3)} ${code.slice(3)}` : code}
              onChange={(e) => {
                setCode(normalizeManual(e.target.value).slice(0, 6));
                setError(null);
              }}
              inputMode="text"
              autoCapitalize="characters"
              autoComplete="one-time-code"
              autoFocus
              spellCheck={false}
              placeholder="ABC 123"
              aria-describedby={error ? 'checkin-error' : undefined}
              className="tnum h-20 w-full rounded-[22px] border-2 border-white/15 bg-white/5 text-center font-mono text-[36px] font-bold tracking-[0.25em] text-white placeholder:text-white/25 focus:border-[#2dd4bf] focus:outline-none"
            />
            <Button type="submit" size="lg" block className="mt-4" disabled={code.length !== 6 || busy}>
              {busy ? 'Wird geprüft …' : 'Einchecken'}
            </Button>
          </form>
        )}

        {error && (
          <div id="checkin-error" role="alert" className="anim-rise mt-5 flex items-start gap-3 rounded-[20px] bg-[#ff6b6f]/15 p-4 text-[15px] text-[#ffb3b5]">
            <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-auto pt-6 text-center text-[13px] text-white/55">
          Keine Standortdaten, keine Fotos – die Kamera erkennt nur den Code.
        </div>
      </div>
    </div>
  );
}

function useCountUp(target: number, enabled: boolean) {
  const [v, setV] = useState(enabled ? 0 : target);
  useEffect(() => {
    if (!enabled) return setV(target);
    const start = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - start) / 900);
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, enabled]);
  return v;
}

function Celebration({ result, onDone }: { result: CheckinSuccess; onDone: () => void }) {
  const reduced = useReducedMotion();
  const points = useCountUp(result.points, !reduced);
  return (
    <div className="dark min-h-dvh bg-[#06080a] pt-safe text-white">
      <div className="mx-auto flex min-h-dvh max-w-xl flex-col items-center px-5 pb-6 text-center">
        <div className="relative mt-14 flex size-44 items-center justify-center" aria-hidden>
          <div className="anim-burst absolute inset-0 rounded-full border-4 border-[#2dd4bf]" />
          <div className="anim-pop flex size-44 items-center justify-center rounded-full bg-gradient-to-br from-[#2dd4bf] to-[#c6f432] shadow-[0_0_60px_rgba(45,212,191,0.45)]">
            <span className="tnum text-[56px] font-black text-[#042420]">+{points}</span>
          </div>
        </div>
        <div role="status">
          <h1 className="anim-rise mt-8 text-[30px] font-extrabold tracking-tight">Eingecheckt!</h1>
          <p className="anim-rise mt-1 text-[17px] text-white/80">
            {result.label} · {result.points} Punkte für dein Team
          </p>
        </div>
        {result.weeklyGoalReached && (
          <p className="anim-rise mt-4 rounded-pill bg-[#c6f432]/15 px-4 py-2 text-[15px] font-bold text-[#c6f432]">Wochenziel geschafft!</p>
        )}
        {result.buddyName && <p className="anim-rise mt-3 text-[15px] text-white/80">Zusammen mit {result.buddyName} eingecheckt – ihr bekommt beide einen Bonus.</p>}

        <ul className="anim-rise mt-6 w-full space-y-1.5 rounded-[22px] bg-white/[0.06] p-4 text-left">
          {result.breakdown.map((b, i) => (
            <li key={i} className="flex items-center justify-between gap-3 text-[15px]">
              <span className="text-white/80">{b.label}</span>
              <span className={cx('tnum font-bold', b.points < 0 ? 'text-[#fbbf24]' : 'text-[#5eead4]')}>
                {b.points > 0 ? '+' : ''}
                {b.points}
              </span>
            </li>
          ))}
        </ul>

        {result.newBadges.map((b) => (
          <div key={b.id} className="anim-pop mt-4 flex w-full items-center gap-4 rounded-[22px] bg-gradient-to-r from-[#c6f432]/20 to-[#2dd4bf]/10 p-4 text-left">
            <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-[#c6f432] text-[#1a2400]">
              <DynIcon name={b.icon} className="size-7" />
            </span>
            <div>
              <p className="text-[12px] font-bold uppercase tracking-wider text-[#c6f432]">Neues Abzeichen</p>
              <p className="text-[18px] font-extrabold">{b.title}</p>
            </div>
          </div>
        ))}

        <div className="mt-auto w-full pt-8">
          <Button size="lg" block onClick={onDone}>
            Fertig
          </Button>
        </div>
      </div>
    </div>
  );
}
