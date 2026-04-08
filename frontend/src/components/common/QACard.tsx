import type { SARQualityMetadata } from "../../types/api";

interface QACardProps {
  quality: SARQualityMetadata;
  analysisParams?: {
    threshold?: number;
    polarization?: string;
    f_start?: string;
    f_end?: string;
    area_ha?: number;
  };
}

export function QACard({ quality, analysisParams }: QACardProps) {
  const confPct = (quality.confidence_score * 100).toFixed(0);
  const confColor = quality.confidence_score >= 0.7 ? "#1a9850" : quality.confidence_score >= 0.4 ? "#e6ab02" : "#d73027";
  const badge = quality.confidence_score >= 0.7 ? "HIGH" : quality.confidence_score >= 0.4 ? "MEDIUM" : "LOW";

  const handleDownloadJSON = () => {
    const artifact = {
      quality_metadata: quality,
      analysis_parameters: analysisParams,
      generated_at: new Date().toISOString(),
      caveats: getCaveats(quality),
    };
    const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `qa_report_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadCSV = () => {
    const rows = [
      ["metric", "value"],
      ["reference_strategy", quality.reference_strategy],
      ["n_pre_scenes", String(quality.n_pre_scenes)],
      ["n_post_scenes", String(quality.n_post_scenes)],
      ["orbit_consistency", String(quality.orbit_consistency)],
      ["temporal_gap_days", String(quality.temporal_gap_days)],
      ["confidence_score", String(quality.confidence_score)],
      ["validation_badge", badge],
    ];
    if (analysisParams?.threshold) rows.push(["threshold_db", String(analysisParams.threshold)]);
    if (analysisParams?.polarization) rows.push(["polarization", analysisParams.polarization]);
    if (analysisParams?.area_ha) rows.push(["flood_area_ha", String(analysisParams.area_ha)]);

    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `qa_report_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", marginBottom: "1rem", background: "var(--surface)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h3 style={{ margin: 0, fontSize: "0.95rem" }}>Quality Assurance</h3>
        <span style={{
          display: "inline-block",
          padding: "2px 10px",
          borderRadius: 4,
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "#fff",
          background: confColor,
        }}>
          {badge} CONFIDENCE — {confPct}%
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem", fontSize: "0.85rem" }}>
        <div><strong>Strategy:</strong> {quality.reference_strategy.replace(/_/g, " ")}</div>
        <div><strong>Pre-scenes:</strong> {quality.n_pre_scenes}</div>
        <div><strong>Post-scenes:</strong> {quality.n_post_scenes}</div>
        <div><strong>Orbit match:</strong> {quality.orbit_consistency ? "Yes" : "No"}</div>
        <div><strong>Temporal gap:</strong> {quality.temporal_gap_days}d</div>
        {analysisParams?.threshold && <div><strong>Threshold:</strong> {analysisParams.threshold} dB</div>}
      </div>

      {quality.low_data_warning && (
        <p style={{ color: "#d73027", fontSize: "0.82rem", marginTop: "0.5rem", marginBottom: 0 }}>
          {quality.low_data_warning}
        </p>
      )}

      {getCaveats(quality).length > 0 && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.82rem", color: "var(--text-secondary)" }}>
          <strong>Caveats:</strong>
          <ul style={{ margin: "0.25rem 0 0 1.25rem", padding: 0 }}>
            {getCaveats(quality).map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
        <button className="btn" onClick={handleDownloadJSON} style={{ fontSize: "0.8rem" }}>
          Download QA (JSON)
        </button>
        <button className="btn" onClick={handleDownloadCSV} style={{ fontSize: "0.8rem" }}>
          Download QA (CSV)
        </button>
      </div>
    </div>
  );
}

function getCaveats(quality: SARQualityMetadata): string[] {
  const caveats: string[] = [];
  if (quality.n_pre_scenes < 3) caveats.push("Few pre-flood scenes — reference composite may be noisy.");
  if (quality.n_post_scenes < 2) caveats.push("Few post-flood scenes — flood extent may be under/over-estimated.");
  if (!quality.orbit_consistency) caveats.push("Mixed orbit passes — may introduce geometric artifacts.");
  if (quality.temporal_gap_days > 60) caveats.push("Large temporal gap — seasonal vegetation changes may affect results.");
  if (quality.confidence_score < 0.4) caveats.push("Low confidence — treat results as indicative, not definitive.");
  return caveats;
}
