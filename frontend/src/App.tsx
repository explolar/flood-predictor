import { useState, useCallback } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Header } from "./components/layout/Header";
import { Sidebar, DEFAULT_PARAMS, type SidebarParams } from "./components/layout/Sidebar";
import { TabBar } from "./components/layout/TabBar";
import { useAOI } from "./hooks/useAOI";
import { RiskTab } from "./pages/RiskTab";
import { SARTab } from "./pages/SARTab";
import { MLTab } from "./pages/MLTab";
import { ClimateTab } from "./pages/ClimateTab";
import { IndicesTab } from "./pages/IndicesTab";
import { HydrologyTab } from "./pages/HydrologyTab";
import { ForecastTab } from "./pages/ForecastTab";
import { geocode } from "./api/endpoints";
import "./index.css";

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
            {activeTab === "risk" && <RiskTab {...tabProps} />}
            {activeTab === "sar" && <SARTab {...tabProps} />}
            {activeTab === "ml" && <MLTab {...tabProps} />}
            {activeTab === "climate" && <ClimateTab {...tabProps} />}
            {activeTab === "indices" && <IndicesTab {...tabProps} />}
            {activeTab === "hydrology" && <HydrologyTab {...tabProps} />}
            {activeTab === "forecast" && <ForecastTab {...tabProps} />}
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
