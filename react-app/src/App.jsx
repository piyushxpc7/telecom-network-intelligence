import { NavLink, Route, Routes } from "react-router-dom";
import UsageDashboard from "./pages/UsageDashboard";
import RegionExplorer from "./pages/RegionExplorer";
import PeakTraffic from "./pages/PeakTraffic";
import RiskPrediction from "./pages/RiskPrediction";

export default function App() {
  return (
    <div className="container">
      <h1>Telecom Network Intelligence</h1>
      <nav>
        <NavLink to="/" className={({ isActive }) => isActive ? "active-link" : ""}>Dashboard</NavLink>
        <NavLink to="/peak" className={({ isActive }) => isActive ? "active-link" : ""}>Peak Traffic</NavLink>
        <NavLink to="/region" className={({ isActive }) => isActive ? "active-link" : ""}>Region Explorer</NavLink>
        <NavLink to="/risk" className={({ isActive }) => isActive ? "active-link" : ""}>Prediction</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<UsageDashboard />} />
        <Route path="/peak" element={<PeakTraffic />} />
        <Route path="/region" element={<RegionExplorer />} />
        <Route path="/risk" element={<RiskPrediction />} />
      </Routes>
    </div>
  );
}
