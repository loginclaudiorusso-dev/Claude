import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Award, ClipboardList, Database, Lightbulb, Moon, RotateCcw, Shield, Star, Sun, SunMoon, Type } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { usePrefs, useSession, type ThemePref } from '../../services/mock/store';
import { earnedBadges, BADGES } from '../../domain/badges';
import { activeSeason, personPoints, seasonRange } from '../../domain/league';
import type { Role } from '../../domain/types';
import { Avatar, Button, Card, Field, inputCls, ListRow, Page, SectionHeader, Segmented, Sheet, TeamBadge, Toggle, useToast } from '../../components/ui';
import { DEMO_IDS } from '../../seed/generate';

const ROLE_LABEL: Record<Role, string> = { participant: 'Teilnehmende', staff: 'Betreuung', lead: 'Leitung' };
const ROLE_HOME: Record<Role, string> = { participant: '/', staff: '/betreuung', lead: '/leitung' };

export function Profile() {
  const db = useDb();
  const me = useMe();
  const now = useNow();
  const navigate = useNavigate();
  const toast = useToast();
  const { role, setRole, setPerson, personByRole } = useSession();
  const { theme, setTheme, largeText, setLargeText } = usePrefs();
  const [editOpen, setEditOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  const switchRole = (r: Role) => {
    setRole(r);
    navigate(ROLE_HOME[r]);
  };

  if (!me) {
    // z. B. nach „Konto löschen“
    return (
      <Page>
        <div className="pt-10 text-center">
          <h1 className="text-[26px] font-extrabold">Konto gelöscht</h1>
          <p className="mt-2 text-ink-2">Deine Daten wurden entfernt. Für die Demo kannst du eine andere Person wählen.</p>
          <Button
            className="mt-6"
            onClick={() => {
              const next = db.persons.find((p) => p.role === role);
              if (next) setPerson(role, next.id);
              else void api.resetDemo().then(() => setPerson(role, DEMO_IDS[role]));
            }}
          >
            Andere Demo-Person wählen
          </Button>
        </div>
      </Page>
    );
  }

  const site = db.sites.find((s) => s.id === me.siteId)!;
  const [sFrom, sTo] = seasonRange(activeSeason(db), now);
  const earned = earnedBadges(db, me.id, now);
  const candidates = db.persons.filter((p) => p.role === role);

  return (
    <Page>
      {/* Rollenwechsler für die Demo */}
      <div className="pt-3">
        <p className="mb-2 text-[12px] font-semibold uppercase tracking-wider text-muted">Demo · Rolle wechseln</p>
        <Segmented<Role>
          label="Rolle"
          value={role}
          onChange={switchRole}
          options={(['participant', 'staff', 'lead'] as Role[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }))}
        />
        {role !== 'lead' && (
          <div className="mt-2">
            <label className="sr-only" htmlFor="demo-person">
              Demo-Person
            </label>
            <select
              id="demo-person"
              className={inputCls + ' min-h-11 text-[15px]'}
              value={personByRole[role]}
              onChange={(e) => setPerson(role, e.target.value)}
            >
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
          </div>
        )}
      </div>

      {/* Kopf */}
      <section className="mt-6 flex flex-col items-center text-center">
        <Avatar name={me.nickname} site={site} size={84} />
        <h1 className="mt-3 text-[28px] font-extrabold tracking-tight">{me.nickname}</h1>
        <div className="mt-1 flex items-center gap-2 text-[14px] text-ink-2">
          <TeamBadge site={site} size="sm" />
          {me.subgroup && <span>· {me.subgroup}</span>}
        </div>
        <p className="mt-1 text-[13px] text-muted">{ROLE_LABEL[me.role]}</p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={() => setEditOpen(true)}>
          Profil bearbeiten
        </Button>
      </section>

      {role === 'participant' && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <Card className="text-center">
              <p className="tnum text-[28px] font-extrabold">{personPoints(db, me.id, sFrom, sTo)}</p>
              <p className="text-[13px] text-muted">Punkte in dieser Saison</p>
            </Card>
            <Card className="text-center">
              <p className="tnum text-[28px] font-extrabold">
                {earned.size}
                <span className="text-[16px] text-muted">/{BADGES.length}</span>
              </p>
              <p className="text-[13px] text-muted">Abzeichen</p>
            </Card>
          </div>
          <Card className="mt-4 divide-y divide-line overflow-hidden p-0">
            <ListRow icon={<Award className="size-5" />} title="Abzeichen" subtitle="Deine Galerie" onClick={() => navigate('/profil/abzeichen')} />
            <ListRow icon={<Lightbulb className="size-5" />} title="Wünsch dir was" subtitle="Ideen einreichen und abstimmen" onClick={() => navigate('/profil/ideen')} />
            <ListRow icon={<Star className="size-5" />} title="Kurzumfrage" subtitle="3 Fragen, anonym" onClick={() => navigate('/profil/umfrage')} />
          </Card>

          <SectionHeader title="Privatsphäre" />
          <Card className="divide-y divide-line overflow-hidden p-0">
            <Toggle
              label="In der Einzel-Rangliste zeigen"
              description="Freiwillig. Ohne Opt-in siehst nur du deinen Fortschritt."
              checked={me.leaderboardOptIn}
              onChange={(v) => {
                void api.updateProfile(me.id, { leaderboardOptIn: v });
                toast(v ? 'Du erscheinst jetzt in der Einzel-Rangliste.' : 'Du bist nicht mehr in der Einzel-Rangliste.', 'info');
              }}
            />
            <Toggle label="Benachrichtigungen" description="Erinnerungen an Events und Ankündigungen" checked={me.notifications} onChange={(v) => void api.updateProfile(me.id, { notifications: v })} />
            <ListRow icon={<Database className="size-5" />} title="Meine Daten" subtitle="Was gespeichert ist · Konto löschen" onClick={() => navigate('/profil/daten')} />
          </Card>
        </>
      )}

      {role === 'staff' && (
        <Card className="mt-6 divide-y divide-line overflow-hidden p-0">
          <ListRow icon={<ClipboardList className="size-5" />} title="Ankündigung senden" subtitle={`An alle in ${site.name}`} onClick={() => navigate('/betreuung/ankuendigung')} />
          <ListRow icon={<Lightbulb className="size-5" />} title="Wünsch dir was" subtitle="Ideen als „wird umgesetzt“ markieren" onClick={() => navigate('/betreuung/ideen')} />
        </Card>
      )}

      {role === 'lead' && (
        <Card className="mt-6 divide-y divide-line overflow-hidden p-0">
          <ListRow icon={<Shield className="size-5" />} title="Datenschutz" subtitle="Löschfristen und gespeicherte Daten" onClick={() => navigate('/leitung/datenschutz')} />
        </Card>
      )}

      <SectionHeader title="Darstellung" />
      <Card className="space-y-1 p-0">
        <div className="px-4 pb-2 pt-4">
          <p className="mb-2 flex items-center gap-2 text-[16px] font-semibold">
            <SunMoon className="size-5 text-muted" aria-hidden /> Hell / Dunkel
          </p>
          <Segmented<ThemePref>
            label="Farbschema"
            value={theme}
            onChange={setTheme}
            options={[
              { value: 'system', label: 'System' },
              { value: 'light', label: 'Hell' },
              { value: 'dark', label: 'Dunkel' },
            ]}
          />
        </div>
        <Toggle label="Größere Schrift" description="Alle Texte etwas größer" checked={largeText} onChange={setLargeText} />
      </Card>
      <p className="mt-2 flex items-center justify-center gap-2 text-[12px] text-muted" aria-hidden>
        <Sun className="size-3.5" /> <Type className="size-3.5" /> <Moon className="size-3.5" />
      </p>

      <SectionHeader title="Demo" />
      <Card className="p-4">
        <p className="text-[14px] text-ink-2">Alle Daten sind erfunden und liegen nur auf diesem Gerät. Zurücksetzen erzeugt frische Demo-Daten.</p>
        <Button variant="danger" block className="mt-3" icon={<RotateCcw className="size-4" />} onClick={() => setResetOpen(true)}>
          Demo zurücksetzen
        </Button>
      </Card>

      <EditProfileSheet open={editOpen} onClose={() => setEditOpen(false)} />
      <Sheet
        open={resetOpen}
        onClose={() => setResetOpen(false)}
        title="Demo zurücksetzen?"
        footer={
          <div className="flex gap-3">
            <Button variant="secondary" block onClick={() => setResetOpen(false)}>
              Abbrechen
            </Button>
            <Button
              variant="danger"
              block
              onClick={async () => {
                await api.resetDemo();
                useSession.setState({ personByRole: { ...DEMO_IDS } });
                setResetOpen(false);
                toast('Demo-Daten wurden neu erzeugt.');
              }}
            >
              Zurücksetzen
            </Button>
          </div>
        }
      >
        <p className="text-[15px] text-ink-2">Alle Änderungen (Check-ins, Anmeldungen, Ideen …) gehen verloren und die Demo startet neu.</p>
      </Sheet>
    </Page>
  );
}

function EditProfileSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const me = useMe()!;
  const [nickname, setNickname] = useState(me.nickname);
  const [subgroup, setSubgroup] = useState(me.subgroup ?? '');
  const toast = useToast();
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Profil bearbeiten"
      footer={
        <Button
          block
          disabled={nickname.trim().length < 2}
          onClick={async () => {
            await api.updateProfile(me.id, { nickname: nickname.trim().slice(0, 24), subgroup: subgroup.trim() || undefined });
            toast('Gespeichert.');
            onClose();
          }}
        >
          Speichern
        </Button>
      }
    >
      <Field label="Spitzname" hint="Bitte keinen vollständigen Klarnamen verwenden.">
        {(id) => <input id={id} className={inputCls} value={nickname} maxLength={24} onChange={(e) => setNickname(e.target.value)} autoComplete="off" />}
      </Field>
      <Field label="Haus / Etage (optional)" hint="Für kleine Untergruppen-Wertungen im Team.">
        {(id) => <input id={id} className={inputCls} value={subgroup} maxLength={30} onChange={(e) => setSubgroup(e.target.value)} placeholder="z. B. Haus A · 1. OG" />}
      </Field>
    </Sheet>
  );
}
