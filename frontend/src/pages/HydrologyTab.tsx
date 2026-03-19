import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { hydrologyAnalysis } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

export function HydrologyTab({ geojson, center }: Props) {
  const [streamThreshold, setStreamThreshold] = useState(500);
  const hydro = useAnalysis<any>(hydrologyAnalysis);

  const handleRun = () => {
    hydro.run({ geojson, stream_threshold: streamThreshold });
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Watershed &amp; Stream Analysis</h2>
        <div className="tab-actions">
          <label className="label-inline">
            Stream Threshold:
            <input
              type="number"
              className="input input-sm"
              value={streamThreshold}
              onChange={(e) => setStreamThreshold(+e.target.value)}
              min={100}
              max={5000}
              step={100}
            />
          </label>
          <button className="btn btn-primary" onClick={handleRun} disabled={hydro.isLoading}>
            {hydro.isLoading ? "Analyzing..." : "ANALYZE HYDROLOGY"}
          </button>
        </div>
      </div>

      {hydro.isLoading && <LoadingOverlay message="Computing watershed analysis..." />}
      {hydro.error && <ErrorBanner message={hydro.error} onDismiss={hydro.reset} />}

      {hydro.data && (
        <TileMap
          center={center}
          tileUrl={(hydro.data as any).tile_url}
          tileName="Hydrology"
        />
      )}
    </div>
  );
}
