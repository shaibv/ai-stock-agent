const BASE = '';

export async function fetchStatus() {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error(`Status API error: ${res.status}`);
  return res.json();
}

export async function fetchHistory(agentName, last = 365) {
  const res = await fetch(`${BASE}/history/${agentName}?last=${last}`);
  if (!res.ok) throw new Error(`History API error: ${res.status}`);
  return res.json();
}

export async function fetchLogs(agentName, days = 30) {
  const res = await fetch(`${BASE}/logs/${agentName}?days=${days}`);
  if (!res.ok) throw new Error(`Logs API error: ${res.status}`);
  return res.text();
}

export async function triggerRun() {
  const res = await fetch(`${BASE}/run`, { method: 'POST' });
  if (res.status === 409) throw new Error('A run is already in progress');
  if (!res.ok) throw new Error(`Run failed: ${res.status}`);
  return res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${BASE}/agents`);
  if (!res.ok) throw new Error(`Agents API error: ${res.status}`);
  return res.json();
}

export async function createAgent(data) {
  const res = await fetch(`${BASE}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (res.status === 409) throw new Error('An agent with that ID already exists');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Create failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPrices(tickers) {
  if (!tickers || tickers.length === 0) return {};
  const res = await fetch(`${BASE}/prices?tickers=${tickers.join(',')}`);
  if (!res.ok) throw new Error(`Prices API error: ${res.status}`);
  const data = await res.json();
  return data.prices;
}

export async function deleteAgent(name) {
  const res = await fetch(`${BASE}/agents/${name}`, { method: 'DELETE' });
  if (res.status === 403) throw new Error('Built-in agents cannot be deleted');
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
  return res.json();
}
