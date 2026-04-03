import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchPrices } from '../api';

const CONF_STARS = { high: '★★★', medium: '★★☆', low: '★☆☆' };
const fmt$ = (v) => '$' + Math.round(v).toLocaleString();

function SignalPill({ signal }) {
  const s = (signal || 'neutral').toLowerCase();
  const cls =
    s === 'bullish' ? 'signal-bullish' :
    s === 'bearish' ? 'signal-bearish' : 'signal-neutral';
  return <span className={`signal-pill ${cls}`}>{s}</span>;
}

export default function AgentCard({ name, label, dotColor, data, history, locked, promptText, onDelete }) {
  if (!data) return null;
  const [strategyOpen, setStrategyOpen] = useState(false);
  const [prices, setPrices] = useState({});
  const [expandedTicker, setExpandedTicker] = useState(null);

  const portfolio = data.last_portfolio?.portfolio || [];
  const sorted = [...portfolio].sort((a, b) => b.weight_pct - a.weight_pct);
  const costBasis = data.last_portfolio?.cost_basis || {};

  useEffect(() => {
    const tickers = (data.last_portfolio?.portfolio || []).map(h => h.ticker);
    if (tickers.length === 0) return;
    fetchPrices(tickers).then(setPrices).catch(() => {});
  }, [data.last_portfolio]);

  const ret = data.total_return_pct;
  const retSign = ret >= 0 ? '+' : '';
  const reversedHist = [...(history || [])].reverse();

  return (
    <div className="card">
      <div style={styles.header}>
        <div className="mono" style={styles.name}>
          <span style={{ ...styles.dot, background: dotColor }} />
          {label}
          {locked && (
            <span style={styles.builtinBadge}>Built-in</span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className={`mono ${ret >= 0 ? 'positive' : 'negative'}`} style={styles.value}>
            {fmt$(data.current_value)}
          </div>
          {!locked && onDelete && (
            <button onClick={() => onDelete(name)} style={styles.deleteBtn} title="Remove agent">✕</button>
          )}
        </div>
      </div>

      <div style={styles.statsRow}>
        <Stat label="Return" value={`${retSign}${ret.toFixed(2)}%`} cls={ret >= 0 ? 'positive' : 'negative'} />
        <Stat label="Cash" value={fmt$(data.cash)} />
        <Stat label="Days" value={data.days_tracked} />
        <Stat label="Trades" value={data.total_trades} />
        <Stat label="Fees" value={fmt$(data.total_fees)} />
      </div>

      {promptText && (
        <>
          <div
            className="section-title mono"
            onClick={() => setStrategyOpen(o => !o)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
          >
            {strategyOpen ? '▼' : '▶'} Strategy
          </div>
          {strategyOpen && (
            <pre style={styles.strategyBox}>{promptText}</pre>
          )}
        </>
      )}

      <div className="section-title">
        Holdings
        <Link to={`/history/${name}`} style={styles.histLink}>View History →</Link>
      </div>

      <table>
        <thead>
          <tr><th>Ticker</th><th>Weight</th><th>Shares</th><th>Today</th><th>Since Bought</th><th>Signal</th><th>Conf</th></tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr><td colSpan={7} style={{ color: 'var(--text-muted)' }}>No holdings yet</td></tr>
          ) : sorted.map((h) => {
            const p = prices[h.ticker];
            const todayChg = p?.change_pct;
            const currentPrice = p?.price;
            const buyPrice = costBasis[h.ticker];
            const sinceBought = (buyPrice && currentPrice)
              ? ((currentPrice - buyPrice) / buyPrice * 100).toFixed(2)
              : null;
            const isExpanded = expandedTicker === h.ticker;
            return (
              <>
                <tr
                  key={h.ticker}
                  onClick={() => setExpandedTicker(isExpanded ? null : h.ticker)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontWeight: 600 }}>
                    <span style={{ marginRight: 5, color: 'var(--text-muted)', fontSize: 9 }}>{isExpanded ? '▼' : '▶'}</span>
                    {h.ticker}
                  </td>
                  <td>{h.weight_pct}%</td>
                  <td>{data.holdings?.[h.ticker] || 0}</td>
                  <td className={todayChg == null ? '' : todayChg >= 0 ? 'positive' : 'negative'} style={{ fontWeight: 600 }}>
                    {todayChg == null ? <span style={{ color: 'var(--text-muted)' }}>—</span> : `${todayChg >= 0 ? '+' : ''}${todayChg}%`}
                  </td>
                  <td className={sinceBought == null ? '' : sinceBought >= 0 ? 'positive' : 'negative'} style={{ fontWeight: 600 }}>
                    {sinceBought == null
                      ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                      : <span title={`Bought at $${buyPrice}`}>
                          {sinceBought >= 0 ? '+' : ''}{sinceBought}%
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: 10, marginLeft: 4 }}>
                            @${buyPrice}
                          </span>
                        </span>
                    }
                  </td>
                  <td><SignalPill signal={h.signal} /></td>
                  <td style={{ color: 'var(--yellow)', letterSpacing: 1 }}>{CONF_STARS[h.confidence] || CONF_STARS.low}</td>
                </tr>
                {isExpanded && (
                  <tr key={`${h.ticker}-rationale`}>
                    <td colSpan={7} style={styles.rationaleCell}>
                      <span style={styles.rationaleLabel}>Agent reasoning</span>
                      {h.rationale || <span style={{ color: 'var(--text-muted)' }}>No rationale recorded.</span>}
                    </td>
                  </tr>
                )}
              </>
            );
          })}
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
  builtinBadge: {
    fontSize: 9, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase',
    background: 'var(--border)', color: 'var(--text-muted)', padding: '2px 5px', borderRadius: 3,
  },
  deleteBtn: {
    background: 'none', border: '1px solid var(--border)', color: 'var(--text-muted)',
    borderRadius: 4, cursor: 'pointer', fontSize: 12, padding: '2px 7px', lineHeight: 1,
  },
  rationaleCell: {
    background: 'var(--bg)',
    padding: '10px 16px',
    fontSize: 12,
    color: 'var(--text-muted)',
    borderTop: 'none',
    lineHeight: 1.6,
  },
  rationaleLabel: {
    display: 'block',
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: 'var(--text-muted)',
    marginBottom: 4,
  },
  strategyBox: {
    margin: '0 20px 0', padding: '10px 12px',
    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4,
    fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    maxHeight: 160, overflowY: 'auto', fontFamily: 'inherit',
  },
};
