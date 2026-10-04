import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ThemeSync } from './components/ThemeSync';
import { useSession } from './services/mock/store';
import type { Role } from './domain/types';
import { Home } from './screens/participant/Home';
import { EventDetail, Events } from './screens/participant/Events';
import { Profile } from './screens/shared/Profile';
import { Page, LargeTitle } from './components/ui';
import type { ReactNode } from 'react';

function Placeholder({ title }: { title: string }) {
  return (
    <Page>
      <LargeTitle title={title} subtitle="Wird in der nächsten Etappe gebaut." />
    </Page>
  );
}

/** Schützt Bereiche einer Rolle – bei falscher Rolle zur Startseite der aktiven Rolle. */
function RoleGate({ role, children }: { role: Role; children: ReactNode }) {
  const current = useSession((s) => s.role);
  if (current !== role) return <Navigate to={current === 'participant' ? '/' : current === 'staff' ? '/betreuung' : '/leitung'} replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <>
      <ThemeSync />
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<RoleGate role="participant"><Home /></RoleGate>} />
          <Route path="challenges" element={<RoleGate role="participant"><Placeholder title="Challenges" /></RoleGate>} />
          <Route path="events" element={<RoleGate role="participant"><Events /></RoleGate>} />
          <Route path="events/:id" element={<RoleGate role="participant"><EventDetail /></RoleGate>} />
          <Route path="liga" element={<RoleGate role="participant"><Placeholder title="Liga" /></RoleGate>} />
          <Route path="profil" element={<Profile />} />
          <Route path="betreuung" element={<RoleGate role="staff"><Placeholder title="Heute" /></RoleGate>} />
          <Route path="leitung" element={<RoleGate role="lead"><Placeholder title="Dashboard" /></RoleGate>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
        <Route path="checkin" element={<RoleGate role="participant"><Placeholder title="Check-in" /></RoleGate>} />
      </Routes>
    </>
  );
}
