import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { BBox } from "../../hooks/useAOI";

/* ── Types ── */
interface DrawableMapProps {
  /** Called when user finishes drawing a rectangle (two clicks). */
  onBBoxCreated: (bbox: BBox) => void;
  /** If provided, render this geometry as a read-only overlay. */
  existingGeojson?: GeoJSON.Geometry | null;
  /** Map center. Defaults to central India. */
  center?: [number, number];
  /** Map height. Defaults to 350px. */
  height?: string;
}

type Corner = L.LatLng | null;
type Phase = "idle" | "first" | "second";

/* ── Crosshair cursor style injected once ── */
const CROSSHAIR_CLASS = "drawable-map-crosshair";

/* ── DrawInteraction: handles click-to-draw-rectangle logic ── */
function DrawInteraction({
  onBBoxCreated,
  existingGeojson,
}: {
  onBBoxCreated: (bbox: BBox) => void;
  existingGeojson?: GeoJSON.Geometry | null;
}) {
  const map = useMap();
  const [phase, setPhase] = useState<Phase>("idle");
  const firstCorner = useRef<Corner>(null);
  const previewRect = useRef<L.Rectangle | null>(null);
  const finalRect = useRef<L.Rectangle | null>(null);
  const existingLayer = useRef<L.GeoJSON | null>(null);
  const instructionControl = useRef<L.Control | null>(null);

  /* -- Cleanup helpers -- */
  const clearPreview = useCallback(() => {
    if (previewRect.current) {
      map.removeLayer(previewRect.current);
      previewRect.current = null;
    }
  }, [map]);

  const clearFinal = useCallback(() => {
    if (finalRect.current) {
      map.removeLayer(finalRect.current);
      finalRect.current = null;
    }
  }, [map]);

  const clearExistingLayer = useCallback(() => {
    if (existingLayer.current) {
      map.removeLayer(existingLayer.current);
      existingLayer.current = null;
    }
  }, [map]);

  /* -- Show existing AOI geometry -- */
  useEffect(() => {
    clearExistingLayer();
    if (!existingGeojson) return;
    try {
      const layer = L.geoJSON(existingGeojson as GeoJSON.GeoJsonObject, {
        style: {
          color: "#0891b2",
          weight: 2,
          fillColor: "#0891b2",
          fillOpacity: 0.10,
          dashArray: "6 3",
        },
      });
      layer.addTo(map);
      existingLayer.current = layer;
      map.fitBounds(layer.getBounds(), { padding: [30, 30] });
    } catch (e) {
      console.error("[DrawableMap] Failed to render existing geometry:", e);
    }
    return () => {
      clearExistingLayer();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existingGeojson, map]);

  /* -- Instruction overlay control -- */
  useEffect(() => {
    const InstructionControl = L.Control.extend({
      onAdd() {
        const div = L.DomUtil.create("div", "drawable-map-instructions");
        div.id = "draw-instructions";
        div.innerHTML = "Click to set first corner";
        return div;
      },
    });
    const ctrl = new InstructionControl({ position: "topright" });
    ctrl.addTo(map);
    instructionControl.current = ctrl;
    return () => {
      map.removeControl(ctrl);
    };
  }, [map]);

  /* -- Update instruction text -- */
  const setInstruction = useCallback((text: string) => {
    const el = document.getElementById("draw-instructions");
    if (el) el.textContent = text;
  }, []);

  /* -- Start drawing mode -- */
  const startDrawing = useCallback(() => {
    clearPreview();
    clearFinal();
    firstCorner.current = null;
    setPhase("first");
    setInstruction("Click to set first corner");
    map.getContainer().classList.add(CROSSHAIR_CLASS);
  }, [clearPreview, clearFinal, setInstruction, map]);

  /* -- Initialize: auto-start drawing if no existing geometry -- */
  useEffect(() => {
    if (!existingGeojson) {
      startDrawing();
    } else {
      setPhase("idle");
      setInstruction("AOI set. Click Reset to redraw.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* -- Rectangle style -- */
  const rectStyle: L.PathOptions = {
    color: "#0891b2",
    weight: 2,
    fillColor: "#06b6d4",
    fillOpacity: 0.15,
  };

  const previewStyle: L.PathOptions = {
    color: "#0891b2",
    weight: 1,
    fillColor: "#06b6d4",
    fillOpacity: 0.08,
    dashArray: "4 4",
  };

  /* -- Map events -- */
  useMapEvents({
    click(e) {
      if (phase === "first") {
        /* First click: set first corner */
        firstCorner.current = e.latlng;
        setPhase("second");
        setInstruction("Click to set opposite corner");
      } else if (phase === "second" && firstCorner.current) {
        /* Second click: finalize rectangle */
        clearPreview();
        const bounds = L.latLngBounds(firstCorner.current, e.latlng);
        const rect = L.rectangle(bounds, rectStyle);
        rect.addTo(map);
        clearFinal();
        finalRect.current = rect;

        /* Compute BBox */
        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        const bbox: BBox = {
          minLon: Math.round(sw.lng * 10000) / 10000,
          minLat: Math.round(sw.lat * 10000) / 10000,
          maxLon: Math.round(ne.lng * 10000) / 10000,
          maxLat: Math.round(ne.lat * 10000) / 10000,
        };

        setPhase("idle");
        setInstruction("AOI set. Click Reset to redraw.");
        map.getContainer().classList.remove(CROSSHAIR_CLASS);
        firstCorner.current = null;

        onBBoxCreated(bbox);
      }
    },
    mousemove(e) {
      if (phase === "second" && firstCorner.current) {
        clearPreview();
        const bounds = L.latLngBounds(firstCorner.current, e.latlng);
        previewRect.current = L.rectangle(bounds, previewStyle);
        previewRect.current.addTo(map);
      }
    },
  });

  /* -- Expose reset via a custom control button -- */
  useEffect(() => {
    const ResetControl = L.Control.extend({
      onAdd() {
        const btn = L.DomUtil.create("button", "drawable-map-reset-btn");
        btn.textContent = "Reset";
        btn.title = "Clear and redraw AOI";
        btn.type = "button";
        L.DomEvent.disableClickPropagation(btn);
        btn.addEventListener("click", () => {
          clearFinal();
          clearPreview();
          clearExistingLayer();
          startDrawing();
        });
        return btn;
      },
    });
    const ctrl = new ResetControl({ position: "topleft" });
    ctrl.addTo(map);
    return () => {
      map.removeControl(ctrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  return null;
}

/* ── DrawableMap: the top-level map component ── */
export function DrawableMap({
  onBBoxCreated,
  existingGeojson,
  center = [22.5, 82.5],
  height = "350px",
}: DrawableMapProps) {
  return (
    <div className="drawable-map-wrapper" style={{ height, width: "100%" }}>
      <MapContainer
        center={center}
        zoom={5}
        style={{ height: "100%", width: "100%", borderRadius: 10 }}
        scrollWheelZoom
        zoomControl
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <DrawInteraction
          onBBoxCreated={onBBoxCreated}
          existingGeojson={existingGeojson}
        />
      </MapContainer>
    </div>
  );
}
