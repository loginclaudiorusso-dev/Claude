import { useEffect } from 'react';
import { BellRing } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { fmt } from '../../domain/time';
import { EmptyState, Sheet, cx } from '../../components/ui';

/** Simulierte Push-Benachrichtigungen (im echten Betrieb: Web-Push). */
export function NotificationsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const list = db.notifications.filter((n) => n.personId === me.id).slice(0, 30);
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => api.markNotificationsRead(me.id), 1200);
    return () => clearTimeout(t);
  }, [open, me.id]);
  return (
    <Sheet open={open} onClose={onClose} title="Benachrichtigungen">
      {!me.notifications && <p className="mb-3 rounded-[14px] bg-warn-soft p-3 text-[14px] text-warn">Benachrichtigungen sind in deinem Profil ausgeschaltet.</p>}
      {list.length === 0 ? (
        <EmptyState icon={<BellRing />} title="Alles gelesen" text="Hier erscheinen Erinnerungen und Ankündigungen." />
      ) : (
        <ul className="space-y-2">
          {list.map((n) => (
            <li key={n.id} className={cx('rounded-[16px] p-3.5', n.read ? 'bg-surface-2/60' : 'bg-accent-soft')}>
              <div className="flex items-center justify-between gap-2">
                <p className="text-[14px] font-bold">{n.title}</p>
                <p className="shrink-0 text-[12px] text-muted">
                  {fmt.relativeDay(n.at, now)}, {fmt.time(n.at)}
                </p>
              </div>
              <p className="mt-0.5 text-[14px] text-ink-2">{n.text}</p>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  );
}
