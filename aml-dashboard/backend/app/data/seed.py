"""Seed data mirroring src/data/constants.js — used until persistence is added."""

CURRENT_USER = {
    "name": "Priya Venkatesh",
    "role": "Analyst L1",
    "branch": "Madurai South Branch",
    "initials": "PV",
}

TEAM = [
    {"handle": "ArjunKrishnan", "name": "Arjun Krishnan", "role": "Analyst L1"},
    {"handle": "RaviSenior", "name": "Ravi Kumar", "role": "Senior AML Officer"},
    {"handle": "ComplianceOfficer", "name": "Meera Iyer", "role": "Compliance Officer"},
]

CASES = [
    {
        "id": "IOB-2024-MU-4471",
        "account": "AC7823901",
        "type": "Jan Dhan",
        "score": 91,
        "flag": "Jan Dhan Spike",
        "status": "in-progress",
        "claimedBy": "Priya Venkatesh",
        "openedMin": 4,
        "strDeadlineHrs": 167,
    },
    {
        "id": "IOB-2024-MU-4469",
        "account": "AC6634821",
        "type": "Savings",
        "score": 78,
        "flag": "Gulf Remittance Layering",
        "status": "unclaimed",
        "claimedBy": None,
        "openedMin": 12,
        "strDeadlineHrs": 167,
    },
    {
        "id": "IOB-2024-MU-4465",
        "account": "AC5521034",
        "type": "Jan Dhan",
        "score": 67,
        "flag": "Fan-Out Structure",
        "status": "in-progress",
        "claimedBy": "Arjun Krishnan",
        "openedMin": 31,
        "strDeadlineHrs": 166,
    },
    {
        "id": "IOB-2024-MU-4461",
        "account": "AC4409127",
        "type": "Savings",
        "score": 44,
        "flag": "Dormancy Break",
        "status": "review",
        "claimedBy": "Priya Venkatesh",
        "openedMin": 72,
        "strDeadlineHrs": 166,
    },
    {
        "id": "IOB-2024-MU-4458",
        "account": "AC3312045",
        "type": "Current",
        "score": 38,
        "flag": "Velocity Spike",
        "status": "closed",
        "claimedBy": "Arjun Krishnan",
        "openedMin": 124,
        "strDeadlineHrs": None,
        "closedReason": "False Positive",
    },
    {
        "id": "IOB-2024-MU-4447",
        "account": "AC2201938",
        "type": "Jan Dhan",
        "score": 88,
        "flag": "DBT Subsidy Diversion",
        "status": "unclaimed",
        "claimedBy": None,
        "openedMin": 47,
        "strDeadlineHrs": 23.23,
        "urgent": True,
    },
]

ACCOUNT_PROFILE = {
    "account": "AC7823901",
    "type": "Jan Dhan",
    "opened": "14 months ago",
    "dormant": "11 months before this event",
    "branch": "Madurai South",
    "kyc": "Basic eKYC",
    "mobile": "94XXXXXXX4",
    "pan": "BXXXX1234X",
    "balanceBefore": "₹340",
    "balancePeak": "₹4,90,340",
    "balanceCurrent": "₹2,340",
}

TIMELINE = [
    {"t": "14:31:02", "dir": "credit", "amt": 490000, "party": "AC1029384", "channel": "IMPS", "flag": "Large credit to dormant Jan Dhan"},
    {"t": "14:32:44", "dir": "debit", "amt": 240000, "party": "AC8834721", "channel": "UPI", "flag": "Shared device fingerprint with recipient"},
    {"t": "14:33:11", "dir": "debit", "amt": 200000, "party": "AC9921045", "channel": "UPI", "flag": "Recipient account 9 days old"},
    {"t": "14:33:58", "dir": "debit", "amt": 45000, "party": "AC3301928", "channel": "ATM", "flag": "ATM cash-out node"},
    {"t": "14:34:22", "dir": "debit", "amt": 2000, "party": "AC7710293", "channel": "UPI", "flag": "Possible test ping pattern"},
]

GRAPH_NODES = [
    {"id": "AC1029384", "label": "VICTIM", "role": "victim", "color": "#ef4444", "size": 26, "balance": "₹12,40,000", "type": "Savings", "note": "Funds origin — likely phishing victim"},
    {"id": "AC7823901", "label": "PRIMARY", "role": "primary", "color": "#f59e0b", "size": 38, "balance": "₹2,340", "type": "Jan Dhan", "note": "Primary mule under investigation"},
    {"id": "AC8834721", "label": "RELAY-1", "role": "relay", "color": "#f59e0b", "size": 28, "balance": "₹8,400", "type": "Savings", "note": "Linked to case IOB-2024-MU-4465"},
    {"id": "AC9921045", "label": "RELAY-2", "role": "relay", "color": "#f59e0b", "size": 28, "balance": "₹1,200", "type": "Savings", "note": "Account opened 9 days ago"},
    {"id": "AC3301928", "label": "CASH-OUT", "role": "cashout", "color": "#8b5cf6", "size": 32, "balance": "—", "type": "ATM", "note": "ATM withdrawal endpoint"},
    {"id": "AC7710293", "label": "LINKED", "role": "linked", "color": "#94a3b8", "size": 20, "balance": "₹620", "type": "Savings", "note": "Possible test-ping account"},
]

GRAPH_LINKS = [
    {"source": "AC1029384", "target": "AC7823901", "amt": 490000, "t": "14:31:02", "channel": "IMPS"},
    {"source": "AC7823901", "target": "AC8834721", "amt": 240000, "t": "14:32:44", "channel": "UPI"},
    {"source": "AC7823901", "target": "AC9921045", "amt": 200000, "t": "14:33:11", "channel": "UPI"},
    {"source": "AC7823901", "target": "AC3301928", "amt": 45000, "t": "14:33:58", "channel": "ATM"},
    {"source": "AC7823901", "target": "AC7710293", "amt": 2000, "t": "14:34:22", "channel": "UPI"},
]

RISK_SIGNALS = [
    {
        "id": "pass",
        "title": "Pass-Through Pattern",
        "pts": 28,
        "desc": "94% outward ratio within 90 seconds",
        "highlight": {"type": "node", "id": "AC7823901"},
        "rule": "RULE_PASS_THROUGH_90S",
        "formula": "Σ(outflow within 90s) ÷ inflow_amount  ≥  0.85",
        "evidence": [
            {"k": "Inflow", "v": "₹4,90,000 from AC1029384 @ 14:31:02"},
            {"k": "Out #1", "v": "₹2,40,000 → AC8834721 (+1m42s)"},
            {"k": "Out #2", "v": "₹2,00,000 → AC9921045 (+2m09s)"},
            {"k": "Out #3", "v": "₹45,000 → AC3301928 (+2m56s)"},
            {"k": "Window Σ", "v": "₹4,85,000 of ₹4,90,000", "emp": True},
            {"k": "Ratio", "v": "98.98% (threshold 85%)", "emp": True},
        ],
        "model": {"weight": "0.30", "precision": "0.87", "trained": "12,400"},
        "trace": "Triggered by alert ALT-7741293 · evaluated against feature vector v3.2.1 · last calibrated 2024-Q3",
    },
    {
        "id": "device",
        "title": "Device Sharing",
        "pts": 22,
        "desc": "Same device fingerprint as AC8834721 (case IOB-2024-MU-4465)",
        "highlight": {"type": "edge", "from": "AC7823901", "to": "AC8834721"},
        "rule": "RULE_DEVICE_REUSE",
        "formula": "device_hash(a) == device_hash(b)  WHERE  a ≠ b  AND  Δt < 24h",
        "evidence": [
            {"k": "Device", "v": "sha256: 4c9e…b8f2 (Android 13)"},
            {"k": "On AC7823901", "v": "logged in 14:28:14"},
            {"k": "On AC8834721", "v": "logged in 14:34:51"},
            {"k": "Δt", "v": "6m 37s", "emp": True},
            {"k": "X-ref", "v": "Case IOB-2024-MU-4465 (Arjun K.)", "link": "IOB-2024-MU-4465"},
        ],
        "model": {"weight": "0.24", "precision": "0.91", "trained": "8,720"},
        "trace": "Device graph join · cross-case correlation engine · matches strengthened by IP overlap",
    },
    {
        "id": "dormancy",
        "title": "Dormancy Break",
        "pts": 18,
        "desc": "Account inactive 11 months before this event",
        "highlight": {"type": "node", "id": "AC7823901"},
        "rule": "RULE_DORMANCY_BREAK",
        "formula": "idle_days > 90  AND  credit_spike > 50× rolling_avg",
        "evidence": [
            {"k": "Last activity", "v": "2023-06-14 (337 days ago)"},
            {"k": "Prior avg", "v": "₹340 / month"},
            {"k": "This credit", "v": "₹4,90,000 — 1,441×", "emp": True},
            {"k": "Account age", "v": "14 months (eligible)"},
        ],
        "model": {"weight": "0.18", "precision": "0.79", "trained": "4,100"},
        "trace": "Behavioural baseline drawn from 14-month account history",
    },
    {
        "id": "fanout",
        "title": "Fan-Out Structure",
        "pts": 16,
        "desc": "1 credit source, 4 debit destinations in 3 minutes",
        "highlight": {"type": "node", "id": "AC7823901"},
        "rule": "RULE_FANOUT_STRUCTURE",
        "formula": "distinct_recipients(window=300s)  ≥  3",
        "evidence": [
            {"k": "Recipients", "v": "AC8834721, AC9921045, AC3301928, AC7710293"},
            {"k": "Window", "v": "14:32:44 — 14:34:22 (98s)"},
            {"k": "Distinct", "v": "4 of 4 unique", "emp": True},
            {"k": "Channels", "v": "UPI × 3, ATM × 1"},
        ],
        "model": {"weight": "0.16", "precision": "0.74", "trained": "9,800"},
        "trace": "Structural graph match · isomorphic to known mule topology M-12",
    },
    {
        "id": "spike",
        "title": "Jan Dhan Spike",
        "pts": 12,
        "desc": "Amount is 47x average Jan Dhan transaction at this branch",
        "highlight": {"type": "node", "id": "AC7823901"},
        "rule": "RULE_JANDHAN_SPIKE",
        "formula": "txn_amount  >  percentile(branch_jandhan, 99.9)",
        "evidence": [
            {"k": "Branch", "v": "Madurai South (BR-4471)"},
            {"k": "Br. avg", "v": "₹10,400 (n=18,400 txns/mo)"},
            {"k": "This txn", "v": "₹4,90,000 — 47.1× avg", "emp": True},
            {"k": "Percentile", "v": "99.97th of branch", "emp": True},
        ],
        "model": {"weight": "0.12", "precision": "0.68", "trained": "21,600"},
        "trace": "Branch-level distribution refreshed nightly · n=18,400 transactions sampled",
    },
    {
        "id": "new",
        "title": "New Account Link",
        "pts": 8,
        "desc": "AC9921045 opened 9 days ago",
        "highlight": {"type": "node", "id": "AC9921045"},
        "rule": "RULE_NEW_ACCOUNT_LINK",
        "formula": "exists(neighbor n WHERE age_days(n) < 30)",
        "evidence": [
            {"k": "Counterparty", "v": "AC9921045"},
            {"k": "Opened", "v": "2024-05-13 (9 days ago)", "emp": True},
            {"k": "KYC", "v": "Basic eKYC, mobile-only"},
            {"k": "Prior txns", "v": "0 inbound, 0 outbound (pre-event)"},
        ],
        "model": {"weight": "0.08", "precision": "0.63", "trained": "15,200"},
        "trace": "Account-age check on N+1 neighbour set",
    },
]

AUDIT_LOG = [
    {"ts": "14:30:58", "actor": "TM-ENGINE", "action": "Alert generated · ALT-7741293", "hash": "a3f8…21bc"},
    {"ts": "14:31:03", "actor": "AML-SYS", "action": "Case IOB-2024-MU-4471 created from alert", "hash": "b1e4…8a09"},
    {"ts": "14:31:04", "actor": "AML-SYS", "action": "Graph pre-loaded · 6 nodes, 5 edges", "hash": "9c2d…ff71"},
    {"ts": "14:34:21", "actor": "P.Venkatesh", "action": "Case claimed", "hash": "d8a7…42b0"},
    {"ts": "14:34:21", "actor": "AML-SYS", "action": "Status → IN_PROGRESS", "hash": "7e1f…6d3a"},
    {"ts": "14:36:04", "actor": "P.Venkatesh", "action": "Note added (audit-1)", "hash": "5b9c…118e"},
    {"ts": "14:36:42", "actor": "P.Venkatesh", "action": "Risk signal expanded: PASS_THROUGH_90S", "hash": "2a44…cd91"},
    {"ts": "14:37:19", "actor": "P.Venkatesh", "action": "Confidence updated → 87%", "hash": "8f10…7704"},
]

SUMMARY_EN = (
    "This Jan Dhan account received ₹4.9 lakh and forwarded 94% of it within 90 seconds across four accounts. "
    "The account was dormant for 11 months before this event. The primary receiving device matches a previously "
    "flagged mule account in case IOB-2024-MU-4465. This pattern is consistent with a coordinated pass-through mule operation."
)

SUMMARY_TA = (
    "இந்த ஜன் தன் கணக்கு ₹4.9 லட்சம் பெற்று 90 வினாடிகளில் நான்கு கணக்குகளுக்கு 94% அனுப்பியது. "
    "இந்த கணக்கு 11 மாதங்களாக செயலற்று இருந்தது. முதன்மை பெறும் சாதனத்தின் கைரேகை, முன்பு கண்டறியப்பட்ட "
    "ஒரு மியூல் கணக்துடன் (வழக்கு IOB-2024-MU-4465) பொருந்துகிறது. இந்த முறை ஒருங்கிணைந்த pass-through மியூல் செயல்பாட்டுக்கு ஒத்துப்போகிறது."
)

INITIAL_NOTES = [
    {
        "id": 2,
        "kind": "system",
        "author": "AML Shield System",
        "role": "Auto",
        "time": "14:34:21",
        "body": "Case auto-created from Transaction Monitoring Engine. Triggered rules: JANDHAN_SPIKE, PASS_THROUGH_90S, DEVICE_REUSE. Graph pre-loaded with 6 connected nodes.",
    },
    {
        "id": 1,
        "kind": "user",
        "author": "Priya Venkatesh",
        "role": "Analyst L1",
        "time": "14:36:04",
        "body": "Claimed case. Initial review confirms pass-through pattern. Device fingerprint match with IOB-2024-MU-4465 is significant — same device used to access both accounts within 6 minutes. Recommending confirm mule.",
    },
]

INITIAL_NOTIFICATIONS = [
    {
        "id": 1,
        "type": "deadline",
        "color": "#ef4444",
        "icon": "⏱",
        "title": "STR Deadline Alert",
        "time": "2 min ago",
        "msg": 'Case <span class="case-ref">IOB-2024-MU-4447</span> STR filing deadline in 23 hours 14 minutes. Case currently unclaimed.',
        "action": "Claim Now",
        "caseId": "IOB-2024-MU-4447",
    },
    {
        "id": 2,
        "type": "mention",
        "color": "#0ea5e9",
        "icon": "@",
        "title": "@Mention",
        "time": "8 min ago",
        "msg": 'Arjun Krishnan mentioned you in <span class="case-ref">IOB-2024-MU-4465</span>: <em>"<span class="mention">@PriyaVenkatesh</span> the device fingerprint on your case 4471 matches our relay node here — possible same ring"</em>',
        "action": "View Case",
        "caseId": "IOB-2024-MU-4465",
    },
    {
        "id": 3,
        "type": "escalation",
        "color": "#f59e0b",
        "icon": "↑",
        "title": "Escalation Received",
        "time": "34 min ago",
        "msg": 'Case <span class="case-ref">IOB-2024-MU-4461</span> escalated to you by Priya Venkatesh for senior review. Priority: Normal.',
        "action": "Review",
        "caseId": "IOB-2024-MU-4461",
    },
    {
        "id": 4,
        "type": "info",
        "color": "#64748b",
        "icon": "✓",
        "title": "Case Update",
        "time": "1hr ago",
        "msg": 'Arjun Krishnan closed case <span class="case-ref">IOB-2024-MU-4458</span> as False Positive — Legitimate business account.',
        "action": "View",
        "caseId": "IOB-2024-MU-4458",
    },
    {
        "id": 5,
        "type": "deadline",
        "color": "#ef4444",
        "icon": "!",
        "title": "New Critical Case",
        "time": "1hr 12min ago",
        "msg": 'New critical case auto-generated: <span class="case-ref">IOB-2024-MU-4461</span>. Risk Score 88. Flag: DBT Subsidy Diversion. Unclaimed.',
        "action": "Claim",
        "caseId": "IOB-2024-MU-4461",
    },
]

STR_DRAFT_NARRATIVE = """Account AC7823901, a Jan Dhan account held at Madurai South Branch (IOB), received an IMPS credit of ₹4,90,000 on 22 May 2024 at 14:31:02 IST from account AC1029384. Within 90 seconds of receipt, ₹4,85,000 (98.98% of the credited funds) was transferred outward across four separate accounts via UPI and ATM channels, consistent with a structured pass-through mule pattern (Rule: PASS_THROUGH_90S).

The subject account had been dormant for 11 months prior to this transaction, with a pre-event average monthly balance of ₹340. The incoming credit of ₹4,90,000 represents a 1,441x deviation from the account's established baseline and falls at the 99.97th percentile for Jan Dhan transactions at this branch (47x branch average of ₹10,400).

Device forensics confirm that the mobile device used to authorise outgoing UPI transfers from AC7823901 (device hash: 4c9e…b8f2, Android 13) was also used to access account AC8834721 within the same session window (Δt: 6m 37s). AC8834721 is currently under active investigation in case IOB-2024-MU-4465 as a confirmed relay node. This cross-case device linkage indicates coordinated control of multiple accounts by a single actor or group.

Recipient AC9921045, which received ₹2,00,000 via UPI, was opened 9 days prior to this transaction with basic eKYC and no prior transaction history, consistent with a freshly activated mule account.

The structural pattern — single large inbound credit, rapid fan-out to four distinct destinations including an ATM cash-out node (AC3301928) — matches known mule network topology M-12 flagged by the Financial Intelligence Unit."""

STR_CITE_SEGMENTS = [
    {"text": "received an IMPS credit of ₹4,90,000", "highlight": {"type": "edge", "from": "AC1029384", "to": "AC7823901"}, "chipId": "pass"},
    {"text": "98.98% of the credited funds", "highlight": {"type": "node", "id": "AC7823901"}, "chipId": "pass"},
    {"text": "device used to authorise outgoing UPI transfers", "highlight": {"type": "edge", "from": "AC7823901", "to": "AC8834721"}, "chipId": "device"},
    {"text": "dormant for 11 months prior", "highlight": {"type": "node", "id": "AC7823901"}, "chipId": "dormancy"},
    {"text": "AC9921045, which received ₹2,00,000", "highlight": {"type": "node", "id": "AC9921045"}, "chipId": "new"},
    {"text": "single large inbound credit, rapid fan-out", "highlight": {"type": "node", "id": "AC7823901"}, "chipId": "fanout"},
]

STR_EVIDENCE_CHIPS = [
    {"id": "pass", "label": "PASS_THROUGH_90S", "cls": "chip-pass", "checked": True},
    {"id": "device", "label": "DEVICE_REUSE", "cls": "chip-device", "checked": True},
    {"id": "dormancy", "label": "DORMANCY_BREAK", "cls": "chip-dormancy", "checked": True},
    {"id": "fanout", "label": "FAN_OUT_M-12", "cls": "chip-fanout", "checked": True},
    {"id": "spike", "label": "JANDHAN_SPIKE", "cls": "chip-spike", "checked": True},
    {"id": "new", "label": "NEW_ACCT_LINK", "cls": "chip-new", "checked": True},
    {"id": "case", "label": "× IOB-2024-MU-4465", "cls": "chip-linked-case", "checked": True},
]

COMPLIANCE_ITEMS = [
    {"label": "Account holder identity verified (eKYC)", "status": "ok", "icon": "✓"},
    {"label": "Transaction amount ≥ ₹10 lakh threshold", "status": "fail", "icon": "✗", "note": "₹4.9L — below FIU threshold; file on pattern grounds"},
    {"label": "Pattern-based reporting criteria met", "status": "ok", "icon": "✓"},
    {"label": "Cross-case linkage documented", "status": "ok", "icon": "✓"},
    {"label": "Senior officer review required", "status": "warn", "icon": "!"},
    {"label": "Filing deadline: 7 days (167h remaining)", "status": "ok", "icon": "✓"},
]

STR_ENTITIES = [
    {"account": "AC7823901", "type": "Jan Dhan", "role": "Primary mule", "amount": "₹4,90,000 in / ₹4,85,000 out", "note": "Subject account under investigation"},
    {"account": "AC1029384", "type": "Savings", "role": "Victim / source", "amount": "₹4,90,000 credit", "note": "Likely phishing victim — funds origin"},
    {"account": "AC8834721", "type": "Savings", "role": "Relay node", "amount": "₹2,40,000", "note": "Linked case IOB-2024-MU-4465 · shared device"},
    {"account": "AC9921045", "type": "Savings", "role": "Relay node", "amount": "₹2,00,000", "note": "Account opened 9 days prior"},
    {"account": "AC3301928", "type": "ATM", "role": "Cash-out", "amount": "₹45,000", "note": "ATM withdrawal endpoint"},
    {"account": "AC7710293", "type": "Savings", "role": "Linked", "amount": "₹2,000", "note": "Possible test-ping account"},
]

# Primary demo case — investigation data is keyed here until per-case DB exists
PRIMARY_CASE_ID = "IOB-2024-MU-4471"

GEN_STEPS = [
    "Extracting risk signals…",
    "Loading transaction evidence…",
    "Cross-referencing device data…",
    "Composing narrative…",
    "Populating entity fields…",
]
