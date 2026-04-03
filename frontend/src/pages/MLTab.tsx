import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { MetricCard } from "../components/common/MetricCard";
import { useAnalysis } from "../hooks/useAnalysis";
import { mlClassify, mlExplain } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import { LEGENDS } from "../config/legends";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ClassifyData {
  tile_url?: string;
  ml_area_ha?: number;
  threshold_area_ha?: number;
  n_samples?: number;
  feature_importance?: Record<string, number>;
}

interface ShapData {
  shap_importance?: Record<string, number>;
  summary_plot_b64?: string;
  n_samples_explained?: number;
  model_name?: string;
}

interface Props {
  geojson: GeoJSON.Geometry;
  center: [number, number];
  params: SidebarParams;
}

const MODELS = [
  { id: "gradient_boosting", label: "Gradient Boosting" },
  { id: "xgboost", label: "XGBoost" },
  { id: "lightgbm", label: "LightGBM" },
  { id: "ensemble", label: "Ensemble Stack" },
] as const;

export function MLTab({ geojson, center, params }: Props) {
  const [model, setModel] = useState<string>("gradient_boosting");
  const [showProb, setShowProb] = useState(true);

  const classify = useAnalysis<any, ClassifyData>(mlClassify);
  const shap = useAnalysis<any, ShapData>(mlExplain);

  const sarReq = {
    geojson,
    f_start: params.f_start,
    f_end: params.f_end,
    p_start: params.p_start,
    p_end: params.p_end,
    threshold: params.threshold,
    polarization: params.polarization,
    speckle: params.speckle,
  };

  const handleClassify = () => {
    classify.run({ ...sarReq, model, return_probability: showProb });
    shap.reset();
  };

  const handleExplain = () => {
    shap.run({ ...sarReq, model, return_probability: showProb });
  };

  const data = classify.data;
  const shapData = shap.data;

  // Build feature importance chart data
  const importanceData = data?.feature_importance
    ? Object.entries(data.feature_importance)
        .map(([name, value]) => ({ name: name.replace(/_/g, " "), value: +(value * 100).toFixed(1) }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)
    : [];

  // Build SHAP importance chart data
  const shapImportanceData = shapData?.shap_importance
    ? Object.entries(shapData.shap_importance)
        .map(([name, value]) => ({ name: name.replace(/_/g, " "), value: +value.toFixed(4) }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)
    : [];

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>ML Flood Classification</h2>
        <div className="tab-actions">
          <select className="select" value={model} onChange={(e) => setModel(e.target.value)}>
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <label className="checkbox-label">
            <input type="checkbox" checked={showProb} onChange={(e) => setShowProb(e.target.checked)} />
            Probability
          </label>
          <button className="btn btn-primary" onClick={handleClassify} disabled={classify.isLoading}>
            {classify.isLoading ? "Classifying..." : "CLASSIFY"}
          </button>
          {data && (
            <button
              className="btn btn-primary"
              onClick={handleExplain}
              disabled={shap.isLoading}
              style={{ backgroundColor: "#d97706", borderColor: "#d97706" }}
            >
              {shap.isLoading ? "Computing SHAP..." : "SHAP EXPLAIN"}
            </button>
          )}
        </div>
      </div>

      {classify.isLoading && <LoadingOverlay message="Running ML model..." />}
      {shap.isLoading && <LoadingOverlay message="Computing SHAP explanations..." />}
      {classify.error && <ErrorBanner message={classify.error} onDismiss={classify.reset} />}
      {shap.error && <ErrorBanner message={shap.error} onDismiss={shap.reset} />}

      {data && (
        <>
          <h3 className="map-title">
            Classification ({MODELS.find((m) => m.id === model)?.label})
          </h3>
          <TileMap center={center} tileUrl={data.tile_url} tileName="ML Classification" height="460px" legend={LEGENDS["ML Probability"]} />

          <div className="metrics-grid">
            {data.ml_area_ha != null && (
              <MetricCard label="ML Flood Area" value={data.ml_area_ha.toFixed(1)} unit="ha" color="#ff6b81" />
            )}
            {data.threshold_area_ha != null && (
              <MetricCard label="Threshold Area" value={data.threshold_area_ha.toFixed(1)} unit="ha" color="#ffc554" />
            )}
            {data.n_samples != null && (
              <MetricCard label="Samples" value={data.n_samples.toLocaleString()} />
            )}
          </div>

          {importanceData.length > 0 && (
            <div className="chart-container">
              <h3>Feature Importance</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={importanceData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" unit="%" />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => `${v}%`} />
                  <Bar dataKey="value" name="Importance" fill="var(--accent, #0891b2)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {shapImportanceData.length > 0 && (
            <div className="chart-container">
              <h3>SHAP Feature Importance (mean |SHAP| value)</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary, #94a3b8)", margin: "0 0 0.5rem 0" }}>
                {shapData?.n_samples_explained != null
                  ? `Computed over ${shapData.n_samples_explained} samples using TreeExplainer`
                  : "Computed using TreeExplainer"}
              </p>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={shapImportanceData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => Number(v).toFixed(4)} />
                  <Bar dataKey="value" name="mean |SHAP|" fill="#d97706" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {shapData?.summary_plot_b64 && (
            <div className="chart-container">
              <h3>SHAP Summary Plot</h3>
              <img
                src={`data:image/png;base64,${shapData.summary_plot_b64}`}
                alt="SHAP summary plot"
                style={{ width: "100%", maxWidth: 700, borderRadius: 8 }}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
