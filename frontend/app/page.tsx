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
            <div className="status-pill"><span className="dot" />GitHub MCP</div>
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
