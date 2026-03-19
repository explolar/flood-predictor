import { Activity } from "lucide-react";

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
        background: "rgba(79, 143, 247, 0.12)",
        border: "1px solid rgba(79, 143, 247, 0.15)",
      }}>
        <Activity size={18} color="#4f8ff7" strokeWidth={2.5} />
      </div>
      <div className="header-content">
        <h1 className="header-title">HYDRORISK ATLAS</h1>
        <p className="header-subtitle">
          Sentinel-1 SAR &middot; Sentinel-2 SR &middot; CHIRPS &middot; SRTM DEM &middot; 10&ndash;30 m
        </p>
      </div>
    </header>
  );
}
