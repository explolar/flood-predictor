import { useState, useMemo } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { indicesTiles } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { IndicesData } from "../types/api";
import { LEGENDS } from "../config/legends";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

const INDEX_NAMES = ["NDVI", "NDWI", "MNDWI", "NDBI", "BSI", "SAVI", "EVI"];

export function IndicesTab({ geojson, center, params }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);
  const indices = useAnalysis<any, IndicesData>(indicesTiles);

  const handleRun = () => {
    indices.run({
      geojson,
      date_start: params.img_start,
      date_end: params.img_end,
      cloud_thresh: params.cloud_thresh,
    });
  };

  const activeKey = INDEX_NAMES[activeIndex];
  const currentData = indices.data?.indices?.[activeKey];

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Spectral Indices</h2>
        <button className="btn btn-primary" onClick={handleRun} disabled={indices.isLoading}>
          {indices.isLoading ? "Computing..." : "Compute indices"}
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
            tileUrl={currentData?.tile_url}
            tileName={activeKey}
            legend={LEGENDS[activeKey]}
          />

          {currentData && (
            <div className="metrics-grid">
              <MetricCard label={`Mean ${activeKey}`} value={currentData.mean_value.toFixed(4)} />
              <MetricCard label="Scenes used" value={currentData.n_scenes} />
            </div>
          )}

          <IndicesComparison data={indices.data} />
        </>
      )}
    </div>
  );
}

/* ---------- Indices Comparison sub-component ---------- */

function IndicesComparison({ data }: { data: IndicesData }) {
  const allIndices = useMemo(() => {
    if (!data?.indices) return [];
    return Object.entries(data.indices).map(([name, info]) => ({
      name,
      mean: info.mean_value,
      scenes: info.n_scenes,
    }));
  }, [data]);

  // Normalize mean values to 0-1 range for the radar chart
  // Many indices can be negative (e.g. NDVI anomaly), so we use min-max normalization
  const radarData = useMemo(() => {
    if (allIndices.length === 0) return [];
    const means = allIndices.map((d) => Math.abs(d.mean));
    const maxMean = Math.max(...means, 0.001); // avoid division by zero
    return allIndices.map((d) => ({
      index: d.name,
      value: Math.round((Math.abs(d.mean) / maxMean) * 100) / 100,
      raw: d.mean,
    }));
  }, [allIndices]);

  if (allIndices.length === 0) return null;

  return (
    <>
      <h3 className="map-title" style={{ marginTop: "1.5rem" }}>All Indices Comparison</h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", alignItems: "start" }}>
        {/* Comparison table */}
        <div className="ahp-weights-table">
          <table>
            <thead>
              <tr>
                <th>Index</th>
                <th>Mean Value</th>
                <th>Scenes Used</th>
              </tr>
            </thead>
            <tbody>
              {allIndices.map((d) => (
                <tr key={d.name}>
                  <td><strong>{d.name}</strong></td>
                  <td className="weight-value">{d.mean.toFixed(4)}</td>
                  <td className="weight-value">{d.scenes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Radar chart */}
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="index" tick={{ fill: "#4a5568", fontSize: 12 }} />
              <Tooltip
                formatter={(value: any, _name: any, props: any) =>
                  `${props?.payload?.raw?.toFixed(4) ?? value} (normalized: ${Number(value).toFixed(2)})`
                }
              />
              <Radar
                name="Normalized Index"
                dataKey="value"
                stroke="#0891b2"
                fill="#0891b2"
                fillOpacity={0.3}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
