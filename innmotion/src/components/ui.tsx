import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronRight, Info, X } from 'lucide-react';
import { TEAM_CLASSES } from '../theme/teams';
import type { Site } from '../domain/types';

export const cx = (...xs: (string | false | null | undefined)[]) => xs.filter(Boolean).join(' ');

// ------------------------------------------------------------------ Layout

export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx('mx-auto w-full max-w-xl px-4 pb-32 pt-2', className)}>{children}</div>;
}

export function LargeTitle({ title, subtitle, trailing, eyebrow }: { title: string; subtitle?: ReactNode; trailing?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <header className="mb-5 flex items-end justify-between gap-3 pt-3">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-[13px] font-semibold uppercase tracking-wider text-muted">{eyebrow}</div>}
        <h1 className="text-[32px] font-extrabold leading-[1.05] tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1.5 text-[15px] text-ink-2">{subtitle}</p>}
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </header>
  );
}

export function SectionHeader({ title, action, id }: { title: string; action?: ReactNode; id?: string }) {
  return (
    <div className="mb-3 mt-7 flex items-center justify-between gap-3">
      <h2 id={id} className="text-[20px] font-bold tracking-tight text-ink">
        {title}
      </h2>
      {action}
    </div>
  );
}

export function Card({ children, className, as: As = 'div', ...rest }: { children: ReactNode; className?: string; as?: 'div' | 'section' | 'article' | 'li' } & Record<string, unknown>) {
  return (
    <As className={cx('rounded-card bg-surface p-4 shadow-card', className)} {...rest}>
      {children}
    </As>
  );
}

// ------------------------------------------------------------------ Buttons

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'soft';
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-accent-ink hover:bg-accent-strong',
  secondary: 'bg-surface-2 text-ink hover:bg-surface-3',
  soft: 'bg-accent-soft text-accent hover:opacity-90',
  ghost: 'bg-transparent text-accent hover:bg-accent-soft',
  danger: 'bg-danger-soft text-danger hover:opacity-90',
};

export function Button({
  variant = 'primary',
  size = 'md',
  block,
  icon,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' | 'lg'; block?: boolean; icon?: ReactNode }) {
  return (
    <button
      type="button"
      className={cx(
        'press inline-flex select-none items-center justify-center gap-2 rounded-pill font-semibold disabled:cursor-not-allowed disabled:opacity-45',
        size === 'lg' && 'min-h-14 px-6 text-[17px]',
        size === 'md' && 'min-h-12 px-5 text-[15px]',
        size === 'sm' && 'min-h-10 px-4 text-[14px]',
        block && 'w-full',
        VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}

export function IconButton({ label, children, className, badge, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; badge?: number }) {
  return (
    <button type="button" aria-label={label} title={label} className={cx('press relative inline-flex size-12 items-center justify-center rounded-full bg-surface-2 text-ink hover:bg-surface-3', className)} {...rest}>
      {children}
      {badge ? (
        <span className="absolute right-1.5 top-1.5 flex min-w-5 items-center justify-center rounded-full bg-danger px-1 text-[11px] font-bold leading-5 text-white" aria-hidden>
          {badge}
        </span>
      ) : null}
    </button>
  );
}

export function ListRow({ icon, title, subtitle, trailing, onClick, href }: { icon?: ReactNode; title: ReactNode; subtitle?: ReactNode; trailing?: ReactNode; onClick?: () => void; href?: string }) {
  const content = (
    <>
      {icon && <span className="flex size-10 shrink-0 items-center justify-center rounded-[12px] bg-surface-2 text-ink-2">{icon}</span>}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[16px] font-semibold text-ink">{title}</span>
        {subtitle && <span className="mt-0.5 block text-[13px] text-muted">{subtitle}</span>}
      </span>
      {trailing ?? (onClick || href ? <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden /> : null)}
    </>
  );
  const cls = 'press flex min-h-14 w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-2/60';
  if (onClick) return <button type="button" onClick={onClick} className={cls}>{content}</button>;
  return <div className={cls}>{content}</div>;
}

// ------------------------------------------------------------------ Status & Fortschritt

export function Chip({ children, tone = 'neutral', icon, className }: { children: ReactNode; tone?: 'neutral' | 'accent' | 'success' | 'warn' | 'danger'; icon?: ReactNode; className?: string }) {
  const tones = {
    neutral: 'bg-surface-2 text-ink-2',
    accent: 'bg-accent-soft text-accent',
    success: 'bg-success-soft text-success',
    warn: 'bg-warn-soft text-warn',
    danger: 'bg-danger-soft text-danger',
  };
  return (
    <span className={cx('inline-flex items-center gap-1 whitespace-nowrap rounded-pill px-2.5 py-1 text-[12px] font-semibold', tones[tone], className)}>
      {icon}
      {children}
    </span>
  );
}

export function ProgressBar({ value, max, label, tone = 'accent', height = 10 }: { value: number; max: number; label: string; tone?: 'accent' | 'team-gs' | 'team-we' | 'team-bp' | 'success'; height?: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const fills = { accent: 'bg-accent', success: 'bg-success', 'team-gs': 'bg-team-gs', 'team-we': 'bg-team-we', 'team-bp': 'bg-team-bp' };
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} className="w-full overflow-hidden rounded-full bg-surface-2" style={{ height }}>
      <div className={cx('bar-progress h-full rounded-full', fills[tone])} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Fortschrittsring wie bei den großen Fitness-Apps. */
export function Ring({ value, max, size = 120, stroke = 14, children, label, gradient = true, color, trackClass = 'text-surface-2' }: { value: number; max: number; size?: number; stroke?: number; children?: ReactNode; label: string; gradient?: boolean; color?: string; trackClass?: string }) {
  const id = useId();
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(1, value / max) : 0;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--ring-from, var(--accent))" />
            <stop offset="100%" stopColor="var(--ring-to, var(--volt))" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={stroke} className={trackClass} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color ?? (gradient ? `url(#${id})` : 'var(--accent)')}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className="ring-progress"
          style={pct === 0 ? { opacity: 0 } : undefined}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  );
}

export function Stat({ label, value, unit, hint, icon }: { label: string; value: ReactNode; unit?: string; hint?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="min-w-0 rounded-tile bg-surface-2/70 p-3.5">
      <div className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-muted">
        {icon}
        <span className="truncate">{label}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="tnum text-[26px] font-extrabold leading-none tracking-tight text-ink">{value}</span>
        {unit && <span className="text-[13px] font-semibold text-muted">{unit}</span>}
      </div>
      {hint && <div className="mt-1 text-[12px] text-muted">{hint}</div>}
    </div>
  );
}

// ------------------------------------------------------------------ Identität

export function TeamBadge({ site, size = 'md', withName = true }: { site: Site; size?: 'sm' | 'md' | 'lg'; withName?: boolean }) {
  const t = TEAM_CLASSES[site.team];
  const dims = { sm: 'size-6 text-[10px]', md: 'size-8 text-[11px]', lg: 'size-11 text-[13px]' }[size];
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span className={cx('inline-flex shrink-0 items-center justify-center rounded-[10px] font-extrabold tracking-wide text-white', t.bg, dims)} aria-hidden>
        {site.short}
      </span>
      {withName ? <span className="truncate font-semibold">{site.name}</span> : <span className="sr-only">{site.teamName}</span>}
    </span>
  );
}

export function Avatar({ name, site, size = 40 }: { name: string; site?: Site; size?: number }) {
  const initials = name
    .replace(/\(.*\)/, '')
    .trim()
    .split(/\s+/)
    .map((s) => s[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  return (
    <span
      className={cx('inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white', site ? TEAM_CLASSES[site.team].bg : 'bg-accent')}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      aria-hidden
    >
      {initials}
    </span>
  );
}

// ------------------------------------------------------------------ Eingaben

export function Segmented<T extends string>({ options, value, onChange, label }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="tablist" aria-label={label} className="flex w-full gap-1 rounded-pill bg-surface-2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          type="button"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={cx(
            'press min-h-11 flex-1 truncate rounded-pill px-2 text-[14px] font-semibold',
            o.value === value ? 'bg-surface text-ink shadow-card' : 'text-muted hover:text-ink',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  const id = useId();
  return (
    <div className="flex min-h-14 items-center gap-3 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <label htmlFor={id} className="block text-[16px] font-semibold text-ink">
          {label}
        </label>
        {description && <p className="mt-0.5 text-[13px] text-muted">{description}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cx('press relative h-8 w-[52px] shrink-0 rounded-full', checked ? 'bg-accent' : 'bg-surface-3')}
      >
        <span className={cx('absolute top-1 flex size-6 items-center justify-center rounded-full bg-white shadow transition-all', checked ? 'left-[24px]' : 'left-1')}>
          {checked && <Check className="size-3.5 text-accent-strong" strokeWidth={3} aria-hidden />}
        </span>
        <span className="sr-only">{checked ? 'an' : 'aus'}</span>
      </button>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className="mb-4">
      <label htmlFor={id} className="mb-1.5 block text-[14px] font-semibold text-ink-2">
        {label}
      </label>
      {children(id)}
      {hint && <p className="mt-1 text-[12px] text-muted">{hint}</p>}
    </div>
  );
}

export const inputCls =
  'w-full min-h-12 rounded-[14px] border border-line bg-surface-2 px-4 text-[16px] text-ink placeholder:text-muted focus:border-accent focus:outline-none';

// ------------------------------------------------------------------ Sheet (Bottom Sheet / Dialog)

export function Sheet({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
      prev?.focus?.();
    };
  }, [open, onClose]);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="anim-fade absolute inset-0 bg-black/50" onClick={onClose} aria-hidden />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="anim-sheet relative flex max-h-[92dvh] w-full max-w-xl flex-col rounded-t-[28px] bg-surface shadow-float outline-none sm:rounded-[28px]"
      >
        <div className="mx-auto mt-2.5 h-1.5 w-10 rounded-full bg-surface-3" aria-hidden />
        <div className="flex items-center justify-between gap-3 px-5 pb-2 pt-3">
          <h2 id={titleId} className="text-[20px] font-bold tracking-tight">
            {title}
          </h2>
          <IconButton label="Schließen" onClick={onClose} className="size-10">
            <X className="size-5" />
          </IconButton>
        </div>
        <div className="overflow-y-auto px-5 pb-4">{children}</div>
        {footer && <div className="border-t border-line px-5 py-3 pb-safe">{footer}</div>}
        {!footer && <div className="pb-safe" />}
      </div>
    </div>,
    document.body,
  );
}

// ------------------------------------------------------------------ Toast

type ToastMsg = { id: number; text: string; tone: 'success' | 'info' | 'error' };
const ToastCtx = createContext<(text: string, tone?: ToastMsg['tone']) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastMsg[]>([]);
  const push = useCallback((text: string, tone: ToastMsg['tone'] = 'success') => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs, { id, text, tone }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3800);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-0 z-[60] flex flex-col items-center gap-2 px-4 pt-safe" aria-live="polite" role="status">
        {items.map((t) => (
          <div key={t.id} className="anim-rise glass pointer-events-auto mt-3 flex w-full max-w-md items-start gap-3 rounded-[18px] px-4 py-3 text-[15px] font-medium text-ink shadow-float">
            <span className={cx('mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full', t.tone === 'success' ? 'bg-success text-white' : t.tone === 'error' ? 'bg-danger text-white' : 'bg-accent text-accent-ink')} aria-hidden>
              {t.tone === 'success' ? <Check className="size-4" strokeWidth={3} /> : t.tone === 'error' ? <X className="size-4" strokeWidth={3} /> : <Info className="size-4" />}
            </span>
            <span className="min-w-0 flex-1">{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function EmptyState({ icon, title, text, action }: { icon: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <div className="mb-3 flex size-14 items-center justify-center rounded-full bg-surface-2 text-muted">{icon}</div>
      <p className="text-[17px] font-semibold">{title}</p>
      {text && <p className="mt-1 text-[14px] text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
