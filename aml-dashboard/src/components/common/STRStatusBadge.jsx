import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const configs = {
  none: { label: 'STR: Not Started', className: 'border-border text-muted-foreground' },
  drafting: { label: 'STR: Drafting', className: 'border-amber-500/40 bg-amber-500/10 text-amber-400' },
  review: { label: 'STR: Pending Review', className: 'border-violet-500/40 bg-violet-500/10 text-violet-400' },
  filed: { label: 'STR: Filed', className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' },
};

export default function STRStatusBadge({ strStatus }) {
  const cfg = configs[strStatus] || configs.none;
  return (
    <Badge variant="outline" className={cn('gap-1.5 rounded-full font-mono text-[10px] font-semibold tracking-wide', cfg.className)}>
      <span className={cn('size-1.5 rounded-full bg-current', strStatus === 'drafting' && 'animate-pulse')} />
      {cfg.label}
    </Badge>
  );
}
