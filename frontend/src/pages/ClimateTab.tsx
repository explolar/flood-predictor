import { useState, useMemo } from "react";
import { TileMap } from "../components/map/TileMap";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { MetricCard } from "../components/common/MetricCard";
import { useAnalysis } from "../hooks/useAnalysis";
import { multiyearComparison, droughtAnalysis, projectionsAnalysis } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { TileData, ChartPoint } from "../types/api";
import { LEGENDS } from "../config/legends";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

type SubTab = "multiyear" | "drought" | "projections";

interface ProjectionsData {
  mean_precip_mm_yr?: number;
  mean_tasmax_c?: number;
  mean_tasmin_c?: number;
  precip_tile_url?: string;
  temp_tile_url?: string;
  scenario?: string;
  model?: string;
  period?: string;
  // Support scenario-comparison shape as well
  scenarios?: Record<string, { mean_precip_mm?: number; mean_temp_c?: number }>;
  baseline?: { mean_precip_mm?: number; mean_temp_c?: number };
}

export function ClimateTab({ geojson, center, params }: Props) {
  const [subTab, setSubTab] = useState<SubTab>("multiyear");
  const [years] = useState([2019, 2020, 2021, 2022, 2023, 2024]);
  const [droughtYear, setDroughtYear] = useState(2024);
  const [scenario, setScenario] = useState("ssp245");

  const multiyear = useAnalysis<any, { chart: ChartPoint[]; tiles: TileData[] }>(multiyearComparison);
  const drought = useAnalysis<any, { spi: TileData; ndvi_anomaly: TileData }>(droughtAnalysis);
  const projections = useAnalysis<any, ProjectionsData>(projectionsAnalysis);

  return (
    <div className="tab-content">
      <nav className="sub-tab-bar">
        <button className={`tab-item ${subTab === "multiyear" ? "tab-active" : ""}`} onClick={() => setSubTab("multiyear")}>MULTI-YEAR</button>
        <button className={`tab-item ${subTab === "drought" ? "tab-active" : ""}`} onClick={() => setSubTab("drought")}>DROUGHT</button>
        <button className={`tab-item ${subTab === "projections" ? "tab-active" : ""}`} onClick={() => setSubTab("projections")}>PROJECTIONS</button>
      </nav>

      {subTab === "multiyear" && (
        <>
          <div className="tab-header">
            <h2>Multi-Year Monsoon Comparison</h2>
            <button
              className="btn btn-primary"
              onClick={() =>
                multiyear.run({
                  geojson,
                  years,
                  polarization: params.polarization,
                  threshold: params.threshold,
                })
              }
              disabled={multiyear.isLoading}
            >
              {multiyear.isLoading ? "Loading..." : "COMPARE YEARS"}
            </button>
          </div>
          {multiyear.isLoading && <LoadingOverlay message="Comparing monsoon years..." />}
          {multiyear.error && <ErrorBanner message={multiyear.error} onDismiss={multiyear.reset} />}

          {multiyear.data?.chart && (
            <MultiyearChart chart={multiyear.data.chart} />
          )}
        </>
      )}

      {subTab === "drought" && (
        <>
          <div className="tab-header">
            <h2>SPI / NDVI Anomaly</h2>
            <div className="tab-actions">
              <select className="select" value={droughtYear} onChange={(e) => setDroughtYear(+e.target.value)}>
                {[2019, 2020, 2021, 2022, 2023, 2024].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <button
                className="btn btn-primary"
                onClick={() => drought.run({ geojson, year: droughtYear })}
                disabled={drought.isLoading}
              >
                ANALYZE
              </button>
            </div>
          </div>
          {drought.isLoading && <LoadingOverlay message="Computing drought indices..." />}
          {drought.error && <ErrorBanner message={drought.error} onDismiss={drought.reset} />}

          {drought.data && (
            <div className="map-grid">
              <div>
                <h3 className="map-title">SPI Index</h3>
                <TileMap center={center} tileUrl={drought.data.spi?.tile_url} tileName="SPI" height="400px" legend={LEGENDS["SPI"]} />
              </div>
              <div>
                <h3 className="map-title">NDVI Anomaly</h3>
                <TileMap center={center} tileUrl={drought.data.ndvi_anomaly?.tile_url} tileName="NDVI Anomaly" height="400px" legend={LEGENDS["NDVI Anomaly"]} />
              </div>
            </div>
          )}
        </>
      )}

      {subTab === "projections" && (
        <>
          <div className="tab-header">
            <h2>Climate Projections (CMIP6)</h2>
            <div className="tab-actions">
              <select className="select" value={scenario} onChange={(e) => setScenario(e.target.value)}>
                <option value="ssp126">SSP1-2.6</option>
                <option value="ssp245">SSP2-4.5</option>
                <option value="ssp370">SSP3-7.0</option>
                <option value="ssp585">SSP5-8.5</option>
              </select>
              <button
                className="btn btn-primary"
                onClick={() =>
                  projections.run({
                    geojson,
                    scenario,
                    model: "GFDL-ESM4",
                    start_year: 2030,
                    end_year: 2050,
                  })
                }
                disabled={projections.isLoading}
              >
                PROJECT
              </button>
            </div>
          </div>
          {projections.isLoading && <LoadingOverlay message="Running climate projections..." />}
          {projections.error && <ErrorBanner message={projections.error} onDismiss={projections.reset} />}

          {projections.data && (
            <div className="projections-results">
              {/* Header info */}
              {(projections.data.model || projections.data.period || projections.data.scenario) && (
                <p className="projections-meta">
                  Model: <strong>{projections.data.model ?? "N/A"}</strong>
                  {" | "}Scenario: <strong>{(projections.data.scenario ?? "").toUpperCase()}</strong>
                  {" | "}Period: <strong>{projections.data.period ?? "N/A"}</strong>
                </p>
              )}

              {/* Standard projections response (get_cmip6_projections) */}
              {(projections.data.mean_precip_mm_yr != null ||
                projections.data.mean_tasmax_c != null ||
                projections.data.mean_tasmin_c != null) && (
                <div className="metric-grid">
                  {projections.data.mean_precip_mm_yr != null && (
                    <MetricCard
                      label="Projected Mean Precipitation"
                      value={projections.data.mean_precip_mm_yr}
                      unit="mm/yr"
                      color="#0891b2"
                    />
                  )}
                  {projections.data.mean_tasmax_c != null && (
                    <MetricCard
                      label="Projected Max Temperature"
                      value={projections.data.mean_tasmax_c}
                      unit="°C"
                      color="#dc2626"
                    />
                  )}
                  {projections.data.mean_tasmin_c != null && (
                    <MetricCard
                      label="Projected Min Temperature"
                      value={projections.data.mean_tasmin_c}
                      unit="°C"
                      color="#2563eb"
                    />
                  )}
                </div>
              )}

              {/* Scenario-comparison response (get_cmip6_scenario_comparison) */}
              {projections.data.baseline && (
                <div style={{ marginTop: "1rem" }}>
                  <h3 className="map-title">Baseline</h3>
                  <div className="metric-grid">
                    {projections.data.baseline.mean_precip_mm != null && (
                      <MetricCard
                        label="Baseline Precipitation"
                        value={projections.data.baseline.mean_precip_mm}
                        unit="mm/yr"
                        color="#4a5568"
                      />
                    )}
                    {projections.data.baseline.mean_temp_c != null && (
                      <MetricCard
                        label="Baseline Temperature"
                        value={projections.data.baseline.mean_temp_c}
                        unit="°C"
                        color="#4a5568"
                      />
                    )}
                  </div>
                </div>
              )}

              {projections.data.scenarios && (
                <div style={{ marginTop: "1rem" }}>
                  <h3 className="map-title">Projected Scenarios</h3>
                  {Object.entries(projections.data.scenarios).map(([key, vals]) => (
                    <div key={key} style={{ marginBottom: "0.75rem" }}>
                      <h4 style={{ marginBottom: "0.25rem", color: "#4a5568" }}>{key.replace(/_/g, " ").toUpperCase()}</h4>
                      <div className="metric-grid">
                        {vals.mean_precip_mm != null && (
                          <MetricCard
                            label="Projected Precipitation"
                            value={vals.mean_precip_mm}
                            unit="mm/yr"
                            color="#0891b2"
                          />
                        )}
                        {vals.mean_temp_c != null && (
                          <MetricCard
                            label="Projected Temperature"
                            value={vals.mean_temp_c}
                            unit="°C"
                            color="#dc2626"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Tile maps if available */}
              {(projections.data.precip_tile_url || projections.data.temp_tile_url) && (
                <div className="map-grid" style={{ marginTop: "1rem" }}>
                  {projections.data.precip_tile_url && (
                    <div>
                      <h3 className="map-title">Precipitation</h3>
                      <TileMap center={center} tileUrl={projections.data.precip_tile_url} tileName="Precipitation" height="400px" />
                    </div>
                  )}
                  {projections.data.temp_tile_url && (
                    <div>
                      <h3 className="map-title">Temperature (Max)</h3>
                      <TileMap center={center} tileUrl={projections.data.temp_tile_url} tileName="Temperature" height="400px" />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ---------- MultiyearChart with trend line ---------- */

function computeTrend(points: ChartPoint[]): ChartPoint[] {
  const n = points.length;
  if (n < 2) return points.map((p) => ({ ...p, value: p.value }));

  // Simple linear regression: y = a + b*x
  const xs = points.map((_, i) => i);
  const ys = points.map((p) => p.value);
  const sumX = xs.reduce((s, x) => s + x, 0);
  const sumY = ys.reduce((s, y) => s + y, 0);
  const sumXY = xs.reduce((s, x, i) => s + x * ys[i], 0);
  const sumX2 = xs.reduce((s, x) => s + x * x, 0);
  const b = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const a = (sumY - b * sumX) / n;

  return points.map((p, i) => ({
    label: p.label,
    value: Math.round((a + b * i) * 100) / 100,
  }));
}

function MultiyearChart({ chart }: { chart: ChartPoint[] }) {
  const dataWithTrend = useMemo(() => {
    const trend = computeTrend(chart);
    return chart.map((p, i) => ({
      label: p.label,
      value: p.value,
      trend: trend[i].value,
    }));
  }, [chart]);

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={dataWithTrend}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" stroke="#4a5568" />
          <YAxis stroke="#4a5568" />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill="#0891b2" name="Flood Area (ha)" />
          <Line
            dataKey="trend"
            stroke="#06b6d4"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            name="Trend"
            type="monotone"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
