import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import { useDb, useNow } from '../../services/hooks';
import { placeCode, prettyCode, qrPayload } from '../../domain/codes';
import type { Place } from '../../domain/types';
import { useQrSvg } from '../staff/Code';
import { Button } from '../../components/ui';

/** Druckvorlage: Tages-QR-Codes zum Aushängen an Fitnessraum und Halle (gültig nur heute). */
export function Poster() {
  const { siteId } = useParams();
  const db = useDb();
  const navigate = useNavigate();
  const site = db.sites.find((s) => s.id === siteId) ?? db.sites[0];
  const places = db.places.filter((p) => p.siteId === site.id && p.active);
  return (
    <div className="min-h-dvh bg-white text-[#0B0D10]">
      <div className="mx-auto flex max-w-xl items-center justify-between gap-3 p-4 print:hidden">
        <button type="button" onClick={() => navigate(-1)} aria-label="Zurück" className="press flex size-12 items-center justify-center rounded-full bg-black/5">
          <ArrowLeft className="size-5" aria-hidden />
        </button>
        <Button icon={<Printer className="size-5" />} onClick={() => window.print()}>
          Drucken
        </Button>
      </div>
      {places.map((p) => (
        <PosterPage key={p.id} place={p} siteName={site.name} />
      ))}
    </div>
  );
}

function PosterPage({ place, siteName }: { place: Place; siteName: string }) {
  const db = useDb();
  const now = useNow();
  const code = placeCode(db.codeSecret, place.id, now);
  const svg = useQrSvg(qrPayload('P', place.id, code));
  return (
    <section className="mx-auto flex max-w-xl flex-col items-center px-6 pb-16 pt-6 text-center [break-after:page]">
      <p className="text-[15px] font-bold uppercase tracking-widest text-black/55">INNmotion · {siteName}</p>
      <h1 className="mt-1 text-[40px] font-black leading-tight">{place.name}</h1>
      <p className="mt-1 text-[18px]">Einchecken und Punkte für dein Team sammeln</p>
      <div className="mt-6 aspect-square w-full max-w-[360px] [&_svg]:size-full" role="img" aria-label={`QR-Code ${place.name}`} dangerouslySetInnerHTML={{ __html: svg }} />
      <p className="mt-4 text-[15px] text-black/60">oder Code eingeben</p>
      <p className="tnum font-mono text-[48px] font-black tracking-[0.15em]">{prettyCode(code)}</p>
      <p className="mt-2 text-[14px] text-black/55">Gültig am {now.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
    </section>
  );
}
