import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchHistory, fetchStatus } from '../api';
import PerformanceChart from '../components/PerformanceChart';
import TradeTable from '../components/TradeTable';

const LABELS = {
  momentum: { name: 'MOMENTUM TRADER', dotColor: 'var(--red)' },
  value: { name: 'VALUE ANALYST', dotColor: 'var(--accent)' },
};

export default function HistoryPage() {
  const { agent } = useParams();
  const [history, setHistory] = useState(null);
  const [agentStatus, setAgentStatus] = useState(null);
  const [error, setError] = useState(null);

  const meta = LABELS[agent];

  useEffect(() => {
    if (!meta) return;

    async function load() {
      try {
        const [hist, status] = await Promise.all([
          fetchHistory(agent, 365),
          fetchStatus(),
        ]);
        setHistory(hist.history);
        setAgentStatus(status.agents[agent]);
        setError(null);
      } catch (e) {
        setError(e.message);
      }
    }

    load();
  }, [agent]);

  if (!meta) return <div className="loading">Unknown agent: {agent}</div>;

  return (
    <>
      <div className="header">
        <h1 className="mono">STOCK AGENT COMPETITION</h1>
      </div>

      <Link to="/" className="back-link">← Back to Dashboard</Link>

      <div style={styles.agentHeader}>
        <span style={{ ...styles.dot, background: meta.dotColor }} />
        <span className="mono" style={{ fontSize: 16, fontWeight: 600 }}>{meta.name}</span>
        {agentStatus && (
          <span className={`mono ${agentStatus.total_return_pct >= 0 ? 'positive' : 'negative'}`} style={{ marginLeft: 'auto', fontSize: 18, fontWeight: 600 }}>
            ${Math.round(agentStatus.current_value).toLocaleString()}
            <span style={{ fontSize: 13, marginLeft: 8 }}>
              ({agentStatus.total_return_pct >= 0 ? '+' : ''}{agentStatus.total_return_pct.toFixed(2)}%)
            </span>
          </span>
        )}
      </div>

      {error && <div className="loading">Error: {error}</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <PerformanceChart history={history} />
        <TradeTable history={history} />
      </div>
    </>
  );
}

const styles = {
  agentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 20,
    padding: '12px 20px',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
  },
  dot: { width: 10, height: 10, borderRadius: '50%', display: 'inline-block' },
};
