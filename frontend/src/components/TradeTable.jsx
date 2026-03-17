const fmt$ = (v) => '$' + Math.round(v).toLocaleString();

export default function TradeTable({ history }) {
  if (!history || history.length === 0) {
    return <div className="loading">No trade history yet</div>;
  }

  const reversed = [...history].reverse();

  return (
    <div className="card">
      <div className="section-title">Trade History</div>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Value</th>
            <th>Return</th>
            <th>Trades</th>
            <th>Fees</th>
            <th>Tickers</th>
          </tr>
        </thead>
        <tbody>
          {reversed.map((day, i) => {
            const prev = i < reversed.length - 1 ? reversed[i + 1].value : 100000;
            const pctChange = ((day.value / prev - 1) * 100).toFixed(2);
            const tickers = (day.portfolio?.portfolio || []).map(h => h.ticker).join(', ');
            return (
              <tr key={day.date}>
                <td>{day.date}</td>
                <td>{fmt$(day.value)}</td>
                <td className={pctChange >= 0 ? 'positive' : 'negative'}>
                  {pctChange >= 0 ? '+' : ''}{pctChange}%
                </td>
                <td>{day.trades}</td>
                <td>{fmt$(day.trade_cost)}</td>
                <td style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {tickers}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
