import { useState } from 'react';
import { api } from '@/lib/api.js';
import { exportAudit } from '@/lib/auditExport.js';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

function ModalShell({ open, onClose, dotColor, title, children, footer }) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-lg" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2.5">
            <span className="size-2 rounded-full" style={{ background: dotColor }} />
            {title}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-xs leading-relaxed">{children}</div>
        <DialogFooter>{footer}</DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ActionModal({ kind, caseObj, audit = [], close, toast, onMutated }) {
  const [fpReason, setFpReason] = useState(null);
  const [escalateNote, setEscalateNote] = useState('Please review — senior eyes needed on this case.');
  const [officer, setOfficer] = useState('Ravi Kumar');
  const [priority, setPriority] = useState('critical');
  const [format, setFormat] = useState('PDF');
  const [recipient, setRecipient] = useState('Arjun Krishnan');
  const [reason, setReason] = useState('End of shift — please continue with senior review prep.');

  const finish = (msg, kind = 'green') => {
    const now = new Date().toTimeString().slice(0, 8);
    toast({ kind, title: msg, msg: `${caseObj.id} · ${caseObj.account}`, time: now });
    close();
  };
  const run = async (fn, msg, kind = 'green') => {
    try { await fn(); onMutated?.(); finish(msg, kind); }
    catch { finish('Action failed — backend unreachable', 'warn'); }
  };

  if (!kind) return null;

  if (kind === 'confirm') {
    return (
      <ModalShell
        open
        onClose={close}
        dotColor="var(--red)"
        title="Confirm Mule Account"
        footer={<>
          <Button variant="ghost" onClick={close}>Cancel</Button>
          <Button variant="danger" onClick={() => run(() => api.closeCase(caseObj.id, 'Confirmed Mule'), 'Mule confirmed · case closed', 'red')}>Proceed</Button>
        </>}
      >
        <DialogDescription asChild>
          <p>You are confirming <span className="font-mono text-primary">{caseObj.account}</span> as a mule account. This will:</p>
        </DialogDescription>
        <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
          <li>Place an immediate debit freeze on this account</li>
          <li>Generate a pre-filled STR draft for FIU-IND</li>
          <li>Escalate to Senior Officer for review</li>
          <li>Flag all connected accounts for monitoring</li>
        </ul>
        <p className="text-[11px] text-amber-400">This action is logged to the immutable audit trail and cannot be undone via this interface.</p>
      </ModalShell>
    );
  }

  if (kind === 'fp') {
    const reasons = ['Legitimate business account', 'Remittance from known family member', 'One-time unusual transaction with explanation', 'Other'];
    return (
      <ModalShell open onClose={close} dotColor="var(--green)" title="Mark as False Positive" footer={<>
        <Button variant="ghost" onClick={close}>Cancel</Button>
        <Button variant="success" disabled={!fpReason} onClick={() => run(() => api.closeCase(caseObj.id, fpReason), 'Case closed · false positive')}>Close Case</Button>
      </>}>
        <p>Select a reason for closing this case as false positive:</p>
        <div className="space-y-2">
          {reasons.map((r) => (
            <label key={r} className="flex cursor-pointer items-center gap-2">
              <input type="radio" name="fp" checked={fpReason === r} onChange={() => setFpReason(r)} className="accent-primary" />
              {r}
            </label>
          ))}
        </div>
        <p className="text-[11px] text-muted-foreground">A reason is required. The case will be closed and the account released from monitoring.</p>
      </ModalShell>
    );
  }

  if (kind === 'hold') {
    return (
      <ModalShell open onClose={close} dotColor="var(--amber)" title="Place Debit Hold" footer={<>
        <Button variant="ghost" onClick={close}>Cancel</Button>
        <Button variant="warning" onClick={() => finish('Debit hold placed · 24h', 'warn')}>Place Hold</Button>
      </>}>
        <p>This will temporarily block all outgoing transactions from <span className="font-mono text-primary">{caseObj.account}</span> pending investigation.</p>
        <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
          <li>Incoming transactions will continue normally</li>
          <li>Account holder receives SMS notification</li>
          <li>Duration: 24 hours (renewable)</li>
          <li>Reversible by Senior Officer if needed</li>
        </ul>
      </ModalShell>
    );
  }

  if (kind === 'escalate') {
    return (
      <ModalShell open onClose={close} dotColor="var(--blue)" title="Escalate to Senior Officer" footer={<>
        <Button variant="ghost" onClick={close}>Cancel</Button>
        <Button onClick={() => run(() => api.escalateCase(caseObj.id, officer, escalateNote, priority), `Escalated to ${officer} · ${priority}`, 'blue')}>Send Escalation</Button>
      </>}>
        <div className="space-y-2">
          <Label>Senior Officer</Label>
          <Select value={officer} onValueChange={setOfficer}>
            <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Ravi Kumar">Ravi Kumar — Senior AML Officer, Chennai Regional</SelectItem>
              <SelectItem value="Meera Iyer">Meera Iyer — Compliance Officer, Chennai HQ</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Escalation note</Label>
          <Textarea value={escalateNote} onChange={(e) => setEscalateNote(e.target.value)} className="min-h-[70px] text-xs" />
        </div>
        <div className="space-y-2">
          <Label>Priority</Label>
          <div className="flex gap-1.5">
            {['normal', 'urgent', 'critical'].map((p) => (
              <Button key={p} size="sm" variant={priority === p ? (p === 'normal' ? 'default' : p === 'urgent' ? 'warning' : 'danger') : 'outline'} className="capitalize" onClick={() => setPriority(p)}>{p}</Button>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground">Priority preset based on risk score {caseObj.score}.</p>
        </div>
      </ModalShell>
    );
  }

  if (kind === 'audit') {
    return (
      <Dialog open onOpenChange={(next) => !next && close()}>
        <DialogContent className="sm:max-w-xl" showCloseButton={false}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2.5">
              <span className="size-2 rounded-full bg-primary" />
              Export Audit Trail
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-xs">
            <p>Complete immutable record for case <span className="font-mono text-primary">{caseObj.id}</span>. Every action below is cryptographically chained.</p>
            <div className="flex flex-wrap gap-1.5">
              {['PDF', 'CSV', 'JSON', 'FIU-IND XML'].map((f) => (
                <Badge key={f} variant={format === f ? 'default' : 'outline'} className="cursor-pointer font-mono" onClick={() => setFormat(f)}>{f}</Badge>
              ))}
            </div>
            <div className="audit-preview max-h-[300px] overflow-y-auto rounded-sm border border-border bg-background p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
              {audit.length === 0 && <div>No audit entries yet.</div>}
              {audit.map((row, i) => (
                <div key={i}>
                  <span className="text-muted-foreground">{row.ts}</span>{'  '}
                  <span className="text-primary">[{row.actor}]</span>{'  '}
                  <span className="text-foreground">{row.action}</span>{'  '}
                  <span className="text-[9px] text-muted-foreground">⌐ {row.hash}</span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground">Entries: <span className="font-mono text-foreground">{audit.length}</span> · Append-only chain</p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={close}>Cancel</Button>
            <Button disabled={audit.length === 0} onClick={() => {
              try { const msg = exportAudit(format, caseObj, audit); finish(msg, 'blue'); }
              catch (e) { finish(e?.message === 'popup-blocked' ? 'Enable pop-ups to export PDF' : 'Export failed', 'warn'); }
            }}>Download {format}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  if (kind === 'handoff') {
    return (
      <ModalShell open onClose={close} dotColor="var(--amber)" title="Hand off case" footer={<>
        <Button variant="ghost" onClick={close}>Cancel</Button>
        <Button variant="warning" onClick={() => run(() => api.handoffCase(caseObj.id, recipient, reason), `Case handed off to ${recipient}`, 'warn')}>Send Handoff</Button>
      </>}>
        <p>Transfer ownership of <span className="font-mono text-primary">{caseObj.id}</span> to another analyst. All notes, evidence expansions, and confidence settings travel with the case.</p>
        <div className="space-y-2">
          <Label>Hand off to</Label>
          <Select value={recipient} onValueChange={setRecipient}>
            <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Arjun Krishnan">Arjun Krishnan — L1 Analyst · 3 open cases</SelectItem>
              <SelectItem value="Meera Iyer">Meera Iyer — Compliance Officer · 1 open case</SelectItem>
              <SelectItem value="Unclaimed pool">Return to unclaimed pool</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Handoff note</Label>
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} className="min-h-[70px] text-xs" />
        </div>
        <p className="text-[11px] text-muted-foreground">Recipient will receive a notification with full context. Your access drops to view-only after handoff.</p>
      </ModalShell>
    );
  }

  return null;
}
