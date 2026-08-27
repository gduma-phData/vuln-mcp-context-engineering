"use client";

import { useState } from "react";
import ChatTab from "./components/ChatTab";
import SemanticLayerTab from "./components/SemanticLayerTab";
import KBTab from "./components/KBTab";

type Tab = "chat" | "semantic" | "kb";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-left">
          <div className="brand-icon">VI</div>
          <div>
            <h1>Vulnerability Intelligence</h1>
            <p className="subtitle">MCP Context Engineering Demo</p>
          </div>
        </div>
        <div className="header-right">
          <div className="status-pills">
            <div className="status-pill"><span className="dot" />Semantic View</div>
            <div className="status-pill"><span className="dot" />Cortex Search</div>
            <a
              className="status-pill mcp-cowork"
              href="https://app.snowflake.com/ra89421.east-us-2.azure/ra89421/#/compute/cowork"
              target="_blank"
              rel="noopener noreferrer"
              title="GitHub MCP available in CoWork (requires Snowsight OAuth)"
            >
              <span className="dot cowork" />GitHub MCP (CoWork)
            </a>
          </div>
        </div>
      </header>

      <nav className="tabs">
        <div className={`tab ${activeTab === "chat" ? "active" : ""}`} onClick={() => setActiveTab("chat")}>
          Agent Chat
        </div>
        <div className={`tab ${activeTab === "semantic" ? "active" : ""}`} onClick={() => setActiveTab("semantic")}>
          Semantic Layer
        </div>
        <div className={`tab ${activeTab === "kb" ? "active" : ""}`} onClick={() => setActiveTab("kb")}>
          Knowledge Base
        </div>
      </nav>

      <div className="tab-content">
        {activeTab === "chat" && <ChatTab />}
        {activeTab === "semantic" && <SemanticLayerTab />}
        {activeTab === "kb" && <KBTab />}
      </div>
    </div>
  );
}
