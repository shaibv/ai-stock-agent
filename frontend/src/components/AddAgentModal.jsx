import { useState } from 'react';
import { createAgent } from '../api';

const PRESET_COLORS = ['#ff4444', '#4ade80', '#60a5fa', '#f59e0b', '#a78bfa', '#f472b6'];

const SHARED_RULES_PREVIEW = `## Trading Cost Rules
- Every trade costs $3. Only change positions when expected gain exceeds cost.
- Keeping an existing position unchanged is FREE.

## Portfolio Rules
- All weight_pct values MUST sum to exactly 100.
- MINIMUM 7 stocks, MAXIMUM 20 stocks.
- Every stock must have at least 5% weight. No single position above 25%.

## Output — respond ONLY with valid JSON:
{ "portfolio": [{ "ticker": "...", "weight_pct": 10, "signal": "bullish",
  "confidence": "high", "rationale": "..." }],
  "total_weight": 100, "summary": "..." }`;

function slugify(str) {
  return str.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_-]/g, '').slice(0, 32);
}

export default function AddAgentModal({ onClose, onCreated }) {
  const [displayName, setDisplayName] = useState('');
  const [agentId, setAgentId] = useState('');
  const [idTouched, setIdTouched] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[2]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleDisplayName(v) {
    setDisplayName(v);
    if (!idTouched) setAgentId(slugify(v));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createAgent({ name: agentId, display_name: displayName, prompt_text: promptText, color });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={s.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={s.modal}>
        <div style={s.header}>
          <span className="mono" style={{ fontSize: 14, fontWeight: 700 }}>ADD AGENT</span>
          <button onClick={onClose} style={s.closeBtn}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={s.form}>
          <label style={s.label}>Display Name</label>
          <input
            style={s.input}
            value={displayName}
            onChange={(e) => handleDisplayName(e.target.value)}
            placeholder="e.g. CRYPTO DEGEN"
            maxLength={40}
            required
          />

          <label style={s.label}>Agent ID <span style={s.hint}>(slug, used as key)</span></label>
          <input
            className="mono"
            style={s.input}
            value={agentId}
            onChange={(e) => { setIdTouched(true); setAgentId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '')); }}
            placeholder="e.g. crypto_degen"
            maxLength={32}
            pattern="[a-z0-9_-]{2,32}"
            title="2-32 lowercase letters, numbers, underscores, or hyphens"
            required
          />

          <label style={s.label}>Color</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            {PRESET_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                style={{
                  width: 24, height: 24, borderRadius: '50%', background: c, border: 'none',
                  cursor: 'pointer', outline: color === c ? '2px solid white' : 'none',
                  outlineOffset: 2,
                }}
              />
            ))}
          </div>

          <label style={s.label}>Strategy Prompt</label>
          <textarea
            style={s.textarea}
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder={`Describe your agent's trading strategy, what signals to look for, and how to weigh them.\n\nExample:\nYou are a contrarian sector-rotation analyst. Your strategy: ...\n\n## Workflow\n1. Call get_hot_posts on "investing"\n2. ...`}
            rows={8}
            required
            minLength={20}
          />

          <div style={s.rulesPreview}>
            <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
              AUTO-APPENDED SHARED RULES (always added to your prompt):
            </div>
            <pre style={s.rulesText}>{SHARED_RULES_PREVIEW}</pre>
          </div>

          {error && <div style={s.error}>{error}</div>}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
            <button type="button" onClick={onClose} style={s.cancelBtn}>Cancel</button>
            <button type="submit" disabled={submitting} style={s.submitBtn} className="mono">
              {submitting ? 'CREATING…' : 'CREATE AGENT'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const s = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  modal: {
    background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8,
    width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '16px 20px', borderBottom: '1px solid var(--border)',
  },
  closeBtn: {
    background: 'none', border: 'none', color: 'var(--text-muted)',
    cursor: 'pointer', fontSize: 16, padding: '0 4px',
  },
  form: { padding: '20px', display: 'flex', flexDirection: 'column' },
  label: { fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  hint: { textTransform: 'none', letterSpacing: 0, fontSize: 10 },
  input: {
    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4,
    color: 'inherit', padding: '8px 10px', fontSize: 13, marginBottom: 14, width: '100%', boxSizing: 'border-box',
  },
  textarea: {
    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4,
    color: 'inherit', padding: '8px 10px', fontSize: 12, marginBottom: 10,
    width: '100%', boxSizing: 'border-box', resize: 'vertical', fontFamily: 'inherit',
  },
  rulesPreview: {
    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4,
    padding: '10px 12px', marginBottom: 16,
  },
  rulesText: {
    fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'pre-wrap',
    wordBreak: 'break-word', margin: 0, opacity: 0.6,
  },
  error: { color: 'var(--red)', fontSize: 12, marginBottom: 12 },
  cancelBtn: {
    background: 'none', border: '1px solid var(--border)', color: 'var(--text-muted)',
    borderRadius: 4, padding: '8px 16px', cursor: 'pointer', fontSize: 12,
  },
  submitBtn: {
    background: 'var(--accent)', color: '#000', border: 'none',
    borderRadius: 4, padding: '8px 16px', cursor: 'pointer', fontSize: 12, fontWeight: 700, letterSpacing: 1,
  },
};
