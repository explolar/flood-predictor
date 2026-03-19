import { Shield, Radar, Brain, Cloud, Layers, Droplets, CloudRain } from "lucide-react";

interface Tab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: "risk", label: "RISK", icon: <Shield size={13} /> },
  { id: "sar", label: "SAR", icon: <Radar size={13} /> },
  { id: "ml", label: "ML", icon: <Brain size={13} /> },
  { id: "climate", label: "CLIMATE", icon: <Cloud size={13} /> },
  { id: "indices", label: "INDICES", icon: <Layers size={13} /> },
  { id: "hydrology", label: "HYDRO", icon: <Droplets size={13} /> },
  { id: "forecast", label: "FORECAST", icon: <CloudRain size={13} /> },
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
        >
          {tab.icon}
          <span style={{ marginLeft: 6 }}>{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}
