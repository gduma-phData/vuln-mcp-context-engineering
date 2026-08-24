"use client";

import { useState, useEffect } from "react";
import { getSVSummary, getSVYaml } from "../../lib/api";

export default function SemanticLayerTab() {
  const [summary, setSummary] = useState<any>(null);
  const [yaml, setYaml] = useState<string>("");
  const [showYaml, setShowYaml] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getSVSummary(), getSVYaml()])
      .then(([summaryRes, yamlRes]) => {
        setSummary(summaryRes);
        setYaml(yamlRes.yaml || "");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="sv-container">
        <div className="loading"><div className="spinner" />Loading semantic view...</div>
      </div>
    );
  }

  const arch = summary?.architecture || {};
  const tools = summary?.tools || {};

  return (
    <div className="sv-container">
      <div className="sv-card">
        <h3>Semantic View: {summary?.view_name || "VULNERABILITY_INTELLIGENCE"}</h3>
        <div className="sv-stat-grid">
          <div className="sv-stat">
            <div className="num">{arch.tables?.length || 4}</div>
            <div className="label">Tables</div>
          </div>
          <div className="sv-stat">
            <div className="num">{arch.relationships?.length || 2}</div>
            <div className="label">Relationships</div>
          </div>
          <div className="sv-stat">
            <div className="num">{arch.metrics?.length || 5}</div>
            <div className="label">Metrics</div>
          </div>
          <div className="sv-stat">
            <div className="num">{arch.facts?.length || 5}</div>
            <div className="label">Facts</div>
          </div>
          <div className="sv-stat">
            <div className="num">{arch.dimensions_count || 19}</div>
            <div className="label">Dimensions</div>
          </div>
        </div>
      </div>

      <div className="sv-card">
        <h3>Agent Tools</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
          <div>
            <span className="tools-badge sv">Semantic View</span>{" "}
            <span style={{ color: "var(--text-secondary)" }}>{tools.semantic_view}</span>
          </div>
          <div>
            <span className="tools-badge kb">Cortex Search</span>{" "}
            <span style={{ color: "var(--text-secondary)" }}>{tools.search_service}</span>
          </div>
          <div>
            <span className="tools-badge mcp">GitHub MCP</span>{" "}
            <span style={{ color: "var(--text-secondary)" }}>{tools.mcp_server}</span>
          </div>
        </div>
      </div>

      <div className="sv-card">
        <h3>Tables</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {(arch.tables || []).map((t: any) => (
            <div key={t.name} style={{ fontSize: "13px", padding: "8px", background: "var(--bg-tertiary)", borderRadius: "4px" }}>
              <strong style={{ color: "var(--accent-blue)" }}>{t.name}</strong>
              <span style={{ color: "var(--text-secondary)", marginLeft: "8px" }}>{t.role}</span>
              <span style={{ color: "var(--text-muted)", marginLeft: "8px", fontSize: "11px" }}>{t.grain}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="sv-card">
        <h3 style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          YAML Definition
          <button
            onClick={() => setShowYaml(!showYaml)}
            style={{ fontSize: "11px", padding: "4px 10px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--bg-tertiary)", color: "var(--text-secondary)", cursor: "pointer" }}
          >
            {showYaml ? "Hide" : "Show"}
          </button>
        </h3>
        {showYaml && <div className="yaml-viewer">{yaml || "No YAML available"}</div>}
      </div>
    </div>
  );
}
