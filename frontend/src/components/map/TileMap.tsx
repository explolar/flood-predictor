import { MapContainer, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";

interface TileMapProps {
  center: [number, number];
  zoom?: number;
  tileUrl?: string | null;
  tileName?: string;
  height?: string;
}

function OverlayLayer({ url, name }: { url: string; name: string }) {
  const map = useMap();
  useEffect(() => {
    const layer = (window as any).L.tileLayer(url, {
      attribution: name,
      opacity: 0.8,
      maxZoom: 18,
    });
    layer.addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [url, name, map]);
  return null;
}

function MapUpdater({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, map.getZoom(), { duration: 1.0 });
  }, [center, map]);
  return null;
}

export function TileMap({
  center,
  zoom = 10,
  tileUrl,
  tileName = "Analysis",
  height = "480px",
}: TileMapProps) {
  return (
    <div style={{ height, width: "100%" }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%", borderRadius: 16 }}
        scrollWheelZoom
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <MapUpdater center={center} />
        {tileUrl && <OverlayLayer url={tileUrl} name={tileName} />}
      </MapContainer>
    </div>
  );
}
