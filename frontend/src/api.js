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
