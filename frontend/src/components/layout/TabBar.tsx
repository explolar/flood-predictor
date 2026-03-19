import { Shield, Radar, Brain, Cloud, Layers, Droplets, CloudRain } from "lucide-react";

interface Tab {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut: string;
  desc: string;
}

const TABS: Tab[] = [
  { id: "risk", label: "RISK", icon: <Shield size={13} />, shortcut: "1", desc: "Multi-criteria flood risk" },
  { id: "sar", label: "SAR", icon: <Radar size={13} />, shortcut: "2", desc: "Sentinel-1 flood detection" },
  { id: "ml", label: "ML", icon: <Brain size={13} />, shortcut: "3", desc: "ML classification models" },
  { id: "climate", label: "CLIMATE", icon: <Cloud size={13} />, shortcut: "4", desc: "Multi-year & drought" },
  { id: "indices", label: "INDICES", icon: <Layers size={13} />, shortcut: "5", desc: "Spectral indices" },
  { id: "hydrology", label: "HYDRO", icon: <Droplets size={13} />, shortcut: "6", desc: "Watershed analysis" },
  { id: "forecast", label: "FORECAST", icon: <CloudRain size={13} />, shortcut: "7", desc: "Weather forecast" },
];

interface TabBarProps {
  activeTab: string;
  onTabChange: (id: string) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <nav className="tab-bar">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-item ${activeTab === tab.id ? "tab-active" : ""}`}
          onClick={() => onTabChange(tab.id)}
          title={`${tab.desc} (${tab.shortcut})`}
        >
          {tab.icon}
          <span className="tab-label">{tab.label}</span>
          <kbd className="tab-kbd">{tab.shortcut}</kbd>
        </button>
      ))}
    </nav>
  );
}
