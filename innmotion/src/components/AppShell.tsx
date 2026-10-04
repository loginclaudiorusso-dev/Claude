import { Suspense } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  CalendarDays, ChartColumn, ClipboardList, House, LayoutDashboard, QrCode, Settings, Star, Swords, Trophy, UserRound, Target,
  type LucideIcon,
} from 'lucide-react';
import { useSession } from '../services/mock/store';
import type { Role } from '../domain/types';
import { cx } from './ui';

type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean };

export const NAV: Record<Role, NavItem[]> = {
  participant: [
    { to: '/', label: 'Start', icon: House, end: true },
    { to: '/challenges', label: 'Challenges', icon: Target },
    { to: '/events', label: 'Events', icon: CalendarDays },
    { to: '/liga', label: 'Liga', icon: Trophy },
    { to: '/profil', label: 'Profil', icon: UserRound },
  ],
  staff: [
    { to: '/betreuung', label: 'Heute', icon: ClipboardList, end: true },
    { to: '/betreuung/code', label: 'Code', icon: QrCode },
    { to: '/betreuung/events', label: 'Events', icon: CalendarDays },
    { to: '/betreuung/turnier', label: 'Turnier', icon: Swords },
    { to: '/profil', label: 'Profil', icon: UserRound },
  ],
  lead: [
    { to: '/leitung', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/leitung/liga', label: 'Liga', icon: ChartColumn },
    { to: '/leitung/umfrage', label: 'Umfrage', icon: Star },
    { to: '/leitung/verwaltung', label: 'Verwaltung', icon: Settings },
    { to: '/profil', label: 'Profil', icon: UserRound },
  ],
};

export function AppShell() {
  const role = useSession((s) => s.role);
  return (
    <div className="min-h-dvh bg-bg pt-safe">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-pill focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-ink">
        Zum Inhalt springen
      </a>
      <main id="main">
        <Suspense fallback={<div className="min-h-dvh" aria-busy="true" />}>
          <Outlet />
        </Suspense>
      </main>
      <BottomNav items={NAV[role]} />
    </div>
  );
}

function BottomNav({ items }: { items: NavItem[] }) {
  return (
    <nav aria-label="Hauptnavigation" className="glass fixed inset-x-0 bottom-0 z-40 border-t border-line pb-safe">
      <ul className="mx-auto flex max-w-xl items-stretch justify-around px-1">
        {items.map(({ to, label, icon: Icon, end }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cx('press flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold', isActive ? 'text-accent' : 'text-muted hover:text-ink')
              }
            >
              {({ isActive }) => (
                <>
                  <span className={cx('flex h-8 w-14 items-center justify-center rounded-full transition-colors', isActive && 'bg-accent-soft')}>
                    <Icon className="size-[22px]" strokeWidth={isActive ? 2.4 : 2} aria-hidden />
                  </span>
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
