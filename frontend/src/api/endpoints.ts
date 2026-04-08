import { api } from "./client";
import type {
  AnalysisResponse,
  MCARequest,
  MCAResult,
  AHPReport,
  AOIRequest,
  SARRequest,
  SARData,
  SARDepthData,
  CropLossData,
  MLRequest,
  MLClassifyData,
  MLExplainData,
  IndicesRequest,
  DroughtRequest,
  HydrologyRequest,
  ForecastRequest,
  MultiyearRequest,
  ProjectionsRequest,
  ProjectionsData,
  TileData,
  ChartPoint,
  TimeseriesPoint,
  ForecastData,
  HydrologyData,
  IndicesData,
  ScenarioComparisonRequest,
  ScenarioComparisonData,
  MLRiskPredictionData,
  ImpactRequest,
  ImpactData,
  ForecastInundationData,
} from "../types/api";

// ── MCA (AHP-MCDM) ──
export const mcaRiskMap = (req: MCARequest) =>
  api.post<AnalysisResponse<MCAResult>>("/mca/risk-map", req).then((r) => r.data);

export const mcaStats = (req: MCARequest) =>
  api.post<AnalysisResponse<Record<string, number>>>("/mca/stats", req).then((r) => r.data);

export const mcaAhpWeights = () =>
  api.get<AnalysisResponse<AHPReport>>("/mca/ahp-weights").then((r) => r.data);

export const mcaFactorStats = (req: AOIRequest) =>
  api.post<AnalysisResponse<Record<string, Record<string, number>>>>("/mca/factor-stats", req).then((r) => r.data);

// ── SAR ──
export const sarFloodDetection = (req: SARRequest) =>
  api.post<AnalysisResponse<SARData>>("/sar/flood-detection", req).then((r) => r.data);

export const sarDepth = (req: SARRequest) =>
  api.post<AnalysisResponse<SARDepthData>>("/sar/depth", req).then((r) => r.data);

export const sarCropLoss = (req: SARRequest & { crop_type?: string; crop_price?: number }) =>
  api.post<AnalysisResponse<CropLossData>>("/sar/crop-loss", req).then((r) => r.data);

export const sarTimeseries = (req: SARRequest) =>
  api.post<AnalysisResponse<{ series: TimeseriesPoint[] }>>("/sar/timeseries", req).then((r) => r.data);

// ── ML ──
export const mlClassify = (req: MLRequest) =>
  api.post<AnalysisResponse<MLClassifyData>>("/ml/classify", req).then((r) => r.data);

export const mlExplain = (req: MLRequest) =>
  api.post<AnalysisResponse<MLExplainData>>("/ml/explain", req).then((r) => r.data);

export const mlRiskPrediction = (req: MLRequest) =>
  api.post<AnalysisResponse<MLRiskPredictionData>>("/ml/risk-prediction", req).then((r) => r.data);

// ── Indices ──
export const indicesTiles = (req: IndicesRequest) =>
  api.post<AnalysisResponse<IndicesData>>("/indices/tiles", req).then((r) => r.data);

// ── Drought ──
export const droughtAnalysis = (req: DroughtRequest) =>
  api.post<AnalysisResponse<{ spi: TileData; ndvi_anomaly: TileData }>>("/drought/analysis", req).then((r) => r.data);

// ── Hydrology ──
export const hydrologyAnalysis = (req: HydrologyRequest) =>
  api.post<AnalysisResponse<HydrologyData>>("/hydrology/analysis", req).then((r) => r.data);

// ── Multiyear ──
export const multiyearComparison = (req: MultiyearRequest) =>
  api.post<AnalysisResponse<{ chart: ChartPoint[]; tiles: TileData[] }>>("/multiyear/comparison", req).then((r) => r.data);

// ── Forecast ──
export const forecastWeather = (req: ForecastRequest) =>
  api.post<AnalysisResponse<ForecastData>>("/forecast/weather", req).then((r) => r.data);

// ── Projections ──
export const projectionsAnalysis = (req: ProjectionsRequest) =>
  api.post<AnalysisResponse<ProjectionsData>>("/projections/analysis", req).then((r) => r.data);

export const scenarioComparison = (req: ScenarioComparisonRequest) =>
  api.post<AnalysisResponse<ScenarioComparisonData>>("/projections/scenario-comparison", req).then((r) => r.data);

// ── Impact ──
export const impactAssessment = (req: ImpactRequest) =>
  api.post<AnalysisResponse<ImpactData>>("/impact/assessment", req).then((r) => r.data);

// ── Forecast Inundation ──
export const forecastInundation = (req: { geojson: GeoJSON.Geometry; flood_depth_m?: number; stream_threshold?: number; forecast_days?: number }) =>
  api.post<AnalysisResponse<ForecastInundationData>>("/forecast/inundation", req).then((r) => r.data);

// ── Advanced ──
export const advancedFusion = (req: SARRequest & { cloud_thresh?: number; fusion_weight?: number }) =>
  api.post<AnalysisResponse>("/advanced/fusion", req).then((r) => r.data);

export const advancedBatch = (req: { aois: Record<string, any>[]; analysis_type?: string }) =>
  api.post<AnalysisResponse>("/advanced/batch", req).then((r) => r.data);

export const advancedWatchpointCheck = (req: { geojson: GeoJSON.Geometry; name: string; alert_threshold_ha?: number }) =>
  api.post<AnalysisResponse>("/advanced/watchpoint/check", req).then((r) => r.data);

// ── Geocoding ──
export const geocode = (query: string) =>
  api.get<{ lat: number; lon: number; display_name: string }>("/geocode", { params: { q: query } }).then((r) => r.data);

// ── Health ──
export const healthCheck = () =>
  api.get<{ status: string }>("/health").then((r) => r.data);
