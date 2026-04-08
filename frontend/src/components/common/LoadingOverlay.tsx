import { useState, useEffect } from "react";

interface LoadingOverlayProps {
  message?: string;
  estimatedSeconds?: number;
  variant?: "spinner" | "skeleton";
}

export function LoadingOverlay({
  message = "Running analysis...",
  estimatedSeconds,
  variant = "spinner",
}: LoadingOverlayProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!estimatedSeconds) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [estimatedSeconds]);

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

  const remaining = estimatedSeconds ? Math.max(0, estimatedSeconds - elapsed) : null;

  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <p>{message}</p>
      {remaining !== null && (
        <span className="loading-eta">
          {remaining > 0
            ? `~${remaining}s remaining`
            : "Finishing up..."}
        </span>
      )}
    </div>
  );
}
