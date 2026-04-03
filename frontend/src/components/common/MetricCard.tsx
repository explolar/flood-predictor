interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}

export function MetricCard({ label, value, unit, color = "var(--accent)" }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-value" style={{ color }}>
        {typeof value === "number" ? value.toLocaleString() : value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
