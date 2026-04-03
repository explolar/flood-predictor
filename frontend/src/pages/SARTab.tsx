import { useMemo } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { sarFloodDetection } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { SARData } from "../types/api";
import { LEGENDS } from "../config/legends";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

export function SARTab({ geojson, center, params }: Props) {
  const sar = useAnalysis<any, SARData>(sarFloodDetection);

  const handleRun = () => {
    sar.run({
      geojson,
      f_start: params.f_start,
      f_end: params.f_end,
      p_start: params.p_start,
      p_end: params.p_end,
      threshold: params.threshold,
      polarization: params.polarization,
      speckle: params.speckle,
    });
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>SAR Flood Detection</h2>
        <button className="btn btn-primary" onClick={handleRun} disabled={sar.isLoading}>
          {sar.isLoading ? "Detecting..." : "RUN SAR DETECTION"}
        </button>
      </div>

      {sar.isLoading && <LoadingOverlay message="Processing Sentinel-1 SAR data..." />}
      {sar.error && <ErrorBanner message={sar.error} onDismiss={sar.reset} />}

      {sar.data && (
        <div className="metrics-grid">
          <MetricCard label="Flooded Area" value={sar.data.area_ha.toFixed(1)} unit="ha" color="#ff6b81" />
          <MetricCard label="Population Exposed" value={sar.data.pop_exposed} color="#ffc554" />
        </div>
      )}

      {sar.data && <SARSummary data={sar.data} />}

      <div className="map-grid">
        <div>
          <h3 className="map-title">Flood Mask</h3>
          <TileMap center={center} tileUrl={sar.data?.flood_url} tileName="Flood Mask" height="460px" legend={LEGENDS["SAR Flood"]} />
        </div>
        <div>
          <h3 className="map-title">Severity Zones</h3>
          <TileMap center={center} tileUrl={sar.data?.severity_url} tileName="Severity" height="460px" legend={LEGENDS["SAR Severity"]} />
        </div>
      </div>
    </div>
  );
}

/* ---------- SAR Summary sub-component ---------- */

const PIE_COLORS = ["#0891b2", "#a5f3fc"];

function formatValue(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v ?? "N/A");
}

function SARSummary({ data }: { data: SARData }) {
  // Build table rows from all data fields (skip URLs)
  const rows = useMemo(() => {
    const entries: { metric: string; value: string }[] = [];
    for (const [key, val] of Object.entries(data)) {
      if (typeof val === "string" && val.startsWith("http")) continue; // skip tile URLs
      entries.push({
        metric: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        value: formatValue(val),
      });
    }
    return entries;
  }, [data]);

  // Pie chart: assume total AOI area is roughly 10x flooded area for visual context
  // If backend provides total_area_ha we use it; otherwise derive a reasonable estimate
  const dataAny = data as any;
  const totalArea = dataAny.total_area_ha
    ? Number(dataAny.total_area_ha)
    : data.area_ha * 10;
  const nonFlood = Math.max(totalArea - data.area_ha, 0);

  const pieData = [
    { name: "Flooded", value: Math.round(data.area_ha * 100) / 100 },
    { name: "Non-Flooded", value: Math.round(nonFlood * 100) / 100 },
  ];

  return (
    <>
      <h3 className="map-title" style={{ marginTop: "1.5rem" }}>SAR Detection Summary</h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", alignItems: "start" }}>
        {/* Summary table */}
        <div className="ahp-weights-table">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="weight-value">{r.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pie chart */}
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(1)}%`}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value} ha`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
