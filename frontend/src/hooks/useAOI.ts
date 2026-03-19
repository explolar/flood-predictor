import { useState, useCallback } from "react";

export interface BBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export interface AOIState {
  geojson: GeoJSON.Geometry | null;
  center: [number, number];
  bbox: BBox | null;
  name: string;
}

const DEFAULT_CENTER: [number, number] = [25.61, 85.12];

export function useAOI() {
  const [aoi, setAOI] = useState<AOIState>({
    geojson: null,
    center: DEFAULT_CENTER,
    bbox: null,
    name: "",
  });

  const setFromBBox = useCallback((bbox: BBox, name?: string) => {
    const geojson: GeoJSON.Geometry = {
      type: "Polygon",
      coordinates: [
        [
          [bbox.minLon, bbox.minLat],
          [bbox.maxLon, bbox.minLat],
          [bbox.maxLon, bbox.maxLat],
          [bbox.minLon, bbox.maxLat],
          [bbox.minLon, bbox.minLat],
        ],
      ],
    };
    setAOI({
      geojson,
      center: [(bbox.minLat + bbox.maxLat) / 2, (bbox.minLon + bbox.maxLon) / 2],
      bbox,
      name: name || "",
    });
  }, []);

  const setFromGeoJSON = useCallback((geojson: GeoJSON.Geometry, name?: string) => {
    // Simple centroid from first coordinate
    const coords =
      geojson.type === "Polygon"
        ? geojson.coordinates[0]
        : geojson.type === "MultiPolygon"
          ? geojson.coordinates[0][0]
          : [];
    const center: [number, number] = coords.length
      ? [
          coords.reduce((s: number, c: number[]) => s + c[1], 0) / coords.length,
          coords.reduce((s: number, c: number[]) => s + c[0], 0) / coords.length,
        ]
      : DEFAULT_CENTER;

    setAOI({ geojson, center, bbox: null, name: name || "" });
  }, []);

  const clear = useCallback(() => {
    setAOI({ geojson: null, center: DEFAULT_CENTER, bbox: null, name: "" });
  }, []);

  return { aoi, setFromBBox, setFromGeoJSON, clear, isActive: !!aoi.geojson };
}
