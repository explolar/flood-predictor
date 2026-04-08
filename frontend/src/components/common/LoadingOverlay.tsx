import { useState, useEffect } from "react";

interface LoadingOverlayProps {
  message?: string;
  estimatedSeconds?: number;
  variant?: "spinner" | "skeleton";
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function LoadingOverlay({
  message = "Running analysis...",
  estimatedSeconds,
  variant = "spinner",
}: LoadingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setElapsed(0);
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [message]);

  if (variant === "skeleton") {
    return (
      <div className="skeleton-container">
        <div className="skeleton-metrics">
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
        </div>
        <div className="skeleton skeleton-map" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text-sm" />
      </div>
    );
  }

  const pct = estimatedSeconds ? Math.min((elapsed / estimatedSeconds) * 100, 98) : null;
  const remaining = estimatedSeconds ? Math.max(0, estimatedSeconds - elapsed) : null;

  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <p>{message}</p>

      {/* Always show elapsed timer */}
      <span className="loading-elapsed">{formatTime(elapsed)} elapsed</span>

      {/* Progress bar when estimate is available */}
      {pct !== null && (
        <div className="loading-progress-track">
          <div
            className="loading-progress-bar"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      {remaining !== null && (
        <span className="loading-eta">
          {remaining > 0
            ? `~${formatTime(remaining)} remaining`
            : "Finishing up..."}
        </span>
      )}
    </div>
  );
}
