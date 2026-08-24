"use client";

import { useState } from "react";
import { searchKB } from "../../lib/api";

interface KBResult {
  text: string;
  source: string;
  section: string;
}

export default function KBTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KBResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

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

  return (
    <div className="kb-container">
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
          <div style={{ textAlign: "center", marginTop: "40px", color: "var(--text-muted)" }}>
            <p style={{ fontSize: "14px" }}>Search the vulnerability standards knowledge base</p>
            <p style={{ fontSize: "12px", marginTop: "8px" }}>
              10 documents, 49 chunks covering NVD, CVSS, EPSS, KEV, CWE, ATT&CK, and semantic layer patterns
            </p>
          </div>
        )}
        {searched && results.length === 0 && !loading && (
          <div style={{ textAlign: "center", marginTop: "40px", color: "var(--text-muted)" }}>
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
  );
}
