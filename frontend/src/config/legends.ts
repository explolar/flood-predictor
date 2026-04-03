/* ── Legend configurations keyed by layer name ── */

export interface LegendConfig {
  title: string;
  type: "continuous" | "discrete";
  /** Hex colors (without #) */
  palette: string[];
  min?: number;
  max?: number;
  /** Labels for discrete swatches (same order as palette) */
  labels?: string[];
  unit?: string;
}

export const LEGENDS: Record<string, LegendConfig> = {
  /* ── Multi-Criteria Analysis ── */
  "MCA Composite": {
    title: "MCA Composite",
    type: "discrete",
    palette: ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"],
    labels: ["Very Low", "Low", "Moderate", "High", "Very High"],
    min: 1,
    max: 5,
  },

  /* ── SAR layers ── */
  "SAR Flood": {
    title: "SAR Flood",
    type: "discrete",
    palette: ["00FFFF"],
    labels: ["Flood"],
  },
  "SAR Severity": {
    title: "SAR Severity",
    type: "discrete",
    palette: ["ffffbf", "fc8d59", "d73027"],
    labels: ["Low", "Medium", "High"],
  },

  /* ── ML model ── */
  "ML Probability": {
    title: "ML Probability",
    type: "continuous",
    palette: ["000005", "0d1b2a", "1b4f72", "2e86c1", "00FFFF", "ffffff"],
    min: 0,
    max: 100,
    unit: "%",
  },

  /* ── Spectral indices ── */
  NDVI: {
    title: "NDVI",
    type: "continuous",
    palette: ["d73027", "fee08b", "1a9850"],
    min: -1,
    max: 1,
    unit: "",
  },
  NDWI: {
    title: "NDWI",
    type: "continuous",
    palette: ["d73027", "ffffbf", "2166ac"],
    min: -1,
    max: 1,
    unit: "",
  },
  MNDWI: {
    title: "MNDWI",
    type: "continuous",
    palette: ["d73027", "ffffbf", "2166ac"],
    min: -1,
    max: 1,
    unit: "",
  },
  NDBI: {
    title: "NDBI",
    type: "continuous",
    palette: ["2166ac", "f7f7f7", "d73027"],
    min: -1,
    max: 1,
    unit: "",
  },
  BSI: {
    title: "BSI",
    type: "continuous",
    palette: ["1a9850", "f7f7f7", "d73027"],
    min: -1,
    max: 1,
    unit: "",
  },
  SAVI: {
    title: "SAVI",
    type: "continuous",
    palette: ["d73027", "fee08b", "1a9850"],
    min: -1,
    max: 1,
    unit: "",
  },
  EVI: {
    title: "EVI",
    type: "continuous",
    palette: ["d73027", "fee08b", "1a9850"],
    min: -1,
    max: 1,
    unit: "",
  },

  /* ── Hydrology ── */
  "Stream Network": {
    title: "Stream Network",
    type: "discrete",
    palette: ["0000FF"],
    labels: ["Stream"],
  },
  "Flow Accumulation": {
    title: "Flow Accumulation",
    type: "continuous",
    palette: ["f7fbff", "6baed6", "08306b"],
    min: 0,
    max: 1000,
    unit: "",
  },
  "Flow Direction": {
    title: "Flow Direction",
    type: "continuous",
    palette: ["440154", "31688e", "35b779", "fde725"],
    min: 0,
    max: 360,
    unit: "\u00b0",
  },

  /* ── Climate / forecast ── */
  SPI: {
    title: "SPI",
    type: "continuous",
    palette: ["d73027", "fee08b", "1a9850"],
    min: -3,
    max: 3,
    unit: "",
  },
  "NDVI Anomaly": {
    title: "NDVI Anomaly",
    type: "continuous",
    palette: ["d73027", "fee08b", "1a9850"],
    min: -0.3,
    max: 0.3,
  },
  "Precipitation Forecast": {
    title: "Precipitation",
    type: "continuous",
    palette: ["f7fbff", "c6dbef", "6baed6", "2171b5", "08306b"],
    min: 0,
    max: 200,
    unit: "mm",
  },
  "Temperature Forecast": {
    title: "Temperature",
    type: "continuous",
    palette: ["3288bd", "99d594", "e6f598", "fee08b", "fc8d59", "d53e4f"],
    min: 10,
    max: 45,
    unit: "\u00b0C",
  },
};
