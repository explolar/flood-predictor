import { useEffect, useState, type ReactNode } from "react";
import { healthCheck } from "../../api/endpoints";

export function Header({ children }: { children?: ReactNode }) {
  const [geeStatus, setGeeStatus] = useState<"checking" | "connected" | "offline">("checking");

  useEffect(() => {
    healthCheck()
      .then(() => setGeeStatus("connected"))
      .catch(() => setGeeStatus("offline"));

    const interval = setInterval(() => {
      healthCheck()
        .then(() => setGeeStatus("connected"))
        .catch(() => setGeeStatus("offline"));
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="header">
      {children}
      <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
        <defs>
          <linearGradient id="hdr-bg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0369a1" />
            <stop offset="100%" stopColor="#075985" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="7" fill="url(#hdr-bg)" />
        <path d="M10 7 L22 7 M10 7 L10 25 M10 15 L19 15" stroke="white" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.95" />
        <path d="M8 22 Q12 19 16 22 Q20 25 24 22" stroke="rgba(255,255,255,0.5)" strokeWidth="1.8" strokeLinecap="round" fill="none" />
      </svg>
      <div className="header-content">
        <h1 className="header-title">FluviaAI</h1>
        <p className="header-subtitle">Satellite Flood Intelligence &middot; WeatherEx</p>
      </div>
      <div className="gee-status" title={geeStatus === "connected" ? "Google Earth Engine connected" : geeStatus === "offline" ? "GEE offline" : "Checking..."}>
        <span className={`gee-dot ${geeStatus === "connected" ? "gee-dot-on" : geeStatus === "offline" ? "gee-dot-off" : "gee-dot-checking"}`} />
        <span className="gee-label">GEE</span>
      </div>
    </header>
  );
}
