import { useState } from "react";
import { apiGet } from "../api";

export default function RegionExplorer() {
  const [region, setRegion] = useState("Region-5161");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  async function fetchRegion() {
    setError("");
    try {
      const res = await apiGet(`/usage/region/${encodeURIComponent(region)}`);
      setData(res);
    } catch (e) {
      setData(null);
      setError(e.message);
    }
  }

  return (
    <div className="card">
      <h3>Region Analytics</h3>
      <form className="row" style={{ marginBottom: '24px' }} onSubmit={(e) => { e.preventDefault(); fetchRegion(); }}>
        <input 
          value={region} 
          onChange={(e) => setRegion(e.target.value)} 
          placeholder="Enter region (e.g. Centro, Region-1)" 
          style={{ flex: 1 }}
        />
        <button type="submit">Analyze Region</button>
      </form>
      
      {error && <div className="error">{error}</div>}
      
      {data ? (
        <div className="chart-container" style={{ height: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Hour</th>
                <th>Calls</th>
                <th>SMS</th>
                <th>Internet Usage</th>
              </tr>
            </thead>
            <tbody>
              {data.hourly_distribution.map((row) => (
                <tr key={row.hour}>
                  <td style={{ fontWeight: 600 }}>{row.hour}:00</td>
                  <td>{Number(row.calls).toLocaleString()}</td>
                  <td>{Number(row.sms).toLocaleString()}</td>
                  <td>{Number(row.internet_mb).toFixed(2)} MB</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !error && (
        <div className="loading">Enter a region name to view hourly distribution</div>
      )}
    </div>
  );
}
