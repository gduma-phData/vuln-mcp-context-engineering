"use client";

import { useState } from "react";
import { searchKB, scanOntology } from "../../lib/api";

interface KBResult {
  text: string;
  source: string;
  section: string;
}

interface OntologyRepo {
  name: string;
  description: string;
  url: string;
  priority: string;
  updated_at: string;
}

interface OntologyScanResult {
  repos_found: number;
  repos: OntologyRepo[];
  analysis: string;
  tools_used: string[];
}

export default function KBTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KBResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [scanResult, setScanResult] = useState<OntologyScanResult | null>(null);
  const [scanning, setScanning] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await searchKB(query);
      setResults(res.results || []);
    } catch {
      setResults([]);
    }
    setLoading(false);
  };

  const handleOntologyScan = async () => {
    setScanning(true);
    try {
      const res = await scanOntology();
      setScanResult(res);
    } catch (e: any) {
      setScanResult({ repos_found: 0, repos: [], analysis: `Error: ${e.message}`, tools_used: [] });
    }
    setScanning(false);
  };

  const priorityColor = (p: string) => {
    if (p === "HIGH") return "var(--accent-red)";
    if (p === "MEDIUM") return "var(--accent-orange)";
    return "var(--accent-green)";
  };

  return (
    <div className="kb-container">
      {/* Ontology Monitor Section */}
      <div className="ontology-section">
        <div className="ontology-header">
          <div>
            <h3 className="ontology-title">Ontology Monitor</h3>
            <p className="ontology-subtitle">
              Scan GitHub for semantic view updates proposed by the security team
            </p>
          </div>
          <button
            className="scan-btn"
            onClick={handleOntologyScan}
            disabled={scanning}
          >
            {scanning ? "Scanning..." : "Scan for Updates"}
          </button>
        </div>

        {scanning && (
          <div className="ontology-scanning">
            <div className="loading"><div className="spinner" />Scanning GitHub repos and analyzing ontology changes...</div>
          </div>
        )}

        {scanResult && !scanning && (
          <div className="ontology-results">
            <div className="ontology-repos-grid">
              {scanResult.repos.map((repo) => (
                <div key={repo.name} className="ontology-repo-card">
                  <div className="repo-header">
                    <span className="repo-priority" style={{ color: priorityColor(repo.priority) }}>
                      {repo.priority}
                    </span>
                    <a href={repo.url} target="_blank" rel="noopener noreferrer" className="repo-link">
                      {repo.name}
                    </a>
                  </div>
                  <p className="repo-desc">{repo.description}</p>
                </div>
              ))}
            </div>

            {scanResult.tools_used.length > 0 && (
              <div className="ontology-tools">
                {scanResult.tools_used.map((t) => (
                  <span key={t} className="tools-badge mcp">{t}</span>
                ))}
              </div>
            )}

            <div className="ontology-analysis">
              <h4>Agent Analysis & Proposed DDL</h4>
              <div className="analysis-content">{scanResult.analysis}</div>
            </div>
          </div>
        )}
      </div>

      {/* KB Search Section */}
      <div className="kb-search-section">
        <h3 className="kb-section-title">Knowledge Base Search</h3>
        <div className="kb-search-row">
          <input
            className="chat-input"
            placeholder="Search vulnerability standards (CVSS, EPSS, KEV, CWE, ATT&CK...)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button className="send-btn" onClick={handleSearch} disabled={loading || !query.trim()}>
            Search
          </button>
        </div>

        {loading && (
          <div className="loading"><div className="spinner" />Searching knowledge base...</div>
        )}

        <div className="kb-results">
          {!searched && !loading && (
            <div style={{ textAlign: "center", marginTop: "20px", color: "var(--text-muted)", fontSize: "13px" }}>
              10 documents covering NVD, CVSS, EPSS, KEV, CWE, ATT&CK standards
            </div>
          )}
          {searched && results.length === 0 && !loading && (
            <div style={{ textAlign: "center", marginTop: "20px", color: "var(--text-muted)" }}>
              No results found.
            </div>
          )}
          {results.map((r, i) => (
            <div key={i} className="kb-result">
              <div className="source">{r.source}</div>
              {r.section && <div className="section">{r.section}</div>}
              <div className="text">{r.text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
