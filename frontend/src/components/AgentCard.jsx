import { Link } from 'react-router-dom';

const CONF_STARS = { high: '★★★', medium: '★★☆', low: '★☆☆' };
const fmt$ = (v) => '$' + Math.round(v).toLocaleString();

function SignalPill({ signal }) {
  const s = (signal || 'neutral').toLowerCase();
  const cls =
    s === 'bullish' ? 'signal-bullish' :
    s === 'bearish' ? 'signal-bearish' : 'signal-neutral';
  return <span className={`signal-pill ${cls}`}>{s}</span>;
}

export default function AgentCard({ name, label, dotColor, data, history }) {
  if (!data) return null;

  const ret = data.total_return_pct;
  const retSign = ret >= 0 ? '+' : '';
  const portfolio = data.last_portfolio?.portfolio || [];
  const sorted = [...portfolio].sort((a, b) => b.weight_pct - a.weight_pct);
  const reversedHist = [...(history || [])].reverse();

  return (
    <div className="card">
      <div style={styles.header}>
        <div className="mono" style={styles.name}>
          <span style={{ ...styles.dot, background: dotColor }} />
          {label}
        </div>
        <div className={`mono ${ret >= 0 ? 'positive' : 'negative'}`} style={styles.value}>
          {fmt$(data.current_value)}
        </div>
      </div>

      <div style={styles.statsRow}>
        <Stat label="Return" value={`${retSign}${ret.toFixed(2)}%`} cls={ret >= 0 ? 'positive' : 'negative'} />
        <Stat label="Cash" value={fmt$(data.cash)} />
        <Stat label="Days" value={data.days_tracked} />
        <Stat label="Trades" value={data.total_trades} />
        <Stat label="Fees" value={fmt$(data.total_fees)} />
      </div>

      <div className="section-title">
        Holdings
        <Link to={`/history/${name}`} style={styles.histLink}>View History →</Link>
      </div>

      <table>
        <thead>
          <tr><th>Ticker</th><th>Weight</th><th>Shares</th><th>Signal</th><th>Conf</th></tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr><td colSpan={5} style={{ color: 'var(--text-muted)' }}>No holdings yet</td></tr>
          ) : sorted.map((h) => (
            <tr key={h.ticker}>
              <td style={{ fontWeight: 600 }}>{h.ticker}</td>
              <td>{h.weight_pct}%</td>
              <td>{data.holdings?.[h.ticker] || 0}</td>
              <td><SignalPill signal={h.signal} /></td>
              <td style={{ color: 'var(--yellow)', letterSpacing: 1 }}>{CONF_STARS[h.confidence] || CONF_STARS.low}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-title" style={{ marginTop: 8 }}>Recent Activity</div>
      <div style={styles.activityList}>
        {reversedHist.length === 0 ? (
          <div style={styles.activityEntry}>
            <span style={{ color: 'var(--text-muted)' }}>No activity yet</span>
          </div>
        ) : reversedHist.slice(0, 10).map((day) => (
          <div key={day.date} style={styles.activityEntry}>
            <div className="mono" style={styles.activityDate}>
              {day.date}
              {day.trades > 0 && ` — ${day.trades} trade${day.trades > 1 ? 's' : ''}, ${fmt$(day.trade_cost)} fees`}
            </div>
            {day.trades === 0 ? (
              <span style={{ color: 'var(--text-muted)' }}>No changes (held)</span>
            ) : (
              <span className="mono" style={{ fontSize: 12 }}>
                {(day.portfolio?.portfolio || []).map(h => h.ticker).join(', ')}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value, cls }) {
  return (
    <div style={styles.stat}>
      <span style={styles.statLabel}>{label}</span>
      <span className={`mono ${cls || ''}`} style={styles.statValue}>{value}</span>
    </div>
  );
}

const styles = {
  header: {
    padding: '16px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--border)',
  },
  name: { fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: '50%', display: 'inline-block' },
  value: { fontSize: 20, fontWeight: 600 },
  statsRow: {
    display: 'flex',
    gap: 20,
    padding: '12px 20px',
    borderBottom: '1px solid var(--border)',
    fontSize: 13,
  },
  stat: { display: 'flex', flexDirection: 'column', gap: 2 },
  statLabel: { color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  statValue: { fontSize: 13, fontWeight: 600 },
  histLink: { float: 'right', fontSize: 11, letterSpacing: 0, textTransform: 'none', fontWeight: 500 },
  activityList: { padding: '8px 20px 16px', maxHeight: 280, overflowY: 'auto' },
  activityEntry: { padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 12 },
  activityDate: { color: 'var(--text-muted)', fontSize: 11, marginBottom: 4 },
};
