import { useEffect, useRef, useState } from 'react';
import jsQR from 'jsqr';
import { CameraOff } from 'lucide-react';

type ScanState = 'starting' | 'scanning' | 'denied' | 'unavailable';

/**
 * QR-Scanner über die Kamera. Läuft komplett im Browser (jsQR, lokal gebündelt) – es wird nichts hochgeladen.
 * Funktioniert auf iOS-Safari und Android-Chrome; Kamera-Zugriff braucht HTTPS oder localhost.
 */
export function QrScanner({ onResult, paused }: { onResult: (text: string) => void; paused?: boolean }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, setState] = useState<ScanState>('starting');
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    let stream: MediaStream | undefined;
    let raf = 0;
    let stopped = false;
    let last = 0;

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setState('unavailable');
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      } catch (e) {
        setState((e as DOMException)?.name === 'NotAllowedError' ? 'denied' : 'unavailable');
        return;
      }
      if (stopped) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      const video = videoRef.current!;
      video.srcObject = stream;
      video.setAttribute('playsinline', 'true');
      await video.play().catch(() => {});
      setState('scanning');
      const tick = (t: number) => {
        if (stopped) return;
        raf = requestAnimationFrame(tick);
        if (pausedRef.current || t - last < 120 || video.readyState < 2) return;
        last = t;
        const canvas = canvasRef.current!;
        // Für die Erkennung verkleinern – spart Akku, reicht für Aushänge und Handy-Displays.
        const scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx || !canvas.width) return;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(img.data, img.width, img.height, { inversionAttempts: 'attemptBoth' });
        if (code?.data) onResultRef.current(code.data);
      };
      raf = requestAnimationFrame(tick);
    }
    void start();
    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-[28px] bg-black">
      <video ref={videoRef} className="absolute inset-0 size-full object-cover" muted playsInline aria-label="Kamerabild zum Scannen" />
      <canvas ref={canvasRef} className="hidden" aria-hidden />
      {state === 'scanning' && (
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          <div className="absolute inset-[14%] rounded-[24px] shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]" />
          {[
            'left-[14%] top-[14%] border-l-4 border-t-4 rounded-tl-[24px]',
            'right-[14%] top-[14%] border-r-4 border-t-4 rounded-tr-[24px]',
            'left-[14%] bottom-[14%] border-l-4 border-b-4 rounded-bl-[24px]',
            'right-[14%] bottom-[14%] border-r-4 border-b-4 rounded-br-[24px]',
          ].map((c) => (
            <div key={c} className={`absolute size-12 border-[#2dd4bf] ${c}`} />
          ))}
          <div className="absolute inset-x-[18%] top-[16%] h-[68%] [--scan-h:100%]">
            <div className="anim-scan h-1 rounded-full bg-[#2dd4bf] shadow-[0_0_16px_4px_rgba(45,212,191,0.6)]" />
          </div>
        </div>
      )}
      {state === 'starting' && <p className="absolute inset-0 flex items-center justify-center text-[15px] text-white/80">Kamera wird gestartet …</p>}
      {(state === 'denied' || state === 'unavailable') && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8 text-center text-white" role="alert">
          <CameraOff className="size-10 text-white/70" aria-hidden />
          <p className="text-[17px] font-semibold">{state === 'denied' ? 'Kein Zugriff auf die Kamera' : 'Kamera nicht verfügbar'}</p>
          <p className="text-[14px] text-white/75">
            {state === 'denied' ? 'Erlaube den Kamera-Zugriff in den Browser-Einstellungen – oder gib den Code einfach von Hand ein.' : 'Gib den Code einfach von Hand ein. Er steht unter jedem QR-Code.'}
          </p>
        </div>
      )}
    </div>
  );
}
