/** Shared API types mirroring FastAPI schemas */

export interface AOIRequest {
  geojson: GeoJSON.Geometry;
  name?: string;
}

export interface MCARequest extends AOIRequest {
  method: "ahp" | "custom";
  custom_weights?: Record<string, number>;
  /** @deprecated Legacy fields kept for backward compatibility */
  w_lulc?: number;
  w_slope?: number;
  w_rain?: number;
}

export interface SARRequest extends AOIRequest {
  f_start: string;
  f_end: string;
  p_start: string;
  p_end: string;
  threshold: number;
  polarization: "VH" | "VV";
  speckle: boolean;
}

export interface MLRequest extends SARRequest {
  model: "gradient_boosting" | "xgboost" | "lightgbm" | "ensemble";
  return_probability: boolean;
}

export interface IndicesRequest extends AOIRequest {
  date_start: string;
  date_end: string;
  cloud_thresh: number;
}

export interface DroughtRequest extends AOIRequest {
  year: number;
}

export interface HydrologyRequest extends AOIRequest {
  stream_threshold?: number;
  flood_depth?: number;
}

export interface ForecastRequest extends AOIRequest {
  forecast_days?: number;
}

export interface MultiyearRequest extends AOIRequest {
  years: number[];
  polarization: "VH" | "VV";
  threshold: number;
}

export interface ProjectionsRequest extends AOIRequest {
  scenario: string;
  model: string;
  start_year: number;
  end_year: number;
}

export interface ScenarioComparisonRequest extends AOIRequest {
  model?: string;
  periods?: string[];
}

export interface AnalysisResponse<T = Record<string, unknown>> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface TileData {
  tile_url: string;
  metadata?: Record<string, unknown>;
}

export interface SARData {
  area_ha: number;
  pop_exposed: number;
  flood_url: string;
  severity_url: string;
  water_url?: string;
  pre_url?: string;
  post_url?: string;
  diff_url?: string;
}

export interface SARDepthData {
  tile_url: string;
  mean_depth: number;
  max_depth: number;
  histogram: Record<string, number>;
}

export interface CropLossData {
  affected_ha: number;
  estimated_loss_usd: number;
  message?: string;
}

export interface AHPReport {
  weights: Record<string, number>;
  cr: number | null;
  ci: number | null;
  lambda_max: number | null;
  consistent: boolean;
  ri: number;
  n_factors: number;
}

export interface MCAResult {
  tile_url: string;
  factor_urls: Record<string, string>;
  ahp: AHPReport;
}

export interface MCAStats {
  tile_url: string;
  stats?: Record<string, number>;
}

export interface IndexTile {
  name: string;
  tile_url: string;
  metrics?: Record<string, number>;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface TimeseriesPoint {
  date: string;
  value: number;
}

export interface ForecastData {
  precip_tile_url: string;
  temp_tile_url: string;
  total_precip_mm: number;
  max_daily_precip_mm: number;
  mean_temp_c: number;
  max_wind_ms: number;
  forecast_days: number;
  n_steps: number;
  daily_df: { date: string; precip_mm: number; temp_c: number }[];
}

export interface HydrologyData {
  flow_acc_url: string;
  flow_dir_url: string;
  stream_url: string;
  cond_dem_url: string;
  stream_length_km: number;
  max_accumulation: number;
  mean_accumulation: number;
  dem_min: number;
  dem_max: number;
  dem_mean: number;
}

export interface IndicesData {
  indices: Record<string, { tile_url: string; mean_value: number; n_scenes: number }>;
}

export interface ProjectionsData {
  mean_precip_mm_yr?: number;
  mean_tasmax_c?: number;
  mean_tasmin_c?: number;
  precip_tile_url?: string;
  temp_tile_url?: string;
  scenario?: string;
  model?: string;
  period?: string;
}

export interface ScenarioComparisonData {
  model: string;
  comparison: Record<string, string | number>[];
}

export interface DroughtData {
  spi: { tile_url: string; value?: number };
  ndvi_anomaly: { tile_url: string; value?: number };
}

export interface MultiyearData {
  chart: ChartPoint[];
  tiles: TileData[];
}

export interface MLClassifyData {
  tile_url: string;
  ml_area_ha?: number;
  threshold_area_ha?: number;
  n_samples?: number;
  oob_score?: number;
  feature_importance?: Record<string, number>;
}

export interface MLExplainData {
  shap_importance?: Record<string, number>;
  summary_plot_b64?: string;
  n_samples_explained?: number;
  model_name?: string;
}

export interface MLRiskPredictionData {
  tile_url: string;
  n_samples: number;
  oob_score?: number;
  feature_importance?: Record<string, number>;
  risk_distribution: Record<string, number>;
}

/** Impact module types */
export interface ImpactRequest extends SARRequest {
  include_population?: boolean;
  include_buildings?: boolean;
  include_infrastructure?: boolean;
  include_crop_loss?: boolean;
  crop_type?: string;
  crop_price?: number;
}

export interface PopulationImpact {
  total_population: number;
  displaced_estimate: number;
  children_affected: number;
  elderly_affected: number;
  displacement_rate: number;
}

export interface BuildingDamage {
  total_buildings: number;
  total_affected: number;
  damage_counts: { minor: number; moderate: number; severe: number; destroyed: number };
  tile_url?: string;
}

export interface InfrastructureImpact {
  facilities: { lat: number; lon: number; type: string; name: string }[];
  roads?: { total_km: number; km_by_type: Record<string, number> };
  dams?: { name: string; river: string; capacity_mcm: number }[];
}

export interface ImpactData {
  flood_area_ha: number;
  population?: PopulationImpact;
  buildings?: BuildingDamage;
  infrastructure?: InfrastructureImpact;
  crop_loss?: CropLossData;
}

/** Forecast inundation types */
export interface ForecastInundationData {
  observed_flood_url?: string;
  forecast_flood_url?: string;
  forecast_depth_url?: string;
  observed_area_ha?: number;
  forecast_area_ha?: number;
  alert_level?: string;
  alert_color?: string;
  forecast_max_precip_mm?: number;
  exceedance_return_period?: number;
  hand_stats?: {
    mean_hand_m: number;
    p10_hand_m: number;
    p50_hand_m: number;
    p90_hand_m: number;
  };
}

/** SAR 2.0 types */
export type ReferenceStrategy = "event_pair" | "seasonal_baseline" | "rolling_baseline" | "anomaly_mode";

export interface SAR2Request extends SARRequest {
  reference_strategy?: ReferenceStrategy;
  rolling_days?: number;
  include_optical?: boolean;
}

export interface SARQualityMetadata {
  n_pre_scenes: number;
  n_post_scenes: number;
  orbit_consistency: boolean;
  temporal_gap_days: number;
  confidence_score: number;
  low_data_warning?: string;
  reference_strategy: ReferenceStrategy;
}

export interface SAR2Data extends SARData {
  quality: SARQualityMetadata;
  optical_context_url?: string;
}
