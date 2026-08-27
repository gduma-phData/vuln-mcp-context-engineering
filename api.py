"""FastAPI Backend for Vulnerability Intelligence + MCP Context Engineering Demo."""
import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agents.named_agent_client import call_named_agent, call_named_agent_with_mcp
from agents.search_client import search_kb
from agents.oauth_flow import start_oauth_flow, finish_oauth_flow, check_oauth_status
from agents.ontology_monitor import scan_ontology_updates

app = FastAPI(title="Vulnerability Intelligence - MCP Context Engineering")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    role: str = "ALL_AAI_ARCHITECTS"
    thread_id: int | None = None
    parent_message_id: int | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "vuln-mcp-context-engineering"}


@app.post("/agent/chat")
async def agent_chat(request: ChatRequest):
    """Send a question to the Cortex Agent (SV + Search). MCP available in CoWork."""
    try:
        result = call_named_agent(
            request.question,
            role=request.role,
            thread_id=request.thread_id,
            parent_message_id=request.parent_message_id,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/oauth/status")
async def mcp_oauth_status():
    """Check if GitHub MCP OAuth is connected for the current Snowflake user."""
    try:
        result = check_oauth_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/oauth/start")
async def mcp_oauth_start():
    """Start GitHub OAuth flow. Returns the Snowflake-hosted authorization URL.
    
    The user must be logged into Snowsight in the same browser for this URL to work.
    Snowflake handles the full OAuth round-trip with GitHub.
    """
    try:
        result = start_oauth_flow()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/oauth/callback")
async def mcp_oauth_callback(request: Request):
    """Handle OAuth callback from GitHub. Passes the full query string to Snowflake."""
    try:
        # Pass the entire query string to SYSTEM$FINISH_OAUTH_FLOW
        full_query_string = str(request.url.query)
        result = finish_oauth_flow(query_string=full_query_string)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        if result.get("connected"):
            return RedirectResponse(url=f"{frontend_url}?mcp_connected=true")
        # If it failed, redirect with error
        error_msg = result.get("error", "OAuth flow failed")
        return RedirectResponse(url=f"{frontend_url}?mcp_error={error_msg}")
    except Exception as e:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}?mcp_error={str(e)}")


@app.post("/ontology/scan")
async def ontology_scan():
    """Scan GitHub ontology repos and propose semantic view updates."""
    try:
        result = scan_ontology_updates()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-kb")
async def search(request: SearchRequest):
    """Search the vulnerability standards knowledge base."""
    try:
        results = search_kb(request.query, limit=request.limit)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/semantic-view/summary")
async def sv_summary(role: str = "ALL_AAI_ARCHITECTS"):
    """Get semantic view architecture summary."""
    return {
        "status": "success",
        "view_name": "VULNERABILITY_INTELLIGENCE",
        "architecture": {
            "pattern": "One semantic view per business domain",
            "tables": [
                {"name": "V_FACT_VULNERABILITY", "role": "Central fact (NVD + EPSS + KEV)", "grain": "One row per CVE"},
                {"name": "V_DIM_WEAKNESS", "role": "CWE weakness taxonomy", "grain": "One row per CWE"},
                {"name": "V_CVE_ATTACK_TACTICS", "role": "ATT&CK tactic bridge", "grain": "One row per CVE-technique"},
                {"name": "V_PHISHING_RELEVANCE", "role": "Phishing classification", "grain": "One row per CVE-phishing technique"},
            ],
            "relationships": [
                "ATTACK_TO_VULN: V_CVE_ATTACK_TACTICS -> V_FACT_VULNERABILITY",
                "PHISHING_TO_VULN: V_PHISHING_RELEVANCE -> V_FACT_VULNERABILITY",
            ],
            "metrics": ["VULNERABILITY_COUNT", "AVG_CVSS", "AVG_EPSS", "MAX_CVSS", "MAX_EPSS"],
            "facts": ["CVSS_V31_BASE_SCORE", "EPSS_SCORE", "EPSS_PERCENTILE", "CVSS_V31_EXPLOITABILITY_SCORE", "CVSS_V31_IMPACT_SCORE"],
            "dimensions_count": 19,
        },
        "tools": {
            "semantic_view": "SANDBOX.GDUMA.VULNERABILITY_INTELLIGENCE",
            "search_service": "SANDBOX.GDUMA.VULN_STANDARDS_SEARCH",
            "mcp_server": "SANDBOX.GDUMA.GITHUB_PATCH_REPOS",
        },
        "agent": "SANDBOX.GDUMA.VULN_INTELLIGENCE_AGENT",
    }


@app.get("/semantic-view/yaml")
async def sv_yaml(role: str = "ALL_AAI_ARCHITECTS"):
    """Get the semantic view YAML definition."""
    from shared.snowflake_conn import get_snowflake_connection
    conn = get_snowflake_connection(role_override=role)
    try:
        cursor = conn.cursor()
        db = os.getenv("SNOWFLAKE_DB", "SANDBOX")
        schema = os.getenv("SNOWFLAKE_SCHEMA", "GDUMA")
        cursor.execute(f"SELECT GET_DDL('SEMANTIC VIEW', '{db}.{schema}.VULNERABILITY_INTELLIGENCE')")
        row = cursor.fetchone()
        return {"status": "success", "yaml": row[0] if row else ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
