import { useEffect, useState } from "react";
import { apiGet } from "../api";

export default function PeakTraffic() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/usage/peak").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading peak traffic...</p>;

  return (
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <div className="card">
        <h3>Top Peak Hours</h3>
        <table>
          <thead>
            <tr>
              <th>Hour</th>
              <th>Total Usage</th>
            </tr>
          </thead>
          <tbody>
            {data.top_hours.map((h, idx) => (
              <tr key={idx}>
                <td>{h.hour}:00</td>
                <td>{Number(h.total_usage).toLocaleString()} units</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Top Usage Regions</h3>
        <table>
          <thead>
            <tr>
              <th>Region</th>
              <th>Total Usage</th>
            </tr>
          </thead>
          <tbody>
            {data.top_regions.map((r, idx) => (
              <tr key={idx}>
                <td>{r.region}</td>
                <td>{Number(r.total_usage).toLocaleString()} units</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
