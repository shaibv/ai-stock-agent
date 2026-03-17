import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts';

const fmt$ = (v) => '$' + Math.round(v).toLocaleString();

export default function PerformanceChart({ history, startingCash = 100000 }) {
  if (!history || history.length === 0) {
    return <div className="loading">No history data yet</div>;
  }

  const data = history.map((h) => ({
    date: h.date,
    value: h.value,
    pct: ((h.value / startingCash - 1) * 100).toFixed(2),
  }));

  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min) * 0.1 || 5000;

  return (
    <div className="card" style={{ padding: '20px 16px 12px' }}>
      <div className="section-title" style={{ padding: '0 4px 12px' }}>Portfolio Value Over Time</div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            tickLine={{ stroke: 'var(--border)' }}
            axisLine={{ stroke: 'var(--border)' }}
          />
          <YAxis
            domain={[min - padding, max + padding]}
            tickFormatter={fmt$}
            tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            tickLine={{ stroke: 'var(--border)' }}
            axisLine={{ stroke: 'var(--border)' }}
            width={80}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              fontFamily: 'IBM Plex Mono',
              fontSize: 12,
            }}
            labelStyle={{ color: 'var(--text-muted)' }}
            formatter={(val) => [fmt$(val), 'Value']}
          />
          <ReferenceLine
            y={startingCash}
            stroke="var(--text-muted)"
            strokeDasharray="4 4"
            label={{ value: 'Start', fill: 'var(--text-muted)', fontSize: 11 }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={{ r: 3, fill: 'var(--accent)' }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
