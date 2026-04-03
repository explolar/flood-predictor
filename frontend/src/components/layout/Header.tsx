import { Droplets } from "lucide-react";

export function Header() {
  return (
    <header className="header">
      <div style={{
        width: 34,
        height: 34,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 10,
        background: "rgba(26, 115, 232, 0.12)",
        border: "1px solid rgba(26, 115, 232, 0.18)",
      }}>
        <Droplets size={18} color="#1a73e8" strokeWidth={2.5} />
      </div>
      <div className="header-content">
        <h1 className="header-title">HydroRisk Atlas</h1>
        <p className="header-subtitle">
          Satellite-Powered Flood Intelligence &middot; Powered by WeatherEx
        </p>
      </div>
    </header>
  );
}
