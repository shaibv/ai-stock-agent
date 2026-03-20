import { useState, useEffect } from 'react';
import { fetchStatus, fetchHistory, triggerRun } from '../api';
import LeaderBadge from '../components/LeaderBadge';
import AgentCard from '../components/AgentCard';

const AGENTS = [
  { key: 'momentum', label: 'MOMENTUM TRADER', dotColor: 'var(--red)' },
  { key: 'value', label: 'VALUE ANALYST', dotColor: 'var(--accent)' },
];

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState({ momentum: [], value: [] });
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [st, mH, vH] = await Promise.all([
          fetchStatus(),
          fetchHistory('momentum', 10),
          fetchHistory('value', 10),
        ]);
        if (!active) return;
        setStatus(st);
        setHistory({ momentum: mH.history, value: vH.history });
        setError(null);
      } catch (e) {
        if (active) setError(e.message);
      }
    }

    load();
    const timer = setInterval(load, 60000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  async function handleRun() {
    setRunning(true);
    setRunMsg(null);
    try {
      const result = await triggerRun();
      setRunMsg(`Run complete — ${result.api_calls_total} API calls used`);
      // Refresh data after run
      const [st, mH, vH] = await Promise.all([
        fetchStatus(),
        fetchHistory('momentum', 10),
        fetchHistory('value', 10),
      ]);
      setStatus(st);
      setHistory({ momentum: mH.history, value: vH.history });
    } catch (e) {
      setRunMsg(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <div className="header">
        <h1 className="mono">STOCK AGENT COMPETITION</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LeaderBadge status={status} />
          <button
            className="mono"
            onClick={handleRun}
            disabled={running}
            style={{
              padding: '6px 16px',
              background: running ? 'var(--text-muted)' : 'var(--accent)',
              color: '#000',
              border: 'none',
              borderRadius: 4,
              cursor: running ? 'not-allowed' : 'pointer',
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 1,
            }}
          >
            {running ? 'RUNNING…' : 'RUN AGENTS'}
          </button>
        </div>
      </div>
      {runMsg && (
        <div className="mono" style={{ textAlign: 'center', padding: '8px 16px', color: runMsg.startsWith('Error') ? 'var(--red)' : 'var(--accent)', fontSize: 12 }}>
          {runMsg}
        </div>
      )}

      {error && (
        <div className="loading">Error: {error}. Is the API running?</div>
      )}

      <div className="grid">
        {AGENTS.map((a) => (
          <AgentCard
            key={a.key}
            name={a.key}
            label={a.label}
            dotColor={a.dotColor}
            data={status?.agents?.[a.key]}
            history={history[a.key]}
          />
        ))}
      </div>

      <div className="mono" style={{ textAlign: 'center', padding: 16, color: 'var(--text-muted)', fontSize: 11 }}>
        Auto-refreshes every 60s
      </div>
    </>
  );
}
