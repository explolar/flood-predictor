import { useEffect, useState } from "react";
import { useMap } from "react-leaflet";
import { createPortal } from "react-dom";
import type { LegendConfig } from "../../config/legends";

/**
 * MapLegend renders a Leaflet-aware legend inside the map container.
 * It creates a custom Leaflet control (bottom-right) and portals React
 * content into it so the legend lives within the map's z-index stack.
 */
export function MapLegend({ config }: { config: LegendConfig }) {
  const map = useMap();
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  /* Create a Leaflet control once, tear it down on unmount */
  useEffect(() => {
    const L = (window as unknown as { L: typeof import("leaflet") }).L;

    const LegendControl = L.Control.extend({
      onAdd() {
        const div = L.DomUtil.create("div", "map-legend");
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        setContainer(div);
        return div;
      },
      onRemove() {
        setContainer(null);
      },
    });

    const ctrl = new LegendControl({ position: "bottomright" });
    ctrl.addTo(map);

    return () => {
      ctrl.remove();
    };
  }, [map]);

  /* Build gradient CSS from palette */
  const gradientCSS =
    config.type === "continuous"
      ? config.palette
          .map(
            (hex, i) =>
              `#${hex} ${((i / (config.palette.length - 1)) * 100).toFixed(1)}%`
          )
          .join(", ")
      : "";

  const formatNum = (v: number): string => {
    if (Number.isInteger(v)) return String(v);
    return v.toFixed(2).replace(/\.?0+$/, "");
  };

  /* Render through portal into the Leaflet control div */
  if (!container) return null;

  return createPortal(
    <>
      <div className="map-legend__title">{config.title}</div>

      {config.type === "continuous" && (
        <div className="map-legend__continuous">
          <div
            className="map-legend__gradient"
            style={{
              background: `linear-gradient(to right, ${gradientCSS})`,
            }}
          />
          <div className="map-legend__range">
            <span>
              {formatNum(config.min ?? 0)}
              {config.unit ? config.unit : ""}
            </span>
            <span>
              {formatNum(config.max ?? 1)}
              {config.unit ? config.unit : ""}
            </span>
          </div>
        </div>
      )}

      {config.type === "discrete" && (
        <div className="map-legend__discrete">
          {config.palette.map((hex, i) => (
            <div className="map-legend__swatch" key={hex + String(i)}>
              <span
                className="map-legend__color"
                style={{ background: `#${hex}` }}
              />
              <span className="map-legend__label">
                {config.labels?.[i] ?? `Class ${i + 1}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </>,
    container
  );
}
