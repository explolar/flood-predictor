import { useState, useMemo } from "react";
import { TileMap } from "../components/map/TileMap";
import { MetricCard } from "../components/common/MetricCard";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { sarFloodDetection, sarDepth, sarCropLoss, sarTimeseries } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { SAR2Data, SARData, SARDepthData, CropLossData, SARQualityMetadata, TimeseriesPoint, ReferenceStrategy } from "../types/api";
import { LEGENDS } from "../config/legends";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

type SubTab = "detection" | "depth" | "crop-loss" | "timeseries";

const STRATEGY_OPTIONS: { value: ReferenceStrategy; label: string; desc: string }[] = [
  { value: "event_pair", label: "Event Pair", desc: "Pre/post median (default)" },
  { value: "seasonal_baseline", label: "Seasonal Baseline", desc: "Same season, prior 3 years" },
  { value: "rolling_baseline", label: "Rolling Baseline", desc: "Trailing N-day reference" },
  { value: "anomaly_mode", label: "Anomaly Mode", desc: "5-year historical normal" },
];

export function SARTab({ geojson, center, params }: Props) {
  const [subTab, setSubTab] = useState<SubTab>("detection");
  const [strategy, setStrategy] = useState<ReferenceStrategy>("event_pair");
  const [rollingDays, setRollingDays] = useState(90);
  const [includeOptical, setIncludeOptical] = useState(false);

  const sarParams = {
    geojson,
    f_start: params.f_start,
    f_end: params.f_end,
    p_start: params.p_start,
    p_end: params.p_end,
    threshold: params.threshold,
    polarization: params.polarization,
    speckle: params.speckle,
  };

  const sar = useAnalysis<any, SAR2Data>(sarFloodDetection as any);
  const depth = useAnalysis<any, SARDepthData>(sarDepth);
  const cropLoss = useAnalysis<any, CropLossData>(sarCropLoss);
  const timeseries = useAnalysis<any, { series: TimeseriesPoint[] }>(sarTimeseries);

  const handleRunDetection = () =>
    sar.run({
      ...sarParams,
      reference_strategy: strategy,
      rolling_days: rollingDays,
      include_optical: includeOptical,
    });
  const handleRunDepth = () => depth.run(sarParams);
  const handleRunCropLoss = () =>
    cropLoss.run({ ...sarParams, crop_type: params.crop_type, crop_price: params.crop_price });
  const handleRunTimeseries = () => timeseries.run(sarParams);

  return (
    <div className="tab-content">
      <nav className="sub-tab-bar">
        <button className={`tab-item ${subTab === "detection" ? "tab-active" : ""}`} onClick={() => setSubTab("detection")}>FLOOD DETECTION</button>
        <button className={`tab-item ${subTab === "depth" ? "tab-active" : ""}`} onClick={() => setSubTab("depth")}>FLOOD DEPTH</button>
        <button className={`tab-item ${subTab === "crop-loss" ? "tab-active" : ""}`} onClick={() => setSubTab("crop-loss")}>CROP LOSS</button>
        <button className={`tab-item ${subTab === "timeseries" ? "tab-active" : ""}`} onClick={() => setSubTab("timeseries")}>TIMESERIES</button>
      </nav>

      {/* ── Flood Detection ── */}
      {subTab === "detection" && (
        <>
          <div className="tab-header">
            <h2>SAR Flood Detection</h2>
            <div className="tab-actions">
              <select className="select" value={strategy} onChange={(e) => setStrategy(e.target.value as ReferenceStrategy)}>
                {STRATEGY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              {strategy === "rolling_baseline" && (
                <label className="label-inline">
                  Days:
                  <input type="number" className="input input-sm" value={rollingDays} onChange={(e) => setRollingDays(+e.target.value)} min={30} max={365} step={15} style={{ width: 70 }} />
                </label>
              )}
              <label className="label-inline" style={{ gap: 4 }}>
                <input type="checkbox" checked={includeOptical} onChange={(e) => setIncludeOptical(e.target.checked)} />
                S2 context
              </label>
              <button className="btn btn-primary" onClick={handleRunDetection} disabled={sar.isLoading}>
                {sar.isLoading ? "Detecting..." : "RUN SAR DETECTION"}
              </button>
            </div>
          </div>

          {sar.isLoading && <LoadingOverlay message="Processing Sentinel-1 SAR data..." estimatedSeconds={60} />}
          {sar.error && <ErrorBanner message={sar.error} onDismiss={sar.reset} />}

          {sar.data?.quality && <QualityCard quality={sar.data.quality} />}

          {sar.data && (
            <div className="metrics-grid">
              <MetricCard label="Flooded Area" value={sar.data.area_ha.toFixed(1)} unit="ha" color="#ff6b81" />
              <MetricCard label="Population Exposed" value={sar.data.pop_exposed} color="#ffc554" />
              {sar.data.quality && (
                <MetricCard label="Confidence" value={`${(sar.data.quality.confidence_score * 100).toFixed(0)}%`} color={sar.data.quality.confidence_score >= 0.6 ? "#1a9850" : "#d73027"} />
              )}
            </div>
          )}

          {sar.data && <SARSummary data={sar.data} />}

          <div className="map-grid">
            <div>
              <h3 className="map-title">Flood Mask</h3>
              <TileMap center={center} tileUrl={sar.data?.flood_url} tileName="Flood Mask" height="460px" legend={LEGENDS["SAR Flood"]} />
            </div>
            <div>
              <h3 className="map-title">Severity Zones</h3>
              <TileMap center={center} tileUrl={sar.data?.severity_url} tileName="Severity" height="460px" legend={LEGENDS["SAR Severity"]} />
            </div>
          </div>

          {sar.data?.optical_context_url && (
            <div style={{ marginTop: "1rem" }}>
              <h3 className="map-title">Sentinel-2 Optical Context</h3>
              <TileMap center={center} tileUrl={sar.data.optical_context_url} tileName="S2 True Color" height="400px" />
            </div>
          )}
        </>
      )}

      {/* ── Flood Depth ── */}
      {subTab === "depth" && (
        <>
          <div className="tab-header">
            <h2>SAR Flood Depth Estimation</h2>
            <button className="btn btn-primary" onClick={handleRunDepth} disabled={depth.isLoading}>
              {depth.isLoading ? "Computing..." : "ESTIMATE DEPTH"}
            </button>
          </div>

          {depth.isLoading && <LoadingOverlay message="Estimating flood depth from DEM + SAR..." estimatedSeconds={90} />}
          {depth.error && <ErrorBanner message={depth.error} onDismiss={depth.reset} />}

          {depth.data && (
            <>
              <div className="metrics-grid">
                <MetricCard label="Mean Depth" value={depth.data.mean_depth?.toFixed(2) ?? "N/A"} unit="m" color="#2171b5" />
                <MetricCard label="Max Depth" value={depth.data.max_depth?.toFixed(2) ?? "N/A"} unit="m" color="#08306b" />
              </div>

              <TileMap
                center={center}
                tileUrl={depth.data.tile_url}
                tileName="Flood Depth"
                height="500px"
                legend={LEGENDS["Flood Depth"]}
              />

              {depth.data.histogram && <DepthHistogram histogram={depth.data.histogram} />}
            </>
          )}
        </>
      )}

      {/* ── Crop Loss ── */}
      {subTab === "crop-loss" && (
        <>
          <div className="tab-header">
            <h2>Crop Loss Estimation</h2>
            <div className="tab-actions">
              <span className="label-inline">
                Crop: <strong>{params.crop_type}</strong> @ ₹{params.crop_price}/ha
              </span>
              <button className="btn btn-primary" onClick={handleRunCropLoss} disabled={cropLoss.isLoading}>
                {cropLoss.isLoading ? "Computing..." : "ESTIMATE CROP LOSS"}
              </button>
            </div>
          </div>

          {cropLoss.isLoading && <LoadingOverlay message="Intersecting flood mask with cropland..." estimatedSeconds={60} />}
          {cropLoss.error && <ErrorBanner message={cropLoss.error} onDismiss={cropLoss.reset} />}

          {cropLoss.data && (
            <>
              <div className="metrics-grid">
                <MetricCard label="Affected Cropland" value={cropLoss.data.affected_ha.toFixed(1)} unit="ha" color="#e6550d" />
                <MetricCard
                  label="Estimated Loss"
                  value={`₹${cropLoss.data.estimated_loss_usd.toLocaleString()}`}
                  color="#d73027"
                />
              </div>
              {cropLoss.data.message && (
                <p style={{ color: "var(--text-secondary)", marginTop: "0.75rem" }}>{cropLoss.data.message}</p>
              )}
            </>
          )}
        </>
      )}

      {/* ── Timeseries ── */}
      {subTab === "timeseries" && (
        <>
          <div className="tab-header">
            <h2>SAR Backscatter Timeseries</h2>
            <button className="btn btn-primary" onClick={handleRunTimeseries} disabled={timeseries.isLoading}>
              {timeseries.isLoading ? "Loading..." : "LOAD TIMESERIES"}
            </button>
          </div>

          {timeseries.isLoading && <LoadingOverlay message="Extracting SAR time-series..." estimatedSeconds={45} />}
          {timeseries.error && <ErrorBanner message={timeseries.error} onDismiss={timeseries.reset} />}

          {timeseries.data?.series && timeseries.data.series.length > 0 && (
            <>
              <div className="metrics-grid">
                <MetricCard label="Observations" value={timeseries.data.series.length} color="var(--accent)" />
                <MetricCard
                  label="Mean Backscatter"
                  value={(timeseries.data.series.reduce((s, p) => s + p.value, 0) / timeseries.data.series.length).toFixed(2)}
                  unit="dB"
                  color="#6baed6"
                />
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={timeseries.data.series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" stroke="#4a5568" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={60} />
                    <YAxis stroke="#4a5568" label={{ value: "dB", angle: -90, position: "insideLeft" }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#0891b2" strokeWidth={2} dot={{ r: 3 }} name="Backscatter (dB)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {timeseries.data?.series && timeseries.data.series.length === 0 && (
            <p style={{ color: "var(--text-secondary)", textAlign: "center", marginTop: "2rem" }}>
              No SAR observations found for the selected date range.
            </p>
          )}
        </>
      )}
    </div>
  );
}

/* ---------- Quality Card ---------- */

function QualityCard({ quality }: { quality: SARQualityMetadata }) {
  const confColor = quality.confidence_score >= 0.7 ? "#1a9850" : quality.confidence_score >= 0.4 ? "#fee08b" : "#d73027";

  return (
    <div className="ahp-weights-table" style={{ marginBottom: "1rem" }}>
      <table>
        <thead>
          <tr><th colSpan={2}>Data Quality Report</th></tr>
        </thead>
        <tbody>
          <tr><td>Reference Strategy</td><td className="weight-value">{quality.reference_strategy.replace(/_/g, " ")}</td></tr>
          <tr><td>Pre-flood Scenes</td><td className="weight-value">{quality.n_pre_scenes}</td></tr>
          <tr><td>Post-flood Scenes</td><td className="weight-value">{quality.n_post_scenes}</td></tr>
          <tr><td>Orbit Consistency</td><td className="weight-value">{quality.orbit_consistency ? "Yes" : "No"}</td></tr>
          <tr><td>Temporal Gap</td><td className="weight-value">{quality.temporal_gap_days} days</td></tr>
          <tr>
            <td>Confidence Score</td>
            <td className="weight-value" style={{ color: confColor, fontWeight: 600 }}>
              {(quality.confidence_score * 100).toFixed(0)}%
            </td>
          </tr>
          {quality.low_data_warning && (
            <tr><td colSpan={2} style={{ color: "#d73027", fontSize: "0.85rem" }}>{quality.low_data_warning}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Depth Histogram ---------- */

function DepthHistogram({ histogram }: { histogram: Record<string, number> }) {
  const data = Object.entries(histogram).map(([range, count]) => ({ range, count }));

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <h3 className="map-title">Depth Distribution</h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="range" stroke="#4a5568" label={{ value: "Depth (m)", position: "insideBottom", offset: -5 }} />
            <YAxis stroke="#4a5568" label={{ value: "Pixels", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Bar dataKey="count" fill="#2171b5" name="Pixel Count" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ---------- SAR Summary ---------- */

const PIE_COLORS = ["#0891b2", "#a5f3fc"];

function formatValue(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v ?? "N/A");
}

function SARSummary({ data }: { data: SARData }) {
  const rows = useMemo(() => {
    const entries: { metric: string; value: string }[] = [];
    for (const [key, val] of Object.entries(data)) {
      if (typeof val === "string" && val.startsWith("http")) continue;
      if (typeof val === "object") continue; // skip quality object
      entries.push({
        metric: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        value: formatValue(val),
      });
    }
    return entries;
  }, [data]);

  const dataAny = data as any;
  const totalArea = dataAny.total_area_ha ? Number(dataAny.total_area_ha) : data.area_ha * 10;
  const nonFlood = Math.max(totalArea - data.area_ha, 0);

  const pieData = [
    { name: "Flooded", value: Math.round(data.area_ha * 100) / 100 },
    { name: "Non-Flooded", value: Math.round(nonFlood * 100) / 100 },
  ];

  return (
    <>
      <h3 className="map-title" style={{ marginTop: "1.5rem" }}>SAR Detection Summary</h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", alignItems: "start" }}>
        <div className="ahp-weights-table">
          <table>
            <thead>
              <tr><th>Metric</th><th>Value</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="weight-value">{r.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="chart-container">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(1)}%`}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value} ha`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
