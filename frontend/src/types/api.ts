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
