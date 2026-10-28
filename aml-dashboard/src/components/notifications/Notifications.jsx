import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

export default function Notifications({ list, onMarkAll, onDismiss, openCaseById }) {
  const markAll = () => onMarkAll();
  const dismiss = (id) => onDismiss(id);

  return (
    <div className="view flex h-full flex-col overflow-hidden">
      <ScrollArea className="h-full">
        <div className="mx-auto h-full w-full max-w-[920px] px-7 py-[22px]">
          <div className="mb-[18px] flex items-baseline justify-between">
            <div>
              <h1 className="text-lg font-semibold">Notifications</h1>
              <p className="mt-0.5 text-xs text-muted-foreground">{list.filter((n) => !n.read).length} unread · sorted by recency</p>
            </div>
            <Button variant="sky" size="sm" onClick={markAll}>Mark all as read</Button>
          </div>

          <div className="flex flex-col gap-2">
            {list.length === 0 && (
              <div className="py-8 text-center text-muted-foreground">No notifications</div>
            )}
            {list.map((n) => (
              <Card
                key={n.id}
                className={cn('grid grid-cols-[28px_1fr_auto] items-center gap-3.5 border-l-[3px] py-3.5', n.read && 'opacity-50')}
                style={{ borderLeftColor: n.color }}
              >
                <CardContent className="col-span-3 grid grid-cols-subgrid items-center px-[18px] py-0">
                  <div className="flex size-7 items-center justify-center rounded-full bg-white/5 text-sm" style={{ color: n.color }}>{n.icon}</div>
                  <div>
                    <div className="flex items-center gap-2.5 text-xs font-semibold">
                      {n.title}
                      <span className="font-mono text-[10px] font-normal text-muted-foreground">{n.time}</span>
                    </div>
                    <div className="mt-1 text-xs leading-relaxed text-muted-foreground [&_.case-ref]:font-mono [&_.case-ref]:text-foreground [&_.mention]:font-medium [&_.mention]:text-primary" dangerouslySetInnerHTML={{ __html: n.msg }} />
                  </div>
                  <div className="flex gap-1.5">
                    <Button variant="sky" size="sm" className="text-[11px]" onClick={() => openCaseById(n.caseId)}>{n.action}</Button>
                    <Button variant="ghost" size="icon-sm" className="text-muted-foreground" onClick={() => dismiss(n.id)} title="Dismiss">×</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
