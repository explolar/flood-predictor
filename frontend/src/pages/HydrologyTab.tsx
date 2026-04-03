import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { hydrologyAnalysis } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { HydrologyData } from "../types/api";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

const LAYERS = [
  { key: "stream_url", label: "Stream Network" },
  { key: "flow_acc_url", label: "Flow Accumulation" },
  { key: "flow_dir_url", label: "Flow Direction" },
  { key: "cond_dem_url", label: "Conditioned DEM" },
] as const;

type LayerKey = (typeof LAYERS)[number]["key"];

export function HydrologyTab({ geojson, center }: Props) {
  const [streamThreshold, setStreamThreshold] = useState(500);
  const [activeLayer, setActiveLayer] = useState<LayerKey>("stream_url");
  const hydro = useAnalysis<any, HydrologyData>(hydrologyAnalysis);

  const handleRun = () => {
    hydro.run({ geojson, stream_threshold: streamThreshold });
  };

  const data = hydro.data;
  const currentLayer = LAYERS.find((l) => l.key === activeLayer)!;

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Watershed &amp; Stream Analysis</h2>
        <div className="tab-actions">
          <label className="label-inline">
            Stream threshold:
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
            {hydro.isLoading ? "Analyzing..." : "Analyze hydrology"}
          </button>
        </div>
      </div>

      {hydro.isLoading && <LoadingOverlay message="Computing watershed analysis..." />}
      {hydro.error && <ErrorBanner message={hydro.error} onDismiss={hydro.reset} />}

      {data && (
        <>
          <nav className="sub-tab-bar">
            {LAYERS.map((layer) => (
              <button
                key={layer.key}
                className={`tab-item ${activeLayer === layer.key ? "tab-active" : ""}`}
                onClick={() => setActiveLayer(layer.key)}
              >
                {layer.label}
              </button>
            ))}
          </nav>

          <TileMap
            center={center}
            tileUrl={data[activeLayer]}
            tileName={currentLayer.label}
          />

          <div className="metrics-grid">
            <MetricCard label="Stream length" value={data.stream_length_km.toFixed(1)} unit="km" />
            <MetricCard label="DEM min" value={data.dem_min.toFixed(1)} unit="m" />
            <MetricCard label="DEM max" value={data.dem_max.toFixed(1)} unit="m" />
            <MetricCard label="DEM mean" value={data.dem_mean.toFixed(1)} unit="m" />
            <MetricCard label="Max accumulation" value={data.max_accumulation.toLocaleString()} />
          </div>
        </>
      )}
    </div>
  );
}
