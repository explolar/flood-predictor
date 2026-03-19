import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { mcaRiskMap, mcaStats } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { TileData } from "../types/api";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

export function RiskTab({ geojson, center, params }: Props) {
  const w_rain = Math.max(0, 100 - params.w_lulc - params.w_slope);

  const risk = useAnalysis<any, TileData>(mcaRiskMap);
  const stats = useAnalysis<any, Record<string, number>>(mcaStats);

  const handleRun = () => {
    const req = { geojson, w_lulc: params.w_lulc, w_slope: params.w_slope, w_rain };
    risk.run(req);
    stats.run(req);
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Multi-Criteria Risk Assessment</h2>
        <button className="btn btn-primary" onClick={handleRun} disabled={risk.isLoading}>
          {risk.isLoading ? "Computing..." : "RUN MCA"}
        </button>
      </div>

      {risk.isLoading && <LoadingOverlay message="Computing risk map..." />}
      {risk.error && <ErrorBanner message={risk.error} onDismiss={risk.reset} />}

      <div className="weight-bar">
        <span>LULC {params.w_lulc}%</span>
        <span>Slope {params.w_slope}%</span>
        <span>Rainfall {w_rain}%</span>
      </div>

      <TileMap
        center={center}
        tileUrl={risk.data?.tile_url}
        tileName="Flood Risk (MCA)"
      />

      {stats.data && (
        <div className="metrics-grid">
          {Object.entries(stats.data).map(([key, val]) => (
            <MetricCard key={key} label={key.replace(/_/g, " ")} value={typeof val === "number" ? val.toFixed(2) : String(val)} />
          ))}
        </div>
      )}
    </div>
  );
}
