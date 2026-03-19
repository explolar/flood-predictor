import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { forecastWeather } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

export function ForecastTab({ geojson, center }: Props) {
  const [days, setDays] = useState(5);
  const forecast = useAnalysis<any>(forecastWeather);

  const handleRun = () => {
    forecast.run({ geojson, forecast_days: days });
  };

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
            {forecast.isLoading ? "Forecasting..." : "RUN FORECAST"}
          </button>
        </div>
      </div>

      {forecast.isLoading && <LoadingOverlay message="Fetching GFS forecast data..." />}
      {forecast.error && <ErrorBanner message={forecast.error} onDismiss={forecast.reset} />}

      {forecast.data && (
        <TileMap
          center={center}
          tileUrl={(forecast.data as any).tile_url}
          tileName="Forecast"
        />
      )}
    </div>
  );
}
