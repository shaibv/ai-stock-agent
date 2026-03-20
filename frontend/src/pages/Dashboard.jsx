import { useState, useEffect } from 'react';
import { fetchStatus, fetchHistory, fetchAgents, deleteAgent, triggerRun } from '../api';
import LeaderBadge from '../components/LeaderBadge';
import AgentCard from '../components/AgentCard';
import AddAgentModal from '../components/AddAgentModal';

export default function Dashboard() {
  const [agents, setAgents] = useState([]);
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState({});
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState(null);
  const [showModal, setShowModal] = useState(false);

  async function loadAgents() {
    const res = await fetchAgents();
    setAgents(res.agents || []);
    return res.agents || [];
  }

  async function loadData(agentList) {
    const list = agentList || agents;
    const names = list.map((a) => a.name);
    const [st, ...histories] = await Promise.all([
      fetchStatus(),
      ...names.map((n) => fetchHistory(n, 10).catch(() => ({ history: [] }))),
    ]);
    setStatus(st);
    const h = {};
    names.forEach((n, i) => { h[n] = histories[i].history; });
    setHistory(h);
  }

  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const list = await loadAgents();
        if (!active) return;
        await loadData(list);
        setError(null);
      } catch (e) {
        if (active) setError(e.message);
      }
    }

    init();
    const timer = setInterval(() => {
      if (active) loadData().catch(() => {});
    }, 60000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  async function handleRun() {
    setRunning(true);
    setRunMsg(null);
    try {
      const result = await triggerRun();
      setRunMsg(`Run complete — ${result.api_calls_total} API calls used`);
      const list = await loadAgents();
      await loadData(list);
    } catch (e) {
      setRunMsg(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  async function handleDelete(name) {
    if (!window.confirm(`Remove agent "${name}"? This cannot be undone.`)) return;
    try {
      await deleteAgent(name);
      const list = await loadAgents();
      await loadData(list);
    } catch (e) {
      alert(e.message);
    }
  }

  async function handleAgentCreated() {
    setShowModal(false);
    const list = await loadAgents();
    await loadData(list);
  }

  return (
    <>
      <div className="header">
        <h1 className="mono">STOCK AGENT COMPETITION</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LeaderBadge status={status} />
          <button
            className="mono"
            onClick={() => setShowModal(true)}
            style={btnStyle('#888888')}
          >
            + ADD AGENT
          </button>
          <button
            className="mono"
            onClick={handleRun}
            disabled={running}
            style={btnStyle(running ? 'var(--text-muted)' : 'var(--accent)', running)}
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
        {agents.map((a) => (
          <AgentCard
            key={a.name}
            name={a.name}
            label={a.display_name}
            dotColor={a.color}
            locked={a.locked}
            promptText={a.prompt_text}
            data={status?.agents?.[a.name]}
            history={history[a.name] || []}
            onDelete={handleDelete}
          />
        ))}
      </div>

      <div className="mono" style={{ textAlign: 'center', padding: 16, color: 'var(--text-muted)', fontSize: 11 }}>
        Auto-refreshes every 60s
      </div>

      {showModal && (
        <AddAgentModal onClose={() => setShowModal(false)} onCreated={handleAgentCreated} />
      )}
    </>
  );
}

function btnStyle(bg, disabled) {
  return {
    padding: '6px 16px',
    background: bg,
    color: bg === 'var(--accent)' || bg === '#4ade80' ? '#000' : '#fff',
    border: '1px solid var(--border)',
    borderRadius: 4,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: 1,
  };
}
