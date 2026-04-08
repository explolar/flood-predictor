import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { impactAssessment } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { ImpactData } from "../types/api";
import { LEGENDS } from "../config/legends";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

export function ImpactTab({ geojson, center, params }: Props) {
  const [includePop, setIncludePop] = useState(true);
  const [includeBuildings, setIncludeBuildings] = useState(true);
  const [includeInfra, setIncludeInfra] = useState(true);
  const [includeCrops, setIncludeCrops] = useState(true);

  const impact = useAnalysis<any, ImpactData>(impactAssessment);

  const handleRun = () => {
    impact.run({
      geojson,
      f_start: params.f_start,
      f_end: params.f_end,
      p_start: params.p_start,
      p_end: params.p_end,
      threshold: params.threshold,
      polarization: params.polarization,
      speckle: params.speckle,
      include_population: includePop,
      include_buildings: includeBuildings,
      include_infrastructure: includeInfra,
      include_crop_loss: includeCrops,
      crop_type: params.crop_type,
      crop_price: params.crop_price,
    });
  };

  const data = impact.data;

  const handleExport = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `impact_report_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Impact Assessment</h2>
        <div className="tab-actions">
          <label className="label-inline" style={{ gap: 4 }}><input type="checkbox" checked={includePop} onChange={(e) => setIncludePop(e.target.checked)} /> Population</label>
          <label className="label-inline" style={{ gap: 4 }}><input type="checkbox" checked={includeBuildings} onChange={(e) => setIncludeBuildings(e.target.checked)} /> Buildings</label>
          <label className="label-inline" style={{ gap: 4 }}><input type="checkbox" checked={includeInfra} onChange={(e) => setIncludeInfra(e.target.checked)} /> Infrastructure</label>
          <label className="label-inline" style={{ gap: 4 }}><input type="checkbox" checked={includeCrops} onChange={(e) => setIncludeCrops(e.target.checked)} /> Crops</label>
          <button className="btn btn-primary" onClick={handleRun} disabled={impact.isLoading}>
            {impact.isLoading ? "Assessing..." : "RUN IMPACT ASSESSMENT"}
          </button>
        </div>
      </div>

      {impact.isLoading && <LoadingOverlay message="Computing impact across all modules..." />}
      {impact.error && <ErrorBanner message={impact.error} onDismiss={impact.reset} />}

      {data && (
        <>
          {/* Summary metrics */}
          <div className="metrics-grid">
            <MetricCard label="Flood Area" value={data.flood_area_ha?.toFixed(1) ?? "N/A"} unit="ha" color="#ff6b81" />
            {data.population && (
              <>
                <MetricCard label="People Affected" value={data.population.total_population?.toLocaleString() ?? "N/A"} color="#e6550d" />
                <MetricCard label="Displaced Estimate" value={data.population.displaced_estimate?.toLocaleString() ?? "N/A"} color="#d73027" />
              </>
            )}
            {data.buildings && (
              <MetricCard label="Buildings Affected" value={data.buildings.total_affected?.toLocaleString() ?? "N/A"} color="#8856a7" />
            )}
            {data.crop_loss && (
              <MetricCard label="Crop Loss" value={`$${(data.crop_loss.estimated_loss_usd ?? 0).toLocaleString()}`} color="#e6550d" />
            )}
          </div>

          {/* Population breakdown */}
          {data.population && (
            <section style={{ marginTop: "1.5rem" }}>
              <h3 className="map-title">Population Impact</h3>
              <div className="ahp-weights-table">
                <table>
                  <thead><tr><th>Category</th><th>Count</th></tr></thead>
                  <tbody>
                    <tr><td>Total in AOI</td><td className="weight-value">{data.population.total_population?.toLocaleString()}</td></tr>
                    <tr><td>Displaced Estimate</td><td className="weight-value">{data.population.displaced_estimate?.toLocaleString()}</td></tr>
                    <tr><td>Children Affected</td><td className="weight-value">{data.population.children_affected?.toLocaleString()}</td></tr>
                    <tr><td>Elderly Affected</td><td className="weight-value">{data.population.elderly_affected?.toLocaleString()}</td></tr>
                    <tr><td>Displacement Rate</td><td className="weight-value">{((data.population.displacement_rate ?? 0) * 100).toFixed(0)}%</td></tr>
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Building damage */}
          {data.buildings && data.buildings.damage_counts && (
            <section style={{ marginTop: "1.5rem" }}>
              <h3 className="map-title">Building Damage</h3>
              <div className="metrics-grid">
                <MetricCard label="Minor (0-0.5m)" value={data.buildings.damage_counts.minor} color="#fee08b" />
                <MetricCard label="Moderate (0.5-1.5m)" value={data.buildings.damage_counts.moderate} color="#fc8d59" />
                <MetricCard label="Severe (1.5-3m)" value={data.buildings.damage_counts.severe} color="#d73027" />
                <MetricCard label="Destroyed (>3m)" value={data.buildings.damage_counts.destroyed} color="#67001f" />
              </div>
              {data.buildings.tile_url && (
                <TileMap center={center} tileUrl={data.buildings.tile_url} tileName="Building Damage" height="400px" />
              )}
            </section>
          )}

          {/* Infrastructure */}
          {data.infrastructure && (
            <section style={{ marginTop: "1.5rem" }}>
              <h3 className="map-title">Infrastructure at Risk</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                {/* Facilities */}
                {data.infrastructure.facilities.length > 0 && (
                  <div className="ahp-weights-table">
                    <table>
                      <thead><tr><th>Facility</th><th>Type</th></tr></thead>
                      <tbody>
                        {data.infrastructure.facilities.slice(0, 15).map((f, i) => (
                          <tr key={i}><td>{f.name}</td><td className="weight-value">{f.type}</td></tr>
                        ))}
                        {data.infrastructure.facilities.length > 15 && (
                          <tr><td colSpan={2} style={{ color: "var(--text-secondary)" }}>...and {data.infrastructure.facilities.length - 15} more</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
                {/* Roads + Dams */}
                <div>
                  {data.infrastructure.roads && (
                    <div className="ahp-weights-table" style={{ marginBottom: "0.75rem" }}>
                      <table>
                        <thead><tr><th>Road Type</th><th>Length (km)</th></tr></thead>
                        <tbody>
                          {Object.entries(data.infrastructure.roads.km_by_type).map(([type, km]) => (
                            <tr key={type}><td>{type}</td><td className="weight-value">{km}</td></tr>
                          ))}
                          <tr style={{ fontWeight: 600 }}>
                            <td>Total</td><td className="weight-value">{data.infrastructure.roads.total_km} km</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
                  {data.infrastructure.dams && data.infrastructure.dams.length > 0 && (
                    <div className="ahp-weights-table">
                      <table>
                        <thead><tr><th>Dam</th><th>River</th><th>Capacity (MCM)</th></tr></thead>
                        <tbody>
                          {data.infrastructure.dams.map((d, i) => (
                            <tr key={i}><td>{d.name}</td><td>{d.river}</td><td className="weight-value">{d.capacity_mcm}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* Crop loss detail */}
          {data.crop_loss && (
            <section style={{ marginTop: "1.5rem" }}>
              <h3 className="map-title">Crop Loss</h3>
              <div className="metrics-grid">
                <MetricCard label="Affected Cropland" value={data.crop_loss.affected_ha?.toFixed(1) ?? "N/A"} unit="ha" color="#e6550d" />
                <MetricCard label="Estimated Loss" value={`$${(data.crop_loss.estimated_loss_usd ?? 0).toLocaleString()}`} color="#d73027" />
              </div>
              {data.crop_loss.message && <p style={{ color: "var(--text-secondary)" }}>{data.crop_loss.message}</p>}
            </section>
          )}

          {/* Map */}
          <div className="map-grid" style={{ marginTop: "1.5rem" }}>
            <div>
              <h3 className="map-title">Flood Extent</h3>
              <TileMap center={center} tileUrl={(data as any).flood_url} tileName="Flood" height="400px" legend={LEGENDS["SAR Flood"]} />
            </div>
            <div>
              <h3 className="map-title">Severity</h3>
              <TileMap center={center} tileUrl={(data as any).severity_url} tileName="Severity" height="400px" legend={LEGENDS["SAR Severity"]} />
            </div>
          </div>

          {/* Export */}
          <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.5rem" }}>
            <button className="btn btn-primary" onClick={handleExport}>
              Export Impact Report (JSON)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
