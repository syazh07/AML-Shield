import { useState, useMemo } from 'react';
import { fmtMin, fmtHrs } from '@/utils/formatters.js';
import RiskBadge from '@/components/common/RiskBadge.jsx';
import StatusBadge from '@/components/common/StatusBadge.jsx';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

export default function CasePool({ cases, openCase, claimCase, user }) {
  const userName = user?.name || 'Priya Venkatesh';
  const [filterFlag, setFilterFlag] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [scoreMin, setScoreMin] = useState(0);
  const [scoreMax, setScoreMax] = useState(100);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('score');
  const [sortDir, setSortDir] = useState('desc');

  const flags = useMemo(() => Array.from(new Set(cases.map((c) => c.flag))), [cases]);
  const filtered = useMemo(() => {
    let rows = cases.filter((c) => {
      if (filterFlag !== 'all' && c.flag !== filterFlag) return false;
      if (filterStatus !== 'all' && c.status !== filterStatus) return false;
      if (c.score < scoreMin || c.score > scoreMax) return false;
      if (search && !(c.id.toLowerCase().includes(search.toLowerCase()) || c.account.toLowerCase().includes(search.toLowerCase()))) return false;
      return true;
    });
    rows = [...rows].sort((a, b) => {
      let va = a[sortBy];
      let vb = b[sortBy];
      if (sortBy === 'claimedBy') { va = va || 'zzz'; vb = vb || 'zzz'; }
      if (sortBy === 'strDeadlineHrs') { va = va == null ? 99999 : va; vb = vb == null ? 99999 : vb; }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return rows;
  }, [cases, filterFlag, filterStatus, scoreMin, scoreMax, search, sortBy, sortDir]);

  const toggleSort = (key) => {
    if (sortBy === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortBy(key); setSortDir(key === 'score' ? 'desc' : 'asc'); }
  };
  const sortInd = (key) => sortBy === key ? (sortDir === 'asc' ? '↑' : '↓') : null;

  const unclaimed = cases.filter((c) => c.status === 'unclaimed').length;
  const inProg = cases.filter((c) => c.status === 'in-progress').length;
  const review = cases.filter((c) => c.status === 'review').length;
  const urgent = cases.filter((c) => c.strDeadlineHrs != null && c.strDeadlineHrs < 48).length;

  const stats = [
    { label: 'Unclaimed Cases', value: unclaimed, delta: '+2 in last 30 min', color: 'border-amber-500 text-amber-400', pulse: false },
    { label: 'In Progress', value: inProg, delta: 'Across 2 analysts', color: 'border-sky-500 text-sky-400', pulse: false },
    { label: 'Pending Senior Review', value: review, delta: 'Avg wait: 38 min', color: 'border-violet-500 text-violet-400', pulse: false },
    { label: 'Approaching STR Deadline', value: urgent, delta: 'FIU-IND · < 48h', color: 'border-red-500 text-red-400', pulse: true },
  ];

  return (
    <div className="view flex h-full flex-col overflow-hidden">
      <ScrollArea className="h-full">
        <div className="flex h-full flex-col px-[22px] pt-[18px]">
          <div className="mb-3.5 flex items-baseline justify-between">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Case Pool</h1>
              <p className="mt-0.5 text-xs text-muted-foreground">Shared queue · {filtered.length} of {cases.length} cases shown</p>
            </div>
            <Badge variant="outline" className="font-mono text-[11px] font-normal text-muted-foreground">
              Logged in as <span className="text-primary">{userName}</span> — {user?.role || 'Analyst L1'} — {user?.branch || ''}
            </Badge>
          </div>

          <div className="mb-4 grid grid-cols-4 gap-3">
            {stats.map((stat) => (
              <Card key={stat.label} className={cn('relative overflow-hidden border-border py-3.5', stat.color.split(' ')[0], 'border-l-[3px] border-l-current')}>
                <CardContent className="px-4 py-0">
                  <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{stat.label}</div>
                  <div className={cn('font-mono text-[26px] font-semibold leading-none', stat.color.split(' ')[1], stat.pulse && 'animate-pulse')}>{stat.value}</div>
                  <div className="mt-1.5 font-mono text-[10px] text-muted-foreground">{stat.delta}</div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="mb-3.5 border-violet-500/30 border-l-[3px] border-l-violet-500 bg-gradient-to-r from-violet-500/10 to-transparent py-3">
            <CardContent className="flex items-center gap-3.5 px-3.5 py-0">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-sm text-violet-400">↑</div>
              <div className="flex-1 text-xs">
                Your workload: <strong className="text-violet-400">2 active</strong>, 1 awaiting senior review by <strong className="text-violet-400">Ravi Kumar</strong>, 1 incoming escalation for your review.
                <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                  <span className="text-emerald-400">● SLA on-track</span> · Next STR deadline <span className="text-foreground">6d 22h</span> · Review-action SLA <span className="text-amber-400">2h 14m remaining</span>
                </div>
              </div>
              <Button variant="sky" size="sm" onClick={() => setFilterStatus('review')}>Show approval queue →</Button>
            </CardContent>
          </Card>

          <div className="mb-3 flex flex-wrap items-center gap-2.5">
            <Label className="mr-1 text-[11px] text-muted-foreground">FILTER</Label>
            <Select value={filterFlag} onValueChange={setFilterFlag}>
              <SelectTrigger className="h-[30px] min-w-[140px] text-xs"><SelectValue placeholder="All Flag Types" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Flag Types</SelectItem>
                {flags.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="h-[30px] min-w-[140px] text-xs"><SelectValue placeholder="All Statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="unclaimed">Unclaimed</SelectItem>
                <SelectItem value="in-progress">In Progress</SelectItem>
                <SelectItem value="review">Pending Review</SelectItem>
                <SelectItem value="ready">STR Ready</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex h-[30px] items-center gap-1.5 rounded-sm border border-input bg-background px-2 font-mono text-[11px] text-muted-foreground">
              <span>Risk</span>
              <Input type="number" value={scoreMin} min={0} max={100} onChange={(e) => setScoreMin(+e.target.value)} className="h-[22px] w-10 border-0 bg-transparent p-0 text-center text-xs shadow-none" />
              <span>—</span>
              <Input type="number" value={scoreMax} min={0} max={100} onChange={(e) => setScoreMax(+e.target.value)} className="h-[22px] w-10 border-0 bg-transparent p-0 text-center text-xs shadow-none" />
            </div>
            <Input className="h-[30px] min-w-[220px] text-xs" placeholder="Search Account ID or Case ID…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>

          <Card className="mb-[18px] flex-1 overflow-hidden py-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  {[
                    ['id', 'Case ID'], ['account', 'Account'], ['score', 'Risk'], ['flag', 'Flag'],
                    ['status', 'Status'], ['claimedBy', 'Claimed By'], ['openedMin', 'Time Open'],
                    ['strDeadlineHrs', 'STR Deadline'], [null, ''],
                  ].map(([key, label]) => (
                    <TableHead key={label || 'actions'} className={cn('sticky top-0 z-10 bg-secondary text-[10px] uppercase tracking-wider text-muted-foreground', key && 'cursor-pointer select-none hover:text-foreground')} onClick={key ? () => toggleSort(key) : undefined}>
                      {label} {key && sortInd(key) && <span className="ml-1 text-primary">{sortInd(key)}</span>}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((c) => {
                  const isMine = c.claimedBy === userName;
                  const isUnclaimed = c.status === 'unclaimed';
                  const isClosed = c.status === 'closed';
                  const countdownClass = c.strDeadlineHrs != null
                    ? c.strDeadlineHrs < 24 ? 'text-red-400 font-semibold animate-pulse' : c.strDeadlineHrs < 48 ? 'text-amber-400' : 'text-muted-foreground'
                    : 'text-muted-foreground';
                  return (
                    <TableRow key={c.id} className={cn(isUnclaimed && 'bg-amber-500/[0.03]')}>
                      <TableCell><span className="font-mono font-medium text-primary">{c.id}</span></TableCell>
                      <TableCell>
                        <span className="font-mono">{c.account}</span>
                        <Badge variant="outline" className={cn('ml-1.5 text-[9px] uppercase', c.type === 'Jan Dhan' && 'border-sky-500/30 bg-sky-500/10 text-sky-400')}>{c.type}</Badge>
                      </TableCell>
                      <TableCell><RiskBadge score={c.score} /></TableCell>
                      <TableCell><span className="flex items-center gap-1.5 text-[11px] before:size-1 before:shrink-0 before:rounded-full before:bg-amber-500">{c.flag}</span></TableCell>
                      <TableCell>
                        <StatusBadge status={c.status} />
                        {isClosed && <div className="mt-1 text-[10px] text-muted-foreground">{c.closedReason}</div>}
                      </TableCell>
                      <TableCell>
                        <span className={cn('text-[11px] text-muted-foreground', isUnclaimed && 'font-medium text-amber-400', isMine && 'font-medium text-primary')}>
                          {isUnclaimed ? 'Unclaimed' : c.claimedBy}{isClosed ? ' (closed)' : ''}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">{fmtMin(c.openedMin)}</TableCell>
                      <TableCell><span className={cn('font-mono text-[11px]', countdownClass)}>{fmtHrs(c.strDeadlineHrs)}</span></TableCell>
                      <TableCell>
                        {isClosed ? (
                          <Button variant="ghost" size="sm" disabled className="text-xs">View Only</Button>
                        ) : isUnclaimed ? (
                          <Button size="sm" className="text-xs" onClick={() => claimCase(c.id)}>Claim & Investigate</Button>
                        ) : isMine ? (
                          <Button variant="sky" size="sm" className="text-xs" onClick={() => openCase(c.id)}>Open</Button>
                        ) : (
                          <Button variant="ghost" size="sm" disabled className="text-xs">View Only</Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
