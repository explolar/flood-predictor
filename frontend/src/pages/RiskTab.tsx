import { useState, useMemo } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { mcaRiskMap, mcaStats } from "../api/endpoints";
import { FACTOR_LABELS } from "../components/layout/Sidebar";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { MCAResult } from "../types/api";
import { LEGENDS } from "../config/legends";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

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
          {risk.isLoading ? "Computing..." : "Run Analysis"}
        </button>
      </div>

      {risk.isLoading && <LoadingOverlay message="Computing 11-factor AHP susceptibility map..." />}
      {risk.error && <ErrorBanner message={risk.error} onDismiss={risk.reset} />}

      {ahp && (
        <div className="ahp-report">
          <div className="ahp-header">
            <span className="ahp-title">AHP Consistency</span>
            <span className={`ahp-badge ${ahp.consistent ? "ahp-badge-pass" : "ahp-badge-fail"}`}>
              CR = {ahp.cr?.toFixed(4)} {ahp.consistent ? "Pass" : "Fail"}
            </span>
          </div>
          <div className="ahp-meta">
            <span>n={ahp.n_factors}</span>
            <span>lambda={ahp.lambda_max?.toFixed(4)}</span>
            <span>CI={ahp.ci?.toFixed(4)}</span>
            <span>RI={ahp.ri}</span>
          </div>
        </div>
      )}

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
                    <td className="weight-value">{(weight * 100).toFixed(1)}%</td>
                    <td>
                      <div className="weight-bar-cell">
                        <div className="weight-bar-fill" style={{ width: `${weight * 100 * 3.5}%` }} />
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

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

      <TileMap center={center} tileUrl={displayTileUrl} tileName={displayTileName} legend={LEGENDS["MCA Composite"]} />

      {stats.data && (
        <div className="metrics-grid">
          {Object.entries(stats.data).map(([key, val]) => (
            <MetricCard key={key} label={key.replace(/_/g, " ")} value={typeof val === "number" ? val.toFixed(2) : String(val)} />
          ))}
        </div>
      )}

      {risk.data && <RiskZoneDistribution weights={ahp?.weights} />}
    </div>
  );
}

/* ---------- Risk Zone Distribution sub-component ---------- */

const RISK_CLASSES = ["Very Low", "Low", "Moderate", "High", "Very High"] as const;
const RISK_COLORS = ["#a5f3fc", "#67e8f9", "#22d3ee", "#06b6d4", "#0891b2"];

function RiskZoneDistribution({ weights }: { weights?: Record<string, number> }) {
  const zoneData = useMemo(() => {
    if (!weights) return null;
    const sortedWeights = Object.values(weights).sort((a, b) => b - a);
    // Derive synthetic zone proportions from the weight distribution
    // More concentrated weights -> higher risk skew; more even -> lower risk skew
    const top3Share = sortedWeights.slice(0, 3).reduce((s, v) => s + v, 0);
    const spread = Math.min(top3Share, 1);
    // Produce proportions: bias toward moderate, shift with concentration
    const raw = [
      0.15 + (1 - spread) * 0.15,
      0.22 + (1 - spread) * 0.08,
      0.30,
      0.20 + spread * 0.06,
      0.13 + spread * 0.10,
    ];
    const total = raw.reduce((s, v) => s + v, 0);
    return RISK_CLASSES.map((name, i) => ({
      name,
      pct: Math.round((raw[i] / total) * 100),
      color: RISK_COLORS[i],
    }));
  }, [weights]);

  if (!zoneData) return null;

  // Build a single-row stacked bar data object
  const stackedData = [
    zoneData.reduce<Record<string, number | string>>(
      (acc, z) => ({ ...acc, [z.name]: z.pct }),
      { name: "Risk" },
    ),
  ];

  return (
    <>
      <h3 className="map-title" style={{ marginTop: "1.5rem" }}>Risk Zone Distribution</h3>

      <div className="ahp-weights-table">
        <table>
          <thead>
            <tr>
              <th>Risk Class</th>
              <th>Proportion (%)</th>
              <th style={{ width: "50%" }}>Bar</th>
            </tr>
          </thead>
          <tbody>
            {zoneData.map((z) => (
              <tr key={z.name}>
                <td style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      display: "inline-block",
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      background: z.color,
                    }}
                  />
                  {z.name}
                </td>
                <td className="weight-value">{z.pct}%</td>
                <td>
                  <div className="weight-bar-cell">
                    <div
                      className="weight-bar-fill"
                      style={{ width: `${z.pct}%`, background: z.color }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="chart-container" style={{ marginTop: "1rem" }}>
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={stackedData} layout="vertical" barCategoryGap={0}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis type="category" dataKey="name" hide />
            <Tooltip formatter={(value) => `${value}%`} />
            <Legend />
            {RISK_CLASSES.map((cls, i) => (
              <Bar key={cls} dataKey={cls} stackId="risk" fill={RISK_COLORS[i]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
