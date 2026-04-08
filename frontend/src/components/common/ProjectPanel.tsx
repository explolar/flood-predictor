/**
 * Project panel — saved AOIs, run history, timeline comparison.
 * Renders in the sidebar area when opened.
 */

import { useState } from "react";
import type { SavedAOI, RunRecord } from "../../hooks/useProjectStore";
import { Bookmark, Clock, Trash2, Download, Share2 } from "lucide-react";

interface ProjectPanelProps {
  savedAOIs: SavedAOI[];
  runHistory: RunRecord[];
  onLoadAOI: (aoi: SavedAOI) => void;
  onDeleteAOI: (id: string) => void;
  onClearHistory: () => void;
  onSaveCurrentAOI: () => void;
  currentAOIName?: string;
  isAOIActive: boolean;
}

export function ProjectPanel({
  savedAOIs,
  runHistory,
  onLoadAOI,
  onDeleteAOI,
  onClearHistory,
  onSaveCurrentAOI,
  currentAOIName,
  isAOIActive,
}: ProjectPanelProps) {
  const [view, setView] = useState<"aois" | "history">("aois");

  const handleShareAnalysis = (run: RunRecord) => {
    const shareData = {
      ...run,
      shared_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(shareData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis_${run.tab}_${run.timestamp.slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadReport = () => {
    const report = {
      generated_at: new Date().toISOString(),
      saved_aois: savedAOIs,
      run_history: runHistory,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fluviaai_report_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: "0.75rem" }}>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <button
          className={`tab-item ${view === "aois" ? "tab-active" : ""}`}
          onClick={() => setView("aois")}
          style={{ flex: 1, fontSize: "0.8rem" }}
        >
          <Bookmark size={12} /> AOIs ({savedAOIs.length})
        </button>
        <button
          className={`tab-item ${view === "history" ? "tab-active" : ""}`}
          onClick={() => setView("history")}
          style={{ flex: 1, fontSize: "0.8rem" }}
        >
          <Clock size={12} /> History ({runHistory.length})
        </button>
      </div>

      {view === "aois" && (
        <>
          {isAOIActive && (
            <button
              className="btn btn-primary"
              onClick={onSaveCurrentAOI}
              style={{ width: "100%", marginBottom: "0.5rem", fontSize: "0.82rem" }}
            >
              <Bookmark size={12} /> Save Current AOI{currentAOIName ? `: ${currentAOIName}` : ""}
            </button>
          )}

          {savedAOIs.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem", textAlign: "center" }}>
              No saved AOIs yet. Run an analysis and save the AOI.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {savedAOIs.map((aoi) => (
                <div key={aoi.id} style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.4rem 0.6rem",
                  borderRadius: 6,
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  fontSize: "0.82rem",
                }}>
                  <button
                    onClick={() => onLoadAOI(aoi)}
                    style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontWeight: 500, textAlign: "left", flex: 1 }}
                  >
                    {aoi.name || "Unnamed AOI"}
                    <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
                      {new Date(aoi.created_at).toLocaleDateString()}
                    </div>
                  </button>
                  <button
                    onClick={() => onDeleteAOI(aoi.id)}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "#d73027", padding: 4 }}
                    title="Delete AOI"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {view === "history" && (
        <>
          {runHistory.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem", textAlign: "center" }}>
              No analysis runs recorded yet.
            </p>
          ) : (
            <>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", maxHeight: 300, overflowY: "auto" }}>
                {runHistory.slice(0, 20).map((run) => (
                  <div key={run.id} style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.4rem 0.6rem",
                    borderRadius: 6,
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    fontSize: "0.78rem",
                  }}>
                    <div>
                      <span style={{ fontWeight: 500, textTransform: "uppercase", color: "var(--accent)" }}>{run.tab}</span>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
                        {new Date(run.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <button
                      onClick={() => handleShareAnalysis(run)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)", padding: 4 }}
                      title="Download analysis"
                    >
                      <Share2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
                <button className="btn" onClick={handleDownloadReport} style={{ flex: 1, fontSize: "0.78rem" }}>
                  <Download size={12} /> Download All
                </button>
                <button className="btn" onClick={onClearHistory} style={{ flex: 1, fontSize: "0.78rem", color: "#d73027" }}>
                  <Trash2 size={12} /> Clear History
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
