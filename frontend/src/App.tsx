import { useState, useCallback, useEffect, lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/layout/Header";
import { Sidebar, DEFAULT_PARAMS, type SidebarParams } from "./components/layout/Sidebar";
import { TabBar } from "./components/layout/TabBar";
import { useAOI } from "./hooks/useAOI";
import { LoadingOverlay } from "./components/common/LoadingOverlay";
import { ToastContainer, toast } from "./components/common/Toast";
import { geocode } from "./api/endpoints";
import { Droplets, MapPin } from "lucide-react";
import "./index.css";

const RiskTab = lazy(() => import("./pages/RiskTab").then((m) => ({ default: m.RiskTab })));
const SARTab = lazy(() => import("./pages/SARTab").then((m) => ({ default: m.SARTab })));
const MLTab = lazy(() => import("./pages/MLTab").then((m) => ({ default: m.MLTab })));
const ClimateTab = lazy(() => import("./pages/ClimateTab").then((m) => ({ default: m.ClimateTab })));
const IndicesTab = lazy(() => import("./pages/IndicesTab").then((m) => ({ default: m.IndicesTab })));
const HydrologyTab = lazy(() => import("./pages/HydrologyTab").then((m) => ({ default: m.HydrologyTab })));
const ForecastTab = lazy(() => import("./pages/ForecastTab").then((m) => ({ default: m.ForecastTab })));

const TAB_IDS = ["risk", "sar", "ml", "climate", "indices", "hydrology", "forecast"];

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5 * 60_000 },
  },
});

function AppInner() {
  const { aoi, setFromBBox, setFromGeoJSON, clear, isActive } = useAOI();
  const [activeTab, setActiveTab] = useState("risk");
  const [params, setParams] = useState<SidebarParams>(DEFAULT_PARAMS);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleParamsChange = useCallback(
    (patch: Partial<SidebarParams>) => setParams((p) => ({ ...p, ...patch })),
    []
  );

  const handleSearch = useCallback(
    async (query: string) => {
      try {
        toast("info", `Searching "${query}"...`);
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
        toast("success", `AOI set: ${result.display_name.split(",").slice(0, 2).join(",")}`);
      } catch (err: any) {
        toast("error", `Search failed: ${err.message}`);
      }
    },
    [setFromBBox]
  );

  // Keyboard shortcuts: 1-7 for tabs, Esc to toggle sidebar
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      const num = parseInt(e.key);
      if (num >= 1 && num <= 7) {
        setActiveTab(TAB_IDS[num - 1]);
      } else if (e.key === "Escape") {
        setSidebarCollapsed((c) => !c);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

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
        onSetBBox={(bbox) => {
          setFromBBox(bbox);
          toast("success", "AOI initialized from bounding box");
        }}
        onFileUpload={(geom) => {
          setFromGeoJSON(geom);
          toast("success", "AOI loaded from GeoJSON");
        }}
        isAOIActive={isActive}
        aoiName={aoi.name}
        params={params}
        onParamsChange={handleParamsChange}
        onClearAOI={() => {
          clear();
          toast("info", "AOI cleared");
        }}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
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
            <Droplets size={40} color="var(--accent)" strokeWidth={1.5} />
            <div className="empty-title">Begin Analysis</div>
            <div className="empty-text">Search a location or draw an AOI to start</div>
            <div className="quick-start-grid">
              <button className="quick-start-card" onClick={() => handleSearch("Patna, Bihar")}>
                <MapPin size={16} />
                <div>
                  <strong>Patna, Bihar</strong>
                  <span>Flood-prone Gangetic plain</span>
                </div>
              </button>
              <button className="quick-start-card" onClick={() => handleSearch("Guwahati, Assam")}>
                <MapPin size={16} />
                <div>
                  <strong>Guwahati, Assam</strong>
                  <span>Brahmaputra basin floods</span>
                </div>
              </button>
              <button className="quick-start-card" onClick={() => handleSearch("Kochi, Kerala")}>
                <MapPin size={16} />
                <div>
                  <strong>Kochi, Kerala</strong>
                  <span>Monsoon & coastal flooding</span>
                </div>
              </button>
            </div>
            <div className="empty-footer">Powered by WeatherEx</div>
          </div>
        )}
      </main>
      <ToastContainer />
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
