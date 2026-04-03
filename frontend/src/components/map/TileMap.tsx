import { MapContainer, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";
import { MapLegend } from "./MapLegend";
import type { LegendConfig } from "../../config/legends";

interface TileMapProps {
  center: [number, number];
  zoom?: number;
  tileUrl?: string | null;
  tileName?: string;
  height?: string;
  legend?: LegendConfig;
}

function OverlayLayer({ url, name }: { url: string; name: string }) {
  const map = useMap();
  useEffect(() => {
    if (!url) return;
    try {
      const layer = (window as any).L.tileLayer(url, {
        attribution: name,
        opacity: 0.8,
        maxZoom: 18,
      });
      layer.addTo(map);
      return () => {
        map.removeLayer(layer);
      };
    } catch (e) {
      console.error("[TileMap] Failed to add overlay layer:", e);
    }
  }, [url, name, map]);
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
  return (
    <div style={{ height, width: "100%" }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%", borderRadius: 12 }}
        scrollWheelZoom
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <MapUpdater center={center} zoom={zoom} />
        {tileUrl && <OverlayLayer url={tileUrl} name={tileName} />}
        {legend && <MapLegend config={legend} />}
      </MapContainer>
    </div>
  );
}
