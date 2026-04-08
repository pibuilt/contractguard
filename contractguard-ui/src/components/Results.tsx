export default function Results({ data, onReset }: any) {
  return (
    <div className="card">
      <h2>Risk Analysis</h2>

      {data.risks.map((r: any, i: number) => (
        <div
          key={i}
          style={{
            border: "1px solid #eee",
            borderRadius: 8,
            padding: 12,
            marginTop: 10,
          }}
        >
          <p>
            <b>Type:</b> {r.risk_type}
          </p>
          <p>
            <b>Severity:</b> {r.severity}
          </p>
          <p>
            <b>Confidence:</b> {r.confidence.toFixed(2)}
          </p>
          <p>{r.explanation}</p>
        </div>
      ))}
      <button className="button" onClick={onReset} style={{ marginTop: 20 }}>
        Analyze Another Contract
      </button>
    </div>
  );
}
