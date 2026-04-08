import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { forecastWeather, forecastInundation } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { ForecastData, ForecastInundationData } from "../types/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

type SubTab = "weather" | "inundation";

export function ForecastTab({ geojson, center, params }: Props) {
  const [subTab, setSubTab] = useState<SubTab>("weather");
  const [days, setDays] = useState(5);
  const [floodDepth, setFloodDepth] = useState(2.0);
  const [includeObserved, setIncludeObserved] = useState(false);

  const forecast = useAnalysis<any, ForecastData>(forecastWeather);
  const inundation = useAnalysis<any, ForecastInundationData>(forecastInundation);

  const handleRunWeather = () => forecast.run({ geojson, forecast_days: days });

  const handleRunInundation = () => {
    const req: any = {
      geojson,
      flood_depth_m: floodDepth,
      stream_threshold: 100,
      forecast_days: days,
    };
    if (includeObserved) {
      req.f_start = params.f_start;
      req.f_end = params.f_end;
      req.p_start = params.p_start;
      req.p_end = params.p_end;
      req.threshold = params.threshold;
      req.polarization = params.polarization;
      req.speckle = params.speckle;
    }
    inundation.run(req);
  };

  return (
    <div className="tab-content">
      <nav className="sub-tab-bar">
        <button className={`tab-item ${subTab === "weather" ? "tab-active" : ""}`} onClick={() => setSubTab("weather")}>WEATHER FORECAST</button>
        <button className={`tab-item ${subTab === "inundation" ? "tab-active" : ""}`} onClick={() => setSubTab("inundation")}>INUNDATION FORECAST</button>
      </nav>

      {/* ── Weather Forecast ── */}
      {subTab === "weather" && (
        <>
          <div className="tab-header">
            <h2>Weather &amp; Flood Forecast</h2>
            <div className="tab-actions">
              <select className="select" value={days} onChange={(e) => setDays(+e.target.value)}>
                {[3, 5, 7, 10].map((d) => (
                  <option key={d} value={d}>{d}-day</option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={handleRunWeather} disabled={forecast.isLoading}>
                {forecast.isLoading ? "Forecasting..." : "Run forecast"}
              </button>
            </div>
          </div>

          {forecast.isLoading && <LoadingOverlay message="Fetching GFS forecast data..." estimatedSeconds={45} />}
          {forecast.error && <ErrorBanner message={forecast.error} onDismiss={forecast.reset} />}

          {forecast.data && (
            <>
              <div className="metrics-grid">
                <MetricCard label="Total precipitation" value={forecast.data.total_precip_mm.toFixed(1)} unit="mm" />
                <MetricCard label="Max daily precipitation" value={forecast.data.max_daily_precip_mm.toFixed(1)} unit="mm" />
                <MetricCard label="Mean temperature" value={forecast.data.mean_temp_c.toFixed(1)} unit="°C" />
                <MetricCard label="Max wind speed" value={forecast.data.max_wind_ms.toFixed(1)} unit="m/s" />
              </div>

              {forecast.data.daily_df && forecast.data.daily_df.length > 0 && (
                <div className="chart-container">
                  <h3>Daily Precipitation</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={forecast.data.daily_df}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis unit=" mm" />
                      <Tooltip />
                      <Bar dataKey="precip_mm" name="Precipitation (mm)" fill="var(--accent, #3b82f6)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── Inundation Forecast ── */}
      {subTab === "inundation" && (
        <>
          <div className="tab-header">
            <h2>Forecast Inundation (HAND-based)</h2>
            <div className="tab-actions">
              <label className="label-inline">
                Depth:
                <input type="number" className="input input-sm" value={floodDepth} onChange={(e) => setFloodDepth(+e.target.value)} min={0.5} max={10} step={0.5} style={{ width: 70 }} />
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>m</span>
              </label>
              <select className="select" value={days} onChange={(e) => setDays(+e.target.value)}>
                {[3, 5, 7, 10].map((d) => (
                  <option key={d} value={d}>{d}-day</option>
                ))}
              </select>
              <label className="label-inline" style={{ gap: 4 }}>
                <input type="checkbox" checked={includeObserved} onChange={(e) => setIncludeObserved(e.target.checked)} />
                Compare w/ SAR
              </label>
              <button className="btn btn-primary" onClick={handleRunInundation} disabled={inundation.isLoading}>
                {inundation.isLoading ? "Computing..." : "FORECAST INUNDATION"}
              </button>
            </div>
          </div>

          {inundation.isLoading && <LoadingOverlay message="Computing HAND-based inundation forecast..." estimatedSeconds={180} />}
          {inundation.error && <ErrorBanner message={inundation.error} onDismiss={inundation.reset} />}

          {inundation.data && (
            <>
              {/* Alert level */}
              {inundation.data.alert_level && (
                <div style={{
                  padding: "0.75rem 1rem",
                  borderRadius: 8,
                  border: `2px solid ${inundation.data.alert_color ?? "#ccc"}`,
                  background: `${inundation.data.alert_color ?? "#ccc"}15`,
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                }}>
                  <span style={{
                    padding: "2px 12px",
                    borderRadius: 4,
                    background: inundation.data.alert_color,
                    color: "#fff",
                    fontWeight: 700,
                    fontSize: "0.85rem",
                  }}>
                    {inundation.data.alert_level}
                  </span>
                  <span style={{ fontSize: "0.9rem" }}>
                    {inundation.data.forecast_max_precip_mm != null
                      ? `Max forecast precip: ${inundation.data.forecast_max_precip_mm.toFixed(1)} mm`
                      : ""}
                    {inundation.data.exceedance_return_period != null
                      ? ` | ~${inundation.data.exceedance_return_period}-yr return period`
                      : ""}
                  </span>
                </div>
              )}

              <div className="metrics-grid">
                <MetricCard label="Forecast Flood Area" value={inundation.data.forecast_area_ha?.toFixed(1) ?? "N/A"} unit="ha" color="#0077be" />
                {inundation.data.observed_area_ha != null && (
                  <MetricCard label="Observed (SAR)" value={inundation.data.observed_area_ha.toFixed(1)} unit="ha" color="#ff6b81" />
                )}
                {inundation.data.hand_stats && (
                  <>
                    <MetricCard label="Mean HAND" value={inundation.data.hand_stats.mean_hand_m?.toFixed(1) ?? "N/A"} unit="m" color="#6baed6" />
                    <MetricCard label="HAND P10" value={inundation.data.hand_stats.p10_hand_m?.toFixed(1) ?? "N/A"} unit="m" color="#2171b5" />
                  </>
                )}
              </div>

              {/* Side-by-side: Observed vs Forecast */}
              <div className="map-grid">
                {inundation.data.forecast_flood_url && (
                  <div>
                    <h3 className="map-title">Forecast Inundation ({floodDepth}m depth)</h3>
                    <TileMap center={center} tileUrl={inundation.data.forecast_flood_url} tileName="Forecast Flood" height="460px" />
                  </div>
                )}
                {inundation.data.observed_flood_url && (
                  <div>
                    <h3 className="map-title">Observed Flood (SAR)</h3>
                    <TileMap center={center} tileUrl={inundation.data.observed_flood_url} tileName="Observed Flood" height="460px" />
                  </div>
                )}
              </div>

              {inundation.data.forecast_depth_url && (
                <div style={{ marginTop: "1rem" }}>
                  <h3 className="map-title">Forecast Depth</h3>
                  <TileMap center={center} tileUrl={inundation.data.forecast_depth_url} tileName="Forecast Depth" height="400px" />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
