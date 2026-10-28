import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { riskClass } from '@/utils/formatters';

const styles = {
  'risk-green': 'border-emerald-500/30 bg-emerald-500/15 text-emerald-400',
  'risk-amber': 'border-amber-500/30 bg-amber-500/15 text-amber-400',
  'risk-red': 'border-red-500/30 bg-red-500/15 text-red-400',
  'risk-critical': 'animate-pulse border-red-500 bg-red-500/20 text-red-400',
};

export default function RiskBadge({ score, className }) {
  return (
    <Badge
      variant="outline"
      className={cn('min-w-9 justify-center font-mono text-xs font-semibold', styles[riskClass(score)], className)}
    >
      {score}
    </Badge>
  );
}
