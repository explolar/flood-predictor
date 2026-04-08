import { Shield, Radar, Brain, Cloud, Layers, CloudRain, Droplets, AlertTriangle } from "lucide-react";

interface Tab {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut: string;
  desc: string;
}

const TABS: Tab[] = [
  { id: "risk", label: "Risk", icon: <Shield size={14} />, shortcut: "1", desc: "Multi-criteria flood risk" },
  { id: "sar", label: "SAR", icon: <Radar size={14} />, shortcut: "2", desc: "Sentinel-1 flood detection" },
  { id: "ml", label: "ML", icon: <Brain size={14} />, shortcut: "3", desc: "ML classification models" },
  { id: "climate", label: "Climate", icon: <Cloud size={14} />, shortcut: "4", desc: "Multi-year & drought" },
  { id: "indices", label: "Indices", icon: <Layers size={14} />, shortcut: "5", desc: "Spectral indices" },
  { id: "forecast", label: "Forecast", icon: <CloudRain size={14} />, shortcut: "6", desc: "Weather forecast" },
  { id: "hydrology", label: "Hydrology", icon: <Droplets size={14} />, shortcut: "7", desc: "Watershed & stream analysis" },
  { id: "impact", label: "Impact", icon: <AlertTriangle size={14} />, shortcut: "8", desc: "Who & what is affected" },
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
        </button>
      ))}
    </nav>
  );
}
