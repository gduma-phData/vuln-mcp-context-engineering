"use client";

import { useState, useRef, useEffect } from "react";
import { chatWithAgent } from "../../lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
  sql?: string;
  data?: Record<string, string | null>[];
}

const SAMPLE_QUESTIONS = [
  "What are the top 10 most exploitable critical vulnerabilities?",
  "Have we pushed patches for the latest KEV critical vulnerabilities?",
  "Which ATT&CK tactics are most associated with our critical vulns?",
  "What is the difference between CVSS severity and EPSS probability?",
  "Do we have a patch deployed for CVE-2026-31337?",
];

export default function ChatTab() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question?: string) => {
    const q = question || input.trim();
    if (!q) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res = await chatWithAgent(q);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer || "No response.",
          tools_used: res.tools_used || [],
          sql: res.sql || "",
          data: res.data || [],
        },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e.message}` },
      ]);
    }
    setLoading(false);
  };

  const toolBadge = (tool: string) => {
    if (tool.includes("vulnerability") || tool.includes("sv") || tool.includes("analyst"))
      return <span className="tools-badge sv" key={tool}>SV: {tool}</span>;
    if (tool.includes("kb") || tool.includes("search") || tool.includes("standards"))
      return <span className="tools-badge kb" key={tool}>KB: {tool}</span>;
    return <span className="tools-badge mcp" key={tool}>MCP: {tool}</span>;
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <div className="empty-hero">
              <div className="empty-icon">?</div>
              <h2>Vulnerability Intelligence Agent</h2>
              <p className="empty-subtitle">
                Ask questions about CVEs, exploit probability, patch status, and security standards.
                Powered by Cortex Agent with Semantic View and Knowledge Base.
              </p>
            </div>

            <div className="empty-capabilities">
              <div className="capability-card">
                <div className="capability-icon sv-icon">SV</div>
                <div className="capability-label">Semantic View</div>
                <div className="capability-desc">Query 8K+ CVEs, CVSS scores, EPSS probability, CISA KEV status</div>
              </div>
              <div className="capability-card">
                <div className="capability-icon kb-icon">KB</div>
                <div className="capability-label">Knowledge Base</div>
                <div className="capability-desc">RAG over NVD, CVSS, EPSS, KEV, CWE, and ATT&CK documentation</div>
              </div>
              <div className="capability-card">
                <div className="capability-icon mcp-icon">MCP</div>
                <div className="capability-label">GitHub MCP</div>
                <div className="capability-desc">Patch repo lookups via native MCP connector (available in CoWork)</div>
              </div>
            </div>

            <div className="empty-suggestions">
              <p className="suggestions-label">Try asking</p>
              <div className="suggestion-cards">
                {SAMPLE_QUESTIONS.map((q) => (
                  <button key={q} className="suggestion-card" onClick={() => sendMessage(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
            {msg.tools_used && msg.tools_used.length > 0 && (
              <div style={{ marginTop: "8px", display: "flex", gap: "4px", flexWrap: "wrap" }}>
                {msg.tools_used.map(toolBadge)}
              </div>
            )}
            {msg.sql && (
              <div className="sql-block">{msg.sql}</div>
            )}
            {msg.data && msg.data.length > 0 && (
              <table className="data-table">
                <thead>
                  <tr>
                    {Object.keys(msg.data[0]).map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {msg.data.slice(0, 10).map((row, ri) => (
                    <tr key={ri}>
                      {Object.values(row).map((val, ci) => (
                        <td key={ci}>{val ?? ""}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="loading">
              <div className="spinner" />
              Agent is thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <input
            className="chat-input"
            placeholder="Ask about vulnerabilities, patches, or standards..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            disabled={loading}
          />
          <button className="send-btn" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
