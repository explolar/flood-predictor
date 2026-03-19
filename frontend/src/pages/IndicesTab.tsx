import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { indicesTiles } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { IndexTile } from "../types/api";
import { useState } from "react";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

const INDEX_NAMES = ["NDVI", "NDWI", "MNDWI", "NDBI", "BSI", "SAVI", "EVI"];

export function IndicesTab({ geojson, center, params }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);
  const indices = useAnalysis<any, { indices: IndexTile[] }>(indicesTiles);

  const handleRun = () => {
    indices.run({
      geojson,
      date_start: params.img_start,
      date_end: params.img_end,
      cloud_thresh: params.cloud_thresh,
    });
  };

  const currentTile = indices.data?.indices?.[activeIndex];

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Spectral Indices</h2>
        <button className="btn btn-primary" onClick={handleRun} disabled={indices.isLoading}>
          {indices.isLoading ? "Computing..." : "COMPUTE INDICES"}
        </button>
      </div>

      {indices.isLoading && <LoadingOverlay message="Computing spectral indices..." />}
      {indices.error && <ErrorBanner message={indices.error} onDismiss={indices.reset} />}

      {indices.data && (
        <>
          <nav className="sub-tab-bar">
            {INDEX_NAMES.map((name, i) => (
              <button
                key={name}
                className={`tab-item ${activeIndex === i ? "tab-active" : ""}`}
                onClick={() => setActiveIndex(i)}
              >
                {name}
              </button>
            ))}
          </nav>

          <TileMap
            center={center}
            tileUrl={currentTile?.tile_url}
            tileName={currentTile?.name || "Index"}
          />

          {currentTile?.metrics && (
            <div className="metrics-grid">
              {Object.entries(currentTile.metrics).map(([k, v]) => (
                <MetricCard key={k} label={k} value={v.toFixed(4)} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
