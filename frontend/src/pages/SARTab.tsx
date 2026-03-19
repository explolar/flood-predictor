import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { sarFloodDetection } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { SARData } from "../types/api";

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

      <div className="map-grid">
        <div>
          <h3 className="map-title">Flood Mask</h3>
          <TileMap center={center} tileUrl={sar.data?.flood_url} tileName="Flood Mask" height="400px" />
        </div>
        <div>
          <h3 className="map-title">Severity Zones</h3>
          <TileMap center={center} tileUrl={sar.data?.severity_url} tileName="Severity" height="400px" />
        </div>
      </div>
    </div>
  );
}
