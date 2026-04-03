import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { mcaRiskMap, mcaStats } from "../api/endpoints";
import { FACTOR_LABELS } from "../components/layout/Sidebar";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { MCAResult } from "../types/api";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

const CR_THRESHOLD = 0.10;

export function RiskTab({ geojson, center, params }: Props) {
  const [activeFactorLayer, setActiveFactorLayer] = useState<string | null>(null);

  const risk = useAnalysis<any, MCAResult>(mcaRiskMap);
  const stats = useAnalysis<any, Record<string, number>>(mcaStats);

  const handleRun = () => {
    const req =
      params.mca_method === "custom"
        ? { geojson, method: "custom" as const, custom_weights: params.custom_weights }
        : { geojson, method: "ahp" as const };
    risk.run(req);
    stats.run({ ...req, w_lulc: 40, w_slope: 30 });
  };

  const ahp = risk.data?.ahp;
  const factorUrls = risk.data?.factor_urls;

  // Determine which tile to show: composite or a specific factor
  const displayTileUrl = activeFactorLayer && factorUrls
    ? factorUrls[activeFactorLayer]
    : risk.data?.tile_url;

  const displayTileName = activeFactorLayer
    ? FACTOR_LABELS[activeFactorLayer] || activeFactorLayer
    : "Flood Susceptibility (AHP-MCDM)";

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>AHP-MCDM Flood Susceptibility</h2>
        <button className="btn btn-primary" onClick={handleRun} disabled={risk.isLoading}>
          {risk.isLoading ? "Computing..." : "RUN AHP-MCDM"}
        </button>
      </div>

      {risk.isLoading && <LoadingOverlay message="Computing 10-factor AHP susceptibility map..." />}
      {risk.error && <ErrorBanner message={risk.error} onDismiss={risk.reset} />}

      {/* AHP Consistency Report */}
      {ahp && (
        <div className="ahp-report">
          <div className="ahp-header">
            <span className="ahp-title">AHP Consistency Report</span>
            <span
              className={`ahp-badge ${ahp.consistent ? "ahp-badge-pass" : "ahp-badge-fail"}`}
            >
              CR = {ahp.cr?.toFixed(4)} {ahp.consistent ? "< 0.10 PASS" : ">= 0.10 FAIL"}
            </span>
          </div>
          <div className="ahp-meta">
            <span>n = {ahp.n_factors} factors</span>
            <span>lambda_max = {ahp.lambda_max?.toFixed(4)}</span>
            <span>CI = {ahp.ci?.toFixed(4)}</span>
            <span>RI = {ahp.ri}</span>
          </div>
        </div>
      )}

      {/* AHP Weight Table */}
      {ahp?.weights && (
        <div className="ahp-weights-table">
          <table>
            <thead>
              <tr>
                <th>Factor</th>
                <th>Weight</th>
                <th style={{ width: "50%" }}>Distribution</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(ahp.weights)
                .sort(([, a], [, b]) => b - a)
                .map(([name, weight]) => (
                  <tr key={name}>
                    <td>{FACTOR_LABELS[name] || name}</td>
                    <td>{(weight * 100).toFixed(1)}%</td>
                    <td>
                      <div className="weight-bar-cell">
                        <div
                          className="weight-bar-fill"
                          style={{ width: `${weight * 100 * 3.5}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Factor Layer Toggles */}
      {factorUrls && (
        <div className="factor-toggles">
          <button
            className={`factor-btn ${!activeFactorLayer ? "factor-btn-active" : ""}`}
            onClick={() => setActiveFactorLayer(null)}
          >
            Composite
          </button>
          {Object.keys(factorUrls).map((name) => (
            <button
              key={name}
              className={`factor-btn ${activeFactorLayer === name ? "factor-btn-active" : ""}`}
              onClick={() => setActiveFactorLayer(name === activeFactorLayer ? null : name)}
            >
              {FACTOR_LABELS[name] || name}
            </button>
          ))}
        </div>
      )}

      <TileMap
        center={center}
        tileUrl={displayTileUrl}
        tileName={displayTileName}
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
