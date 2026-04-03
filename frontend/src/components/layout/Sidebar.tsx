import { useState, type FormEvent } from "react";
import {
  Search, MapPin, Sliders, Satellite, ChevronDown, ChevronUp,
  Navigation, X, Upload, PenTool,
} from "lucide-react";
import type { BBox } from "../../hooks/useAOI";
import { DrawableMap } from "../map/DrawableMap";

interface SidebarProps {
  onSearchPlace: (query: string) => void;
  onSetBBox: (bbox: BBox) => void;
  onFileUpload: (geojson: GeoJSON.Geometry) => void;
  isAOIActive: boolean;
  aoiName: string;
  existingGeojson?: GeoJSON.Geometry | null;
  params: SidebarParams;
  onParamsChange: (params: Partial<SidebarParams>) => void;
  onClearAOI: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const FACTOR_NAMES = [
  "distance_to_river", "hand", "rainfall", "slope", "elevation", "drainage_density",
  "twi", "lulc", "soil", "ndvi", "curvature",
] as const;

export const FACTOR_LABELS: Record<string, string> = {
  distance_to_river: "Distance to River",
  hand: "HAND",
  rainfall: "Rainfall",
  slope: "Slope",
  elevation: "Elevation",
  drainage_density: "Drainage Density",
  twi: "TWI",
  lulc: "LULC",
  soil: "Soil Texture",
  ndvi: "NDVI",
  curvature: "Curvature",
};

export interface SidebarParams {
  mca_method: "ahp" | "custom";
  custom_weights: Record<string, number>;
  p_start: string;
  p_end: string;
  f_start: string;
  f_end: string;
  polarization: "VH" | "VV";
  threshold: number;
  speckle: boolean;
  img_start: string;
  img_end: string;
  cloud_thresh: number;
  crop_type: string;
  crop_price: number;
  prog_year: number;
}

const DEFAULT_CUSTOM_WEIGHTS: Record<string, number> = {
  distance_to_river: 0.22,
  hand: 0.16,
  rainfall: 0.14,
  slope: 0.10,
  elevation: 0.09,
  drainage_density: 0.07,
  twi: 0.06,
  lulc: 0.05,
  soil: 0.04,
  ndvi: 0.04,
  curvature: 0.03,
};

export const DEFAULT_PARAMS: SidebarParams = {
  mca_method: "ahp",
  custom_weights: { ...DEFAULT_CUSTOM_WEIGHTS },
  p_start: "2024-05-01",
  p_end: "2024-05-30",
  f_start: "2024-08-01",
  f_end: "2024-08-30",
  polarization: "VH",
  threshold: 3.0,
  speckle: true,
  img_start: "2024-01-01",
  img_end: "2024-12-31",
  cloud_thresh: 60,
  crop_type: "Rice (Kharif)",
  crop_price: 75000,
  prog_year: 2024,
};

const QUICK_LOCATIONS = [
  { name: "Patna", query: "Patna, Bihar" },
  { name: "Mumbai", query: "Mumbai, Maharashtra" },
  { name: "Chennai", query: "Chennai, Tamil Nadu" },
  { name: "Kolkata", query: "Kolkata, West Bengal" },
  { name: "Assam", query: "Guwahati, Assam" },
  { name: "Kerala", query: "Kochi, Kerala" },
];

function BrandLogo() {
  return (
    <svg width="34" height="34" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="logo-bg" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0891b2" />
          <stop offset="100%" stopColor="#0e7490" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7" fill="url(#logo-bg)" />
      <path d="M10 7 L22 7 M10 7 L10 25 M10 15 L19 15" stroke="white" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.95" />
      <path d="M8 22 Q12 19 16 22 Q20 25 24 22" stroke="rgba(255,255,255,0.5)" strokeWidth="1.8" strokeLinecap="round" fill="none" />
      <path d="M8 26 Q12 23 16 26 Q20 29 24 26" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function Sidebar({
  onSearchPlace,
  onSetBBox,
  onFileUpload,
  isAOIActive,
  aoiName,
  existingGeojson,
  params,
  onParamsChange,
  onClearAOI,
  collapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [inputMode, setInputMode] = useState<"bbox" | "geojson" | "draw">("bbox");
  const [bbox, setBBox] = useState<BBox>({ minLon: 84.9, minLat: 25.5, maxLon: 85.3, maxLat: 25.8 });
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    location: true,
    aoi: true,
    mca: false,
    sar: false,
    imagery: false,
  });

  const customTotal = Object.values(params.custom_weights).reduce((a, b) => a + b, 0);

  const toggle = (section: string) =>
    setExpandedSections((s) => ({ ...s, [section]: !s[section] }));

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) onSearchPlace(searchQuery.trim());
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string);
        const geom = data.features?.[0]?.geometry || data.geometry || data;
        onFileUpload(geom);
      } catch {
        alert("Invalid GeoJSON file");
      }
    };
    reader.readAsText(file);
  };

  if (collapsed) {
    return (
      <aside className="sidebar sidebar-collapsed">
        <button className="sidebar-expand-btn" onClick={onToggleCollapse} title="Expand sidebar">
          <ChevronDown size={16} style={{ transform: "rotate(-90deg)" }} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand" style={{ display: "flex", alignItems: "center", gap: 10, position: "relative" }}>
        <BrandLogo />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="brand-title" style={{ fontWeight: 700, fontSize: 16, letterSpacing: "0.02em" }}>FluviaAI</div>
          <div className="brand-sub" style={{ fontSize: 10, opacity: 0.55, marginTop: 1 }}>Powered by WeatherEx</div>
        </div>
        <button
          className="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title="Collapse sidebar"
          style={{ position: "absolute", top: 4, right: 4 }}
        >
          <ChevronDown size={14} style={{ transform: "rotate(90deg)" }} />
        </button>
      </div>

      {/* AOI Status Bar */}
      {isAOIActive && (
        <div className="aoi-status-bar">
          <Navigation size={12} />
          <span className="aoi-name">{aoiName || "Custom AOI"}</span>
          <button className="aoi-clear" onClick={onClearAOI} title="Clear AOI">
            <X size={12} />
          </button>
        </div>
      )}

      {/* Location Search */}
      <SectionHeader title="Location Search" icon={<Search size={14} />} open={expandedSections.location} onToggle={() => toggle("location")} />
      {expandedSections.location && (
        <div className="sidebar-section">
          <form onSubmit={handleSearch} className="search-row">
            <input
              type="text"
              placeholder="Search any location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input"
            />
            <button type="submit" className="btn btn-primary btn-icon" title="Search">
              <Search size={14} />
            </button>
          </form>

          <div className="quick-locations">
            {QUICK_LOCATIONS.map((loc) => (
              <button
                key={loc.name}
                className="quick-loc-btn"
                onClick={() => onSearchPlace(loc.query)}
              >
                <MapPin size={10} />
                {loc.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <hr className="sidebar-hr" />

      {/* AOI Boundary */}
      <SectionHeader title="AOI Boundary" icon={<MapPin size={14} />} open={expandedSections.aoi} onToggle={() => toggle("aoi")} />
      {expandedSections.aoi && (
        <div className="sidebar-section">
          <div className="radio-group">
            <label>
              <input type="radio" checked={inputMode === "bbox"} onChange={() => setInputMode("bbox")} />
              Bounding Box
            </label>
            <label>
              <input type="radio" checked={inputMode === "geojson"} onChange={() => setInputMode("geojson")} />
              GeoJSON
            </label>
            <label>
              <input type="radio" checked={inputMode === "draw"} onChange={() => setInputMode("draw")} />
              <PenTool size={11} style={{ marginRight: 2 }} />
              Draw
            </label>
          </div>

          {inputMode === "bbox" ? (
            <>
              <div className="grid-2">
                <div>
                  <label className="label">Min Lon</label>
                  <input type="number" step="0.0001" value={bbox.minLon} onChange={(e) => setBBox((b) => ({ ...b, minLon: +e.target.value }))} className="input" />
                </div>
                <div>
                  <label className="label">Max Lon</label>
                  <input type="number" step="0.0001" value={bbox.maxLon} onChange={(e) => setBBox((b) => ({ ...b, maxLon: +e.target.value }))} className="input" />
                </div>
                <div>
                  <label className="label">Min Lat</label>
                  <input type="number" step="0.0001" value={bbox.minLat} onChange={(e) => setBBox((b) => ({ ...b, minLat: +e.target.value }))} className="input" />
                </div>
                <div>
                  <label className="label">Max Lat</label>
                  <input type="number" step="0.0001" value={bbox.maxLat} onChange={(e) => setBBox((b) => ({ ...b, maxLat: +e.target.value }))} className="input" />
                </div>
              </div>
              <button type="button" className="btn btn-primary btn-full" onClick={() => onSetBBox(bbox)}>
                INITIALIZE AOI
              </button>
            </>
          ) : inputMode === "geojson" ? (
            <label className="file-upload-area">
              <Upload size={20} />
              <span>Drop GeoJSON or click to browse</span>
              <input type="file" accept=".geojson,.json" onChange={handleFileUpload} hidden />
            </label>
          ) : (
            <div className="draw-map-container">
              <DrawableMap
                onBBoxCreated={(drawnBBox) => {
                  setBBox(drawnBBox);
                  onSetBBox(drawnBBox);
                }}
                existingGeojson={existingGeojson}
              />
              <p className="draw-hint">
                Click two points on the map to define the AOI rectangle.
              </p>
            </div>
          )}
        </div>
      )}

      <hr className="sidebar-hr" />

      {/* AHP-MCDM Weights */}
      <SectionHeader title="AHP-MCDM Weights" icon={<Sliders size={14} />} open={expandedSections.mca} onToggle={() => toggle("mca")} />
      {expandedSections.mca && (
        <div className="sidebar-section">
          <div className="radio-group">
            <label>
              <input type="radio" checked={params.mca_method === "ahp"} onChange={() => onParamsChange({ mca_method: "ahp" })} />
              AHP (Saaty)
            </label>
            <label>
              <input type="radio" checked={params.mca_method === "custom"} onChange={() => onParamsChange({ mca_method: "custom" })} />
              Custom Weights
            </label>
          </div>

          {params.mca_method === "ahp" ? (
            <div className="weight-summary" style={{ fontSize: "11px", opacity: 0.8, lineHeight: 1.6 }}>
              11-factor AHP with Saaty pairwise matrix.
              <br />Weights & CR computed automatically.
            </div>
          ) : (
            <div className="custom-weights-grid">
              {FACTOR_NAMES.map((name) => (
                <div key={name} className="weight-row">
                  <label className="label" style={{ fontSize: "11px" }}>
                    {FACTOR_LABELS[name]} {Math.round((params.custom_weights[name] || 0) * 100)}%
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={50}
                    step={1}
                    value={Math.round((params.custom_weights[name] || 0) * 100)}
                    onChange={(e) => {
                      const updated = { ...params.custom_weights, [name]: +e.target.value / 100 };
                      onParamsChange({ custom_weights: updated });
                    }}
                  />
                </div>
              ))}
              <div className="weight-summary" style={{ color: Math.abs(customTotal - 1) > 0.01 ? "#fc8d59" : "#91cf60" }}>
                Total: {(customTotal * 100).toFixed(0)}%
                {Math.abs(customTotal - 1) > 0.01 && " (must sum to 100%)"}
              </div>
            </div>
          )}
        </div>
      )}

      <hr className="sidebar-hr" />

      {/* SAR Windows */}
      <SectionHeader title="SAR Engine" icon={<Satellite size={14} />} open={expandedSections.sar} onToggle={() => toggle("sar")} />
      {expandedSections.sar && (
        <div className="sidebar-section">
          <div className="grid-2">
            <div>
              <label className="label">Pre Start</label>
              <input type="date" value={params.p_start} onChange={(e) => onParamsChange({ p_start: e.target.value })} className="input" />
            </div>
            <div>
              <label className="label">Pre End</label>
              <input type="date" value={params.p_end} onChange={(e) => onParamsChange({ p_end: e.target.value })} className="input" />
            </div>
            <div>
              <label className="label">Post Start</label>
              <input type="date" value={params.f_start} onChange={(e) => onParamsChange({ f_start: e.target.value })} className="input" />
            </div>
            <div>
              <label className="label">Post End</label>
              <input type="date" value={params.f_end} onChange={(e) => onParamsChange({ f_end: e.target.value })} className="input" />
            </div>
          </div>

          <div className="radio-group">
            <label><input type="radio" checked={params.polarization === "VH"} onChange={() => onParamsChange({ polarization: "VH" })} /> VH</label>
            <label><input type="radio" checked={params.polarization === "VV"} onChange={() => onParamsChange({ polarization: "VV" })} /> VV</label>
          </div>

          <label className="label">Threshold: {params.threshold} dB</label>
          <input type="range" min={0.5} max={6} step={0.25} value={params.threshold} onChange={(e) => onParamsChange({ threshold: +e.target.value })} />

          <label className="checkbox-label">
            <input type="checkbox" checked={params.speckle} onChange={(e) => onParamsChange({ speckle: e.target.checked })} />
            Speckle Filter (Lee 3x3)
          </label>
        </div>
      )}

      <hr className="sidebar-hr" />

      {/* Imagery */}
      <SectionHeader title="Imagery Date Range" icon={<Satellite size={14} />} open={expandedSections.imagery} onToggle={() => toggle("imagery")} />
      {expandedSections.imagery && (
        <div className="sidebar-section">
          <div className="grid-2">
            <div>
              <label className="label">Start</label>
              <input type="date" value={params.img_start} onChange={(e) => onParamsChange({ img_start: e.target.value })} className="input" />
            </div>
            <div>
              <label className="label">End</label>
              <input type="date" value={params.img_end} onChange={(e) => onParamsChange({ img_end: e.target.value })} className="input" />
            </div>
          </div>
          <label className="label">Max Cloud Cover: {params.cloud_thresh}%</label>
          <input type="range" min={10} max={100} step={5} value={params.cloud_thresh} onChange={(e) => onParamsChange({ cloud_thresh: +e.target.value })} />
        </div>
      )}

      {/* Keyboard shortcuts hint */}
      <div className="sidebar-footer">
        <span className="kbd-hint">Press <kbd>1</kbd>-<kbd>7</kbd> to switch tabs</span>
      </div>
    </aside>
  );
}

function SectionHeader({ title, icon, open, onToggle }: { title: string; icon: React.ReactNode; open: boolean; onToggle: () => void }) {
  return (
    <button className="section-header" onClick={onToggle}>
      {icon}
      <span>{title}</span>
      {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
    </button>
  );
}
