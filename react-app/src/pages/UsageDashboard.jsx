import { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function UsageDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/usage/summary").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading summary...</p>;

  return (
    <div className="grid">
      <div className="tile">
        <div className="stat-label">Total Calls</div>
        <div className="stat-value">{data.total_calls.toLocaleString()}</div>
      </div>
      <div className="tile">
        <div className="stat-label">Total SMS</div>
        <div className="stat-value">{data.total_sms.toLocaleString()}</div>
      </div>
      <div className="tile">
        <div className="stat-label">Internet Usage</div>
        <div className="stat-value">{data.total_internet_mb.toFixed(2)} MB</div>
      </div>
      <div className="tile">
        <div className="stat-label">Top 3 Peak Hours</div>
        <div className="stat-value">{data.top_peak_hours.map(h => `${h}:00`).join(', ')}</div>
      </div>
      <div className="tile">
        <div className="stat-label">Top 3 Regions</div>
        <div className="stat-value" style={{ fontSize: '1.1rem' }}>{data.top_busiest_regions.join(', ')}</div>
      </div>
    </div>
  );
}
