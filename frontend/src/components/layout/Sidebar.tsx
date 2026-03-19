import { useState, type FormEvent } from "react";
import { Search, MapPin, Sliders, Satellite, ChevronDown, ChevronUp } from "lucide-react";
import type { BBox } from "../../hooks/useAOI";

interface SidebarProps {
  onSearchPlace: (query: string) => void;
  onSetBBox: (bbox: BBox) => void;
  onFileUpload: (geojson: GeoJSON.Geometry) => void;
  isAOIActive: boolean;
  params: SidebarParams;
  onParamsChange: (params: Partial<SidebarParams>) => void;
}

export interface SidebarParams {
  // MCA weights
  w_lulc: number;
  w_slope: number;
  // SAR
  p_start: string;
  p_end: string;
  f_start: string;
  f_end: string;
  polarization: "VH" | "VV";
  threshold: number;
  speckle: boolean;
  // Imagery
  img_start: string;
  img_end: string;
  cloud_thresh: number;
  // Crop
  crop_type: string;
  crop_price: number;
  // Progression
  prog_year: number;
}

export const DEFAULT_PARAMS: SidebarParams = {
  w_lulc: 40,
  w_slope: 30,
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

export function Sidebar({
  onSearchPlace,
  onSetBBox,
  onFileUpload,
  isAOIActive,
  params,
  onParamsChange,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [inputMode, setInputMode] = useState<"bbox" | "geojson">("bbox");
  const [bbox, setBBox] = useState<BBox>({ minLon: 84.9, minLat: 25.5, maxLon: 85.3, maxLat: 25.8 });
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    location: true,
    aoi: true,
    mca: false,
    sar: false,
    imagery: false,
  });

  const w_rain = Math.max(0, 100 - params.w_lulc - params.w_slope);

  const toggle = (section: string) =>
    setExpandedSections((s) => ({ ...s, [section]: !s[section] }));

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) onSearchPlace(searchQuery.trim());
  };

  const handleInitBBox = () => onSetBBox(bbox);

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

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <img
          src="https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png"
          alt="IIT KGP"
          width={48}
        />
        <div className="brand-title">HYDRORISK</div>
        <div className="brand-sub">IIT Kharagpur &middot; GEE</div>
      </div>

      {/* Location Search */}
      <SectionHeader title="Location Search" icon={<Search size={14} />} open={expandedSections.location} onToggle={() => toggle("location")} />
      {expandedSections.location && (
        <form onSubmit={handleSearch} className="sidebar-section">
          <input
            type="text"
            placeholder="e.g. Patna, Bihar"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input"
          />
          <button type="submit" className="btn btn-primary btn-full">
            SEARCH &amp; SET AOI
          </button>
        </form>
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
              Upload GeoJSON
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
              <button type="button" className="btn btn-primary btn-full" onClick={handleInitBBox}>
                INITIALIZE AOI
              </button>
            </>
          ) : (
            <input type="file" accept=".geojson,.json" onChange={handleFileUpload} className="input" />
          )}

          {isAOIActive && (
            <div className="status-pill">
              <span className="status-dot" /> AOI ACTIVE
            </div>
          )}
        </div>
      )}

      <hr className="sidebar-hr" />

      {/* MCA Weights */}
      <SectionHeader title="MCA Weights" icon={<Sliders size={14} />} open={expandedSections.mca} onToggle={() => toggle("mca")} />
      {expandedSections.mca && (
        <div className="sidebar-section">
          <label className="label">LULC {params.w_lulc}%</label>
          <input type="range" min={10} max={80} step={5} value={params.w_lulc} onChange={(e) => onParamsChange({ w_lulc: +e.target.value })} />
          <label className="label">Slope {params.w_slope}%</label>
          <input type="range" min={10} max={80} step={5} value={params.w_slope} onChange={(e) => onParamsChange({ w_slope: +e.target.value })} />
          <div className="weight-summary">Rainfall: {w_rain}%</div>
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
