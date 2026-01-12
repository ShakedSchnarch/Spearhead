export function PlatoonCard({ name, coverage, onSelect, isActive, anomalyLabel, logo }) {
  const anomaly = coverage?.anomaly;
  const anomalyText = anomaly ? anomalyLabel || anomaly : null;
  return (
    <button className={`platoon-card ${isActive ? "active" : ""}`} onClick={() => onSelect(name)}>
      <div className="platoon-card__header">
        <div className="platoon-card__title">
          <span className="platoon-name">{name}</span>
          {anomaly && <span className="badge warn">אנומליה</span>}
        </div>
        {logo && <img src={logo} alt={name} className="platoon-logo" />}
      </div>
      <div className="platoon-card__metrics">
        <div>
          <div className="metric-label">טפסים</div>
          <div className="metric-value">{coverage?.forms ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">טנקים מדווחים</div>
          <div className="metric-value">{coverage?.distinct_tanks ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">ימים ללא דיווח</div>
          <div className="metric-value">{coverage?.days_since_last ?? "-"}</div>
        </div>
      </div>
      <div className="platoon-card__footer">
        {anomaly ? <span className="muted">סיבה: {anomalyText}</span> : <span className="muted">מצב תקין</span>}
      </div>
    </button>
  );
}
