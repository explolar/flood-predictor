import { useState } from "react";
import { TileMap } from "../components/map/TileMap";
import { LoadingOverlay } from "../components/common/LoadingOverlay";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useAnalysis } from "../hooks/useAnalysis";
import { mlClassify, mlRiskPrediction } from "../api/endpoints";
import type { SidebarParams } from "../components/layout/Sidebar";
import type { TileData } from "../types/api";

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
  const [showProb, setShowProb] = useState(false);

  const classify = useAnalysis<any, TileData>(mlClassify);
  const risk = useAnalysis<any, TileData>(mlRiskPrediction);

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
  };

  const handleRisk = () => {
    risk.run({ ...sarReq, model, return_probability: false });
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>ML Intelligence</h2>
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
            CLASSIFY
          </button>
          <button className="btn btn-secondary" onClick={handleRisk} disabled={risk.isLoading}>
            RISK MAP
          </button>
        </div>
      </div>

      {(classify.isLoading || risk.isLoading) && <LoadingOverlay message="Running ML model..." />}
      {classify.error && <ErrorBanner message={classify.error} onDismiss={classify.reset} />}
      {risk.error && <ErrorBanner message={risk.error} onDismiss={risk.reset} />}

      <div className="map-grid">
        <div>
          <h3 className="map-title">Classification ({MODELS.find((m) => m.id === model)?.label})</h3>
          <TileMap center={center} tileUrl={classify.data?.tile_url} tileName="ML Classification" height="400px" />
        </div>
        <div>
          <h3 className="map-title">Risk Prediction</h3>
          <TileMap center={center} tileUrl={risk.data?.tile_url} tileName="Risk Prediction" height="400px" />
        </div>
      </div>
    </div>
  );
}
