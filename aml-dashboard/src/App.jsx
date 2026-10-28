import { useState, useCallback, useEffect } from 'react';
import { CASES, INITIAL_NOTIFICATIONS } from '@/data/constants.js';
import { api } from '@/lib/api.js';
import TopNav from '@/components/layout/TopNav.jsx';
import CasePool from '@/components/case-pool/CasePool.jsx';
import Investigation from '@/components/investigation/Investigation.jsx';
import Notifications from '@/components/notifications/Notifications.jsx';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const toastStyles = {
  green: 'border-l-emerald-500',
  warn: 'border-l-amber-500',
  red: 'border-l-red-500',
  blue: 'border-l-sky-500',
  purple: 'border-l-violet-500',
};

const POLL_MS = 5000;

export default function App() {
  const [view, setView] = useState('pool');
  // Seed constants are the offline fallback; live data from the API overwrites them.
  const [cases, setCases] = useState(CASES);
  const [currentCaseId, setCurrentCaseId] = useState('IOB-2024-MU-4471');
  const [notifs, setNotifs] = useState(INITIAL_NOTIFICATIONS.map((n) => ({ ...n, read: false })));
  const [session, setSession] = useState({ user: null, team: [] });
  const [toasts, setToasts] = useState([]);

  const pushToast = useCallback((t) => {
    const id = Date.now() + Math.random();
    const time = t.time || new Date().toTimeString().slice(0, 8);
    setToasts((curr) => [...curr, { ...t, id, time }]);
    setTimeout(() => setToasts((curr) => curr.filter((x) => x.id !== id)), 4500);
  }, []);

  // --- live data: fetch on mount + poll, so seeder activity shows up ---
  const loadCases = useCallback(async () => {
    try { setCases(await api.listCases()); } catch { /* keep last good data */ }
  }, []);
  const loadNotifs = useCallback(async () => {
    try { setNotifs(await api.listNotifications()); } catch { /* keep last good data */ }
  }, []);

  useEffect(() => {
    loadCases();
    loadNotifs();
    api.getSession().then(setSession).catch(() => { /* keep default */ });
    const id = setInterval(() => { loadCases(); loadNotifs(); }, POLL_MS);
    return () => clearInterval(id);
  }, [loadCases, loadNotifs]);

  const claimCase = async (id) => {
    try {
      await api.claimCase(id);
      pushToast({ kind: 'blue', title: 'Case claimed', msg: `${id} · investigation started.` });
    } catch {
      pushToast({ kind: 'warn', title: 'Could not claim', msg: `${id} · opening read-only.` });
    }
    await loadCases();
    setCurrentCaseId(id);
    setView('invest');
  };
  const openCase = (id) => { setCurrentCaseId(id); setView('invest'); };

  const markAllRead = async () => {
    setNotifs((ns) => ns.map((n) => ({ ...n, read: true }))); // optimistic
    try { await api.markAllNotificationsRead(); await loadNotifs(); } catch { /* ignore */ }
  };
  const dismissNotif = async (id) => {
    setNotifs((ns) => ns.filter((n) => n.id !== id)); // optimistic
    try { await api.dismissNotification(id); } catch { /* ignore */ }
  };

  const currentCase = cases.find((c) => c.id === currentCaseId) || cases[0];
  const unreadCount = notifs.filter((n) => !n.read).length;

  return (
    <div className="flex h-full flex-col">
      <TopNav view={view} setView={setView} unreadCount={unreadCount} user={session.user} />
      {view === 'pool' && <CasePool cases={cases} openCase={openCase} claimCase={claimCase} user={session.user} />}
      {view === 'invest' && <Investigation caseObj={currentCase} goBack={() => setView('pool')} toast={pushToast} openCase={openCase} session={session} />}
      {view === 'notif' && <Notifications list={notifs} onMarkAll={markAllRead} onDismiss={dismissNotif} openCaseById={(id) => { if (id) openCase(id); }} />}

      <div className="pointer-events-none fixed right-[18px] top-16 z-[200] flex flex-col gap-2">
        {toasts.map((t) => (
          <Card key={t.id} className={cn('pointer-events-auto min-w-[280px] border-l-[3px] py-2.5 shadow-lg animate-in slide-in-from-right-4', toastStyles[t.kind] || toastStyles.green)}>
            <CardContent className="px-3.5 py-0">
              <div className="text-xs font-semibold">{t.title}</div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">{t.msg}</div>
              <div className="mt-1 font-mono text-[10px] text-muted-foreground">{t.time}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
