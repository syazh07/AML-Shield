import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { statusClass, statusLabel } from '@/utils/formatters';

const styles = {
  'status-unclaimed': 'border-amber-500/30 bg-amber-500/15 text-amber-400',
  'status-progress': 'border-sky-500/30 bg-sky-500/15 text-sky-400',
  'status-review': 'border-violet-500/30 bg-violet-500/15 text-violet-400',
  'status-ready': 'border-emerald-500/30 bg-emerald-500/15 text-emerald-400',
  'status-closed': 'border-slate-500/30 bg-slate-500/15 text-slate-400',
};

export default function StatusBadge({ status, className }) {
  const cls = statusClass[status];
  return (
    <Badge
      variant="outline"
      className={cn('rounded-sm text-[10px] uppercase tracking-wide', styles[cls], className)}
    >
      {statusLabel[status]}
    </Badge>
  );
}
