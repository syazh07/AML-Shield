import { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme.js';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

const navItems = [
  { id: 'pool', label: 'Case Pool' },
  { id: 'invest', label: 'Investigation' },
  { id: 'notif', label: 'Notifications' },
];

export default function TopNav({ view, setView, unreadCount, user }) {
  const { isDark, toggleTheme } = useTheme();
  const initials = user?.initials || '—';
  const name = user?.name || 'Loading…';
  const branch = user?.branch || '';
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const i = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(i);
  }, []);
  const clock = `${time.toLocaleTimeString('en-IN', { hour12: false })} IST`;

  return (
    <header className="flex h-[52px] shrink-0 items-center gap-7 border-b border-border bg-card px-[18px]">
      <div className="flex items-center gap-2.5">
        <div className="brand-mark relative flex size-7 items-center justify-center rounded bg-gradient-to-br from-sky-500 to-sky-800" />
        <div>
          <div className="text-[13px] font-bold tracking-wide">AML SHIELD</div>
          <div className="font-mono text-[10px] tracking-widest text-muted-foreground">FINCRIME WORKSTATION</div>
        </div>
      </div>

      <Separator orientation="vertical" className="h-6" />

      <nav className="flex gap-1">
        {navItems.map((item) => (
          <Button
            key={item.id}
            variant="ghost"
            size="sm"
            className={cn(
              'relative h-8 rounded-sm px-3.5 text-xs font-medium text-muted-foreground hover:text-foreground',
              view === item.id && 'text-foreground after:absolute after:inset-x-3.5 after:-bottom-4 after:h-0.5 after:bg-primary'
            )}
            onClick={() => setView(item.id)}
          >
            {item.label}
            {item.id === 'notif' && unreadCount > 0 && (
              <Badge variant="destructive" className="ml-2 h-4 min-w-4 rounded-full px-1 font-mono text-[10px]">
                {unreadCount}
              </Badge>
            )}
          </Button>
        ))}
      </nav>

      <div className="flex-1" />

      <div className="flex items-center gap-[18px]">
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-muted-foreground hover:text-foreground"
          onClick={toggleTheme}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDark ? 'Light mode' : 'Dark mode'}
        >
          {isDark ? <Sun /> : <Moon />}
        </Button>
        <div className="font-mono text-xs tracking-wide text-muted-foreground">{clock}</div>
        <div className="flex items-center gap-2.5 rounded-full border border-border py-1 pr-2.5 pl-1">
          <div className="flex size-[26px] items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-sky-500 text-[11px] font-semibold text-white">
            {initials}
          </div>
          <div className="text-[11px] leading-tight">
            <strong className="block font-semibold">{name}</strong>
            <small className="text-muted-foreground">{user?.role || 'L1 Analyst'} · {branch}</small>
          </div>
        </div>
      </div>
    </header>
  );
}
