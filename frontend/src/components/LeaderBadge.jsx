const fmt$ = (v) => '$' + Math.round(v).toLocaleString();

export default function LeaderBadge({ status }) {
  if (!status) return <span className="mono" style={styles.badge}>Loading...</span>;

  const m = status.agents.momentum.current_value;
  const v = status.agents.value.current_value;

  if (status.leader === 'tied') {
    return <span className="mono" style={styles.badge}>TIED</span>;
  }

  const lead = Math.abs(m - v);
  const winner = status.leader === 'momentum' ? 'MOMENTUM' : 'VALUE';
  const pct = ((lead / 100000) * 100).toFixed(2);

  return (
    <span className="mono" style={styles.badge}>
      Leader: {winner} +{fmt$(lead)} (+{pct}%)
    </span>
  );
}

const styles = {
  badge: {
    fontSize: 13,
    padding: '6px 14px',
    borderRadius: 20,
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    whiteSpace: 'nowrap',
  },
};
