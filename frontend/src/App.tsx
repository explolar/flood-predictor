import { useState, useCallback, useEffect, lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/layout/Header";
import { Sidebar, DEFAULT_PARAMS, type SidebarParams } from "./components/layout/Sidebar";
import { TabBar } from "./components/layout/TabBar";
import { useAOI } from "./hooks/useAOI";
import { LoadingOverlay } from "./components/common/LoadingOverlay";
import { geocode } from "./api/endpoints";
import "./index.css";

// Lazy load all tab pages — each gets its own chunk
const RiskTab = lazy(() => import("./pages/RiskTab").then((m) => ({ default: m.RiskTab })));
const SARTab = lazy(() => import("./pages/SARTab").then((m) => ({ default: m.SARTab })));
const MLTab = lazy(() => import("./pages/MLTab").then((m) => ({ default: m.MLTab })));
const ClimateTab = lazy(() => import("./pages/ClimateTab").then((m) => ({ default: m.ClimateTab })));
const IndicesTab = lazy(() => import("./pages/IndicesTab").then((m) => ({ default: m.IndicesTab })));
const HydrologyTab = lazy(() => import("./pages/HydrologyTab").then((m) => ({ default: m.HydrologyTab })));
const ForecastTab = lazy(() => import("./pages/ForecastTab").then((m) => ({ default: m.ForecastTab })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5 * 60_000 },
  },
});

function AppInner() {
  const { aoi, setFromBBox, setFromGeoJSON, isActive } = useAOI();
  const [activeTab, setActiveTab] = useState("risk");
  const [params, setParams] = useState<SidebarParams>(DEFAULT_PARAMS);

  const handleParamsChange = useCallback(
    (patch: Partial<SidebarParams>) => setParams((p) => ({ ...p, ...patch })),
    []
  );

  const handleSearch = useCallback(
    async (query: string) => {
      try {
        const result = await geocode(query);
        const d = 0.25;
        setFromBBox(
          {
            minLon: result.lon - d,
            minLat: result.lat - d,
            maxLon: result.lon + d,
            maxLat: result.lat + d,
          },
          result.display_name
        );
      } catch (err: any) {
        alert(`Search failed: ${err.message}`);
      }
    },
    [setFromBBox]
  );

  // Prefetch all tab chunks in parallel once AOI is set
  useEffect(() => {
    if (isActive) {
      Promise.all([
        import("./pages/RiskTab"),
        import("./pages/SARTab"),
        import("./pages/MLTab"),
        import("./pages/ClimateTab"),
        import("./pages/IndicesTab"),
        import("./pages/HydrologyTab"),
        import("./pages/ForecastTab"),
      ]);
    }
  }, [isActive]);

  const tabProps = {
    geojson: aoi.geojson!,
    center: aoi.center,
    params,
  };

  return (
    <div className="app-layout">
      <Sidebar
        onSearchPlace={handleSearch}
        onSetBBox={setFromBBox}
        onFileUpload={(geom) => setFromGeoJSON(geom)}
        isAOIActive={isActive}
        params={params}
        onParamsChange={handleParamsChange}
      />
      <main className="main-content">
        <Header />
        <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

        {isActive ? (
          <div className="tab-panel">
            <Suspense fallback={<LoadingOverlay message="Loading module..." />}>
              {activeTab === "risk" && <RiskTab {...tabProps} />}
              {activeTab === "sar" && <SARTab {...tabProps} />}
              {activeTab === "ml" && <MLTab {...tabProps} />}
              {activeTab === "climate" && <ClimateTab {...tabProps} />}
              {activeTab === "indices" && <IndicesTab {...tabProps} />}
              {activeTab === "hydrology" && <HydrologyTab {...tabProps} />}
              {activeTab === "forecast" && <ForecastTab {...tabProps} />}
            </Suspense>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">&#128752;</div>
            <div className="empty-title">NO STUDY AREA DEFINED</div>
            <div className="empty-text">
              Use the sidebar to search a location or define a bounding box, then click <strong>INITIALIZE AOI</strong>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}
