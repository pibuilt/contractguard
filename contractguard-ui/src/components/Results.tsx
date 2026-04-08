export default function Results({ data }: any) {
  return (
    <div>
      <h2>Risk Analysis</h2>

      {data.risks.map((r: any, i: number) => (
        <div
          key={i}
          style={{ border: "1px solid #ccc", padding: 10, margin: 10 }}
        >
          <p>
            <b>Type:</b> {r.risk_type}
          </p>
          <p>
            <b>Severity:</b> {r.severity}
          </p>
          <p>
            <b>Confidence:</b> {r.confidence}
          </p>
          <p>
            <b>Explanation:</b> {r.explanation}
          </p>
        </div>
      ))}
    </div>
  );
}
