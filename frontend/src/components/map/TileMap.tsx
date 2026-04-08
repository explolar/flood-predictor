import { MapContainer, TileLayer, useMap } from "react-leaflet";
import { useEffect, useRef, useState, useCallback } from "react";
import "leaflet/dist/leaflet.css";
import { MapLegend } from "./MapLegend";
import { Maximize2, Minimize2, Layers } from "lucide-react";
import type { LegendConfig } from "../../config/legends";

interface TileMapProps {
  center: [number, number];
  zoom?: number;
  tileUrl?: string | null;
  tileName?: string;
  height?: string;
  legend?: LegendConfig;
}

function OverlayLayer({ url, name, opacity }: { url: string; name: string; opacity: number }) {
  const map = useMap();
  const layerRef = useRef<any>(null);

  useEffect(() => {
    if (!url) return;
    try {
      const layer = (window as any).L.tileLayer(url, {
        attribution: name,
        opacity,
        maxZoom: 18,
      });
      layer.addTo(map);
      layerRef.current = layer;
      return () => {
        map.removeLayer(layer);
      };
    } catch (e) {
      console.error("[TileMap] Failed to add overlay layer:", e);
    }
  }, [url, name, map]);

  // Update opacity without re-adding layer
  useEffect(() => {
    if (layerRef.current) {
      layerRef.current.setOpacity(opacity);
    }
  }, [opacity]);

  return null;
}

function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    // Fix tiles after container becomes visible (e.g. tab switch)
    requestAnimationFrame(() => map.invalidateSize());
    map.flyTo(center, map.getZoom() || zoom, { duration: 1.0 });
  }, [center, zoom, map]);
  return null;
}

export function TileMap({
  center,
  zoom = 10,
  tileUrl,
  tileName = "Analysis",
  height = "480px",
  legend,
}: TileMapProps) {
  const [opacity, setOpacity] = useState(0.8);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOpacity, setShowOpacity] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((f) => !f);
  }, []);

  // Escape key exits fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isFullscreen]);

  return (
    <div
      ref={containerRef}
      className={isFullscreen ? "map-container-fullscreen" : undefined}
      style={isFullscreen ? undefined : { height, width: "100%", position: "relative" }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%", borderRadius: isFullscreen ? 0 : 12 }}
        scrollWheelZoom
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <MapUpdater center={center} zoom={zoom} />
        {tileUrl && <OverlayLayer url={tileUrl} name={tileName} opacity={opacity} />}
        {legend && <MapLegend config={legend} />}
      </MapContainer>

      {/* Map tools overlay */}
      <div className="map-tools">
        <button
          className="map-tool-btn"
          onClick={toggleFullscreen}
          title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>

        {tileUrl && (
          <button
            className="map-tool-btn"
            onClick={() => setShowOpacity((s) => !s)}
            title="Layer opacity"
          >
            <Layers size={14} />
          </button>
        )}

        {showOpacity && tileUrl && (
          <div className="map-opacity-control">
            <label>Opacity {Math.round(opacity * 100)}%</label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(opacity * 100)}
              onChange={(e) => setOpacity(+e.target.value / 100)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/** Hover tooltip for scientific vocabulary */
export function InfoTooltip({ label, tip }: { label: string; tip: string }) {
  return (
    <span className="info-tooltip">
      {label}
      <span className="info-tooltip-text">{tip}</span>
    </span>
  );
}
