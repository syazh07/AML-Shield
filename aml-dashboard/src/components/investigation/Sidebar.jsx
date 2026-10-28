
export default function Sidebar({ activeAccount, openCase }) {
  const data = activeAccount;
  return (
    <div className="invest-sidebar scroll">
      <div className="side-section">
        <h3>Account Profile <span className="pill mono">{data.account}</span></h3>
        <div className="kv"><span className="k">Account ID</span><span className="v hl">{data.account}</span></div>
        <div className="kv"><span className="k">Type</span><span className="v">{data.type}</span></div>
        <div className="kv"><span className="k">Opened</span><span className="v">{data.opened}</span></div>
        <div className="kv"><span className="k">Dormant</span><span className="v warn">{data.dormant}</span></div>
        <div className="kv"><span className="k">Branch</span><span className="v">{data.branch}</span></div>
        <div className="kv"><span className="k">KYC Tier</span><span className="v">{data.kyc}</span></div>
        <div className="kv"><span className="k">Mobile</span><span className="v">{data.mobile}</span></div>
        <div className="kv"><span className="k">PAN</span><span className="v">{data.pan}</span></div>
        <div className="kv"><span className="k">Bal. before</span><span className="v">{data.balanceBefore}</span></div>
        <div className="kv"><span className="k">Peak balance</span><span className="v warn">{data.balancePeak}</span></div>
        <div className="kv"><span className="k">Current</span><span className="v">{data.balanceCurrent}</span></div>
      </div>
      <div className="side-section">
        <h3>Case Status</h3>
        <div className="stepper">
          <div className="step done"><div className="step-dot"></div><div className="step-content"><div className="step-title">Alert Generated</div><div className="step-time">14:30:58</div></div></div>
          <div className="step done"><div className="step-dot"></div><div className="step-content"><div className="step-title">Case Created</div><div className="step-time">14:31:03</div></div></div>
          <div className="step done"><div className="step-dot"></div><div className="step-content"><div className="step-title">Claimed by Priya Venkatesh</div><div className="step-time">14:34:21</div></div></div>
          <div className="step current"><div className="step-dot"></div><div className="step-content"><div className="step-title">Investigation In Progress</div><div className="step-time">since 14:34:21</div></div></div>
          <div className="step future"><div className="step-dot"></div><div className="step-content"><div className="step-title">Pending Senior Review</div></div></div>
          <div className="step future"><div className="step-dot"></div><div className="step-content"><div className="step-title">STR Draft Generated</div></div></div>
          <div className="step future"><div className="step-dot"></div><div className="step-content"><div className="step-title">Filed to FIU-IND</div></div></div>
        </div>
      </div>
      <div className="side-section">
        <h3>Related Cases</h3>
        <div className="related-case" onClick={() => openCase && openCase("IOB-2024-MU-4465")}>
          <div className="rc-id">IOB-2024-MU-4465</div>
          <div className="rc-link">shares <span>AC8834721</span> · device fingerprint match</div>
        </div>
      </div>
    </div>
  );
}
