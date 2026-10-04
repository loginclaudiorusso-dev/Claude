import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ThemeSync } from './components/ThemeSync';
import { useSession } from './services/mock/store';
import type { Role } from './domain/types';
import { Home } from './screens/participant/Home';
import { EventDetail, Events } from './screens/participant/Events';
import { Profile } from './screens/shared/Profile';
import { Challenges } from './screens/participant/Challenges';
import { Liga } from './screens/participant/Liga';
import { Badges, Ideas, MyData, Survey } from './screens/participant/ProfilePages';
import { useMe } from './services/hooks';
import { lazy, Suspense, type ReactNode } from 'react';

// Betreuung, Leitung und Scanner (Kamera/QR-Bibliotheken) erst bei Bedarf laden.
const Checkin = lazy(() => import('./screens/participant/Checkin').then((m) => ({ default: m.Checkin })));
const Dashboard = lazy(() => import('./screens/lead/Dashboard').then((m) => ({ default: m.Dashboard })));
const SurveyResults = lazy(() => import('./screens/lead/SurveyResults').then((m) => ({ default: m.SurveyResults })));
const Poster = lazy(() => import('./screens/lead/Poster').then((m) => ({ default: m.Poster })));
const StaffToday = lazy(() => import('./screens/staff/Today').then((m) => ({ default: m.StaffToday })));
const StaffCode = lazy(() => import('./screens/staff/Code').then((m) => ({ default: m.StaffCode })));
const Admin = lazy(() => import('./screens/lead/Admin').then((m) => ({ default: m.Admin })));
const LeadLiga = lazy(() => import('./screens/lead/Admin').then((m) => ({ default: m.LeadLiga })));
const Privacy = lazy(() => import('./screens/lead/Admin').then((m) => ({ default: m.Privacy })));
const Announcement = lazy(() => import('./screens/staff/StaffEvents').then((m) => ({ default: m.Announcement })));
const NewEvent = lazy(() => import('./screens/staff/StaffEvents').then((m) => ({ default: m.NewEvent })));
const StaffEvents = lazy(() => import('./screens/staff/StaffEvents').then((m) => ({ default: m.StaffEvents })));
const StaffTournamentDetail = lazy(() => import('./screens/staff/StaffTournament').then((m) => ({ default: m.StaffTournamentDetail })));
const StaffTournaments = lazy(() => import('./screens/staff/StaffTournament').then((m) => ({ default: m.StaffTournaments })));

/** Schützt Bereiche einer Rolle – bei falscher Rolle zur Startseite der aktiven Rolle. */
function RoleGate({ role, children }: { role: Role; children: ReactNode }) {
  const current = useSession((s) => s.role);
  const me = useMe();
  if (!me) return <Navigate to="/profil" replace />;
  if (current !== role) return <Navigate to={current === 'participant' ? '/' : current === 'staff' ? '/betreuung' : '/leitung'} replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <>
      <ThemeSync />
      <Suspense fallback={<div className="min-h-dvh bg-bg" aria-busy="true" />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<RoleGate role="participant"><Home /></RoleGate>} />
          <Route path="challenges" element={<RoleGate role="participant"><Challenges /></RoleGate>} />
          <Route path="events" element={<RoleGate role="participant"><Events /></RoleGate>} />
          <Route path="events/:id" element={<RoleGate role="participant"><EventDetail /></RoleGate>} />
          <Route path="liga" element={<RoleGate role="participant"><Liga /></RoleGate>} />
          <Route path="profil" element={<Profile />} />
          <Route path="profil/abzeichen" element={<RoleGate role="participant"><Badges /></RoleGate>} />
          <Route path="profil/ideen" element={<RoleGate role="participant"><Ideas /></RoleGate>} />
          <Route path="profil/umfrage" element={<RoleGate role="participant"><Survey /></RoleGate>} />
          <Route path="profil/daten" element={<RoleGate role="participant"><MyData /></RoleGate>} />
          <Route path="betreuung" element={<RoleGate role="staff"><StaffToday /></RoleGate>} />
          <Route path="betreuung/code" element={<RoleGate role="staff"><StaffCode /></RoleGate>} />
          <Route path="betreuung/events" element={<RoleGate role="staff"><StaffEvents /></RoleGate>} />
          <Route path="betreuung/events/neu" element={<RoleGate role="staff"><NewEvent /></RoleGate>} />
          <Route path="betreuung/turnier" element={<RoleGate role="staff"><StaffTournaments /></RoleGate>} />
          <Route path="betreuung/turnier/:id" element={<RoleGate role="staff"><StaffTournamentDetail /></RoleGate>} />
          <Route path="betreuung/ankuendigung" element={<RoleGate role="staff"><Announcement /></RoleGate>} />
          <Route path="betreuung/ideen" element={<RoleGate role="staff"><Ideas staffMode /></RoleGate>} />
          <Route path="leitung" element={<RoleGate role="lead"><Dashboard /></RoleGate>} />
          <Route path="leitung/liga" element={<RoleGate role="lead"><LeadLiga /></RoleGate>} />
          <Route path="leitung/umfrage" element={<RoleGate role="lead"><SurveyResults /></RoleGate>} />
          <Route path="leitung/verwaltung" element={<RoleGate role="lead"><Admin /></RoleGate>} />
          <Route path="leitung/datenschutz" element={<RoleGate role="lead"><Privacy /></RoleGate>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
 <Route path="aushang/:siteId" element={<RoleGate role="lead"><Poster /></RoleGate>} />
        <Route path="checkin" element={<RoleGate role="participant"><Checkin /></RoleGate>} />
      </Routes>
      </Suspense>
    </>
  );
}
