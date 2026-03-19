interface Tab {
  id: string;
  label: string;
}

const TABS: Tab[] = [
  { id: "risk", label: "RISK" },
  { id: "sar", label: "SAR" },
  { id: "ml", label: "ML" },
  { id: "climate", label: "CLIMATE" },
  { id: "indices", label: "INDICES" },
  { id: "hydrology", label: "HYDROLOGY" },
  { id: "forecast", label: "FORECAST" },
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
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
