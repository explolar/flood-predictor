import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { forecastWeather } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { ForecastData } from "../types/api";
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

export function ForecastTab({ geojson, center }: Props) {
  const [days, setDays] = useState(5);
  const forecast = useAnalysis<any, ForecastData>(forecastWeather);

  const handleRun = () => {
    forecast.run({ geojson, forecast_days: days });
  };

  const data = forecast.data;

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Weather &amp; Flood Forecast</h2>
        <div className="tab-actions">
          <select className="select" value={days} onChange={(e) => setDays(+e.target.value)}>
            {[3, 5, 7, 10].map((d) => (
              <option key={d} value={d}>{d}-day</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={handleRun} disabled={forecast.isLoading}>
            {forecast.isLoading ? "Forecasting..." : "Run forecast"}
          </button>
        </div>
      </div>

      {forecast.isLoading && <LoadingOverlay message="Fetching GFS forecast data..." />}
      {forecast.error && <ErrorBanner message={forecast.error} onDismiss={forecast.reset} />}

      {data && (
        <>
          <div className="map-pair">
            <div className="map-pair-item">
              <h3>Precipitation</h3>
              <TileMap center={center} tileUrl={data.precip_tile_url} tileName="Precipitation" />
            </div>
            <div className="map-pair-item">
              <h3>Temperature</h3>
              <TileMap center={center} tileUrl={data.temp_tile_url} tileName="Temperature" />
            </div>
          </div>

          <div className="metrics-grid">
            <MetricCard label="Total precipitation" value={data.total_precip_mm.toFixed(1)} unit="mm" />
            <MetricCard label="Max daily precipitation" value={data.max_daily_precip_mm.toFixed(1)} unit="mm" />
            <MetricCard label="Mean temperature" value={data.mean_temp_c.toFixed(1)} unit="°C" />
            <MetricCard label="Max wind speed" value={data.max_wind_ms.toFixed(1)} unit="m/s" />
          </div>

          {data.daily_df && data.daily_df.length > 0 && (
            <div className="chart-container">
              <h3>Daily Precipitation</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.daily_df}>
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
    </div>
  );
}
