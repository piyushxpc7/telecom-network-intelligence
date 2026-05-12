import { useState } from "react";
import { apiPost } from "../api";

export default function RiskPrediction() {
  const [form, setForm] = useState({
    region: "Region-5161",
    avg_usage: 1000,
    growth_rate: 0.1,
    variability: 100,
    peak_ratio: 1.4,
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    try {
      const res = await apiPost("/predict-usage-risk", form);
      setResult(res);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <div className="card">
        <h3>Network Risk Simulator</h3>
        <form onSubmit={submit} className="form">
          {Object.keys(form).map((k) => (
            <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="stat-label" style={{ marginBottom: 0 }}>{k.replace('_', ' ')}</label>
              <input
                value={form[k]}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    [k]: k === "region" ? e.target.value : Number(e.target.value),
                  }))
                }
              />
            </div>
          ))}
          <button type="submit" style={{ marginTop: '10px' }}>Run Simulation</button>
        </form>
      </div>

      <div className="card">
        <h3>Prediction Results</h3>
        {error && <div className="error">{error}</div>}
        {result ? (
          <div style={{ display: 'grid', gap: '16px' }}>
            <div className="tile" style={{ borderLeft: result.congestion_risk === 'HIGH' ? '4px solid #ef4444' : '4px solid #10b981' }}>
              <div className="stat-label">Congestion Risk</div>
              <div className="stat-value" style={{ color: result.congestion_risk === 'HIGH' ? '#f87171' : '#34d399' }}>
                {result.congestion_risk}
              </div>
            </div>
            <div className="tile">
              <div className="stat-label">Anomaly Detected</div>
              <div className="stat-value">{result.anomaly_flag ? 'YES' : 'NO'}</div>
            </div>
            <div className="tile">
              <div className="stat-label">Model Confidence</div>
              <div className="stat-value">{(result.score * 100).toFixed(1)}%</div>
            </div>
          </div>
        ) : !error && (
          <div className="loading">Configure parameters and run simulation to see results</div>
        )}
      </div>
    </div>
  );
}
