import { useEffect, useMemo, useState } from 'react';
import QRCode from 'qrcode';
import { Maximize2, X } from 'lucide-react';
import { useDb, useMe, useNow } from '../../services/hooks';
import { eventCode, placeCode, prettyCode, qrPayload, ROTATION_MS } from '../../domain/codes';
import { eventWindowOpen } from '../../domain/checkin';
import { fmt } from '../../domain/time';
import { Button, Card, Chip, LargeTitle, Page, cx } from '../../components/ui';

type Target = { kind: 'P' | 'E'; id: string; label: string; sub: string; code: string };

export function useQrSvg(text: string) {
  const [svg, setSvg] = useState('');
  useEffect(() => {
    let alive = true;
    QRCode.toString(text, { type: 'svg', margin: 1, errorCorrectionLevel: 'M', color: { dark: '#0B0D10', light: '#FFFFFF' } }).then((s) => alive && setSvg(s));
    return () => {
      alive = false;
    };
  }, [text]);
  return svg;
}

/** Check-in-Code anzeigen: rotierender QR-Code (alle 30 s neu) + täglicher Code zum Eintippen. */
export function StaffCode() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow(1000);
  const site = db.sites.find((s) => s.id === me.siteId)!;

  const targets: Target[] = useMemo(() => {
    const places = db.places
      .filter((p) => p.siteId === me.siteId && p.active)
      .map((p) => ({ kind: 'P' as const, id: p.id, label: p.name, sub: 'Tagescode', code: placeCode(db.codeSecret, p.id, now) }));
    const events = db.events
      .filter((e) => e.siteId === me.siteId && eventWindowOpen(e, now))
      .map((e) => ({ kind: 'E' as const, id: e.id, label: e.title, sub: `Event bis ${fmt.time(e.end)} Uhr`, code: eventCode(db.codeSecret, e.id) }));
    return [...events, ...places];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [db, me.siteId, now.toDateString(), Math.floor(now.getTime() / 60000)]);

  const [selected, setSelected] = useState<string>(() => targets[0]?.id ?? '');
  const [full, setFull] = useState(false);
  const target = targets.find((t) => t.id === selected) ?? targets[0];
  const slotStart = Math.floor(now.getTime() / ROTATION_MS) * ROTATION_MS;
  const payload = target ? qrPayload(target.kind, target.id, target.code, new Date(slotStart)) : '';
  const svg = useQrSvg(payload);
  const secondsLeft = Math.ceil((slotStart + ROTATION_MS - now.getTime()) / 1000);

  // Bildschirm im Vollbild-Modus wach halten (wo unterstützt)
  useEffect(() => {
    if (!full || !('wakeLock' in navigator)) return;
    let lock: WakeLockSentinel | undefined;
    navigator.wakeLock.request('screen').then((l) => (lock = l)).catch(() => {});
    return () => void lock?.release();
  }, [full]);

  if (!target) {
    return (
      <Page>
        <LargeTitle title="Check-in-Code" subtitle="Für diesen Standort sind keine Orte aktiv." />
      </Page>
    );
  }

  const qr = (
    <div className="relative mx-auto aspect-square w-full max-w-[340px] rounded-[24px] bg-white p-3" role="img" aria-label={`QR-Code für ${target.label}`}>
      <div className="size-full [&_svg]:size-full" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );

  return (
    <Page>
      <LargeTitle title="Check-in-Code" subtitle={`${site.name} · zeig den Code oder häng ihn aus.`} />
      <div className="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4" role="tablist" aria-label="Ort oder Event">
        {targets.map((t) => (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={t.id === target.id}
            onClick={() => setSelected(t.id)}
            className={cx('press min-h-12 shrink-0 rounded-pill px-4 text-[15px] font-semibold', t.id === target.id ? 'bg-ink text-bg' : 'bg-surface text-ink-2 shadow-card')}
          >
            {t.kind === 'E' && <span className="mr-1.5 inline-block size-2 rounded-full bg-success align-middle" aria-hidden />}
            {t.label}
          </button>
        ))}
      </div>

      <Card className="text-center">
        <div className="mb-3 flex items-center justify-center gap-2">
          <Chip tone={target.kind === 'E' ? 'success' : 'accent'}>{target.sub}</Chip>
          <Chip>neu in {secondsLeft} s</Chip>
        </div>
        {qr}
        <p className="mt-4 text-[13px] font-semibold uppercase tracking-wider text-muted">Code zum Eintippen</p>
        <p className="tnum mt-1 font-mono text-[40px] font-extrabold tracking-[0.15em]" aria-label={`Code ${target.code.split('').join(' ')}`}>
          {prettyCode(target.code)}
        </p>
        <Button size="lg" block className="mt-4" icon={<Maximize2 className="size-5" />} onClick={() => setFull(true)}>
          Vollbild zeigen
        </Button>
      </Card>
      <p className="mt-3 px-1 text-[13px] text-muted">
        Der QR-Code wechselt alle 30 Sekunden, damit Fotos davon schnell ungültig werden. Raum-Codes zum Eintippen wechseln täglich, Event-Codes gelten nur während des Events.
      </p>

      {full && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white p-6 text-[#0B0D10]" role="dialog" aria-modal="true" aria-label={`Vollbild-Code ${target.label}`}>
          <button type="button" onClick={() => setFull(false)} className="press absolute right-4 top-4 flex size-14 items-center justify-center rounded-full bg-black/5" aria-label="Vollbild schließen" autoFocus>
            <X className="size-7" aria-hidden />
          </button>
          <p className="text-[22px] font-extrabold">{target.label}</p>
          <p className="mb-4 text-[16px] text-black/60">Mit INNmotion scannen und Punkte sammeln</p>
          <div className="aspect-square w-full max-w-[min(90vw,70vh)] [&_svg]:size-full" dangerouslySetInnerHTML={{ __html: svg }} />
          <p className="tnum mt-4 font-mono text-[44px] font-extrabold tracking-[0.15em]">{prettyCode(target.code)}</p>
          <p className="text-[14px] text-black/55">QR-Code erneuert sich in {secondsLeft} s</p>
        </div>
      )}
    </Page>
  );
}
