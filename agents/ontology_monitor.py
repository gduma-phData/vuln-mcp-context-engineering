"""Ontology Monitor Agent -- scans GitHub repos for semantic view updates.

Uses direct GitHub API calls to read ontology repos, then feeds the content
to Cortex Agent for analysis and DDL proposal generation.
"""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agents.github_tool import search_ontology_repos, get_ontology_context, get_repo_readme, get_file_content, list_repo_files
from agents.named_agent_client import _generate_jwt_token, _get_agent_endpoint

import httpx
import json


def scan_ontology_updates() -> dict:
    """Scan GitHub for ontology repos and generate proposed semantic view changes."""
    # Step 1: Discover ontology repos via GitHub API
    repos = search_ontology_repos()
    if not repos:
        return {
            "repos_found": 0,
            "proposals": [],
            "summary": "No ontology update repositories found.",
        }

    # Step 2: Read content from all repos
    ontology_context = get_ontology_context()

    # Step 3: Get current SV definition for comparison
    sv_summary = _get_current_sv_summary()

    # Step 4: Call Cortex Agent to analyze and propose changes
    analysis = _analyze_ontology_updates(ontology_context, sv_summary)

    # Step 5: Structure the response
    repo_summaries = []
    for r in repos:
        readme = get_repo_readme(r["name"])
        priority = "HIGH" if "HIGH" in (readme or "") else "MEDIUM" if "MEDIUM" in (readme or "") else "LOW"
        repo_summaries.append({
            "name": r["name"],
            "description": r["description"],
            "url": r["url"],
            "updated_at": r["updated_at"],
            "priority": priority,
        })

    return {
        "repos_found": len(repos),
        "repos": repo_summaries,
        "analysis": analysis.get("answer", ""),
        "tools_used": ["github_ontology_repos"] + analysis.get("tools_used", []),
    }


def _get_current_sv_summary() -> str:
    """Get a summary of the current semantic view structure."""
    return """Current Semantic View: VULNERABILITY_INTELLIGENCE
Tables:
- V_FACT_VULNERABILITY: CVE_ID, CVSS_V31_BASE_SCORE, EPSS_SCORE, EPSS_PERCENTILE, IS_KEV, KEV_DATE_ADDED, DESCRIPTION, PUBLISHED_DATE, LAST_MODIFIED
- V_DIM_WEAKNESS: CWE_ID, CWE_NAME, CWE_DESCRIPTION
- V_CVE_ATTACK_TACTICS: CVE_ID, TECHNIQUE_ID, TECHNIQUE_NAME, TACTIC
- V_PHISHING_RELEVANCE: CVE_ID, PHISHING_TECHNIQUE, RELEVANCE_SCORE

Metrics: VULNERABILITY_COUNT, AVG_CVSS, AVG_EPSS, MAX_CVSS, MAX_EPSS
Facts: CVSS_V31_BASE_SCORE, EPSS_SCORE, EPSS_PERCENTILE, CVSS_V31_EXPLOITABILITY_SCORE, CVSS_V31_IMPACT_SCORE
Dimensions: 19 total across all tables"""


def _analyze_ontology_updates(ontology_context: str, sv_summary: str) -> dict:
    """Call Cortex Agent to analyze ontology updates and propose DDL."""
    db = os.getenv("SNOWFLAKE_DB", "SANDBOX")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "GDUMA")
    model = os.getenv("CORTEX_MODEL", "openai-gpt-4.1")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "DEFAULT_USER_WH")

    token = _generate_jwt_token()
    endpoint = _get_agent_endpoint()

    system_prompt = f"""You are an ontology governance analyst. Your job is to review proposed changes to a vulnerability intelligence semantic view and produce a structured analysis.

Current Semantic View Definition:
{sv_summary}

You have been given documentation from GitHub repositories that propose updates to this semantic view. For each repository/proposal:
1. Summarize what changes are proposed
2. Assess the impact (new columns, new rows, relationship changes)
3. Assign a priority (HIGH/MEDIUM/LOW)
4. Extract the proposed DDL statements

Format your response as a structured report with clear sections for each ontology update. Include all proposed DDL at the end in a consolidated section."""

    user_message = f"""Analyze these ontology update proposals from our GitHub repositories and produce a governance report with proposed DDL changes:

{ontology_context}"""

    request_body = {
        "model": model,
        "tools": [
            {"tool_spec": {"name": "vuln_standards_kb", "type": "cortex_search"}},
        ],
        "tool_resources": {
            "vuln_standards_kb": {
                "search_service": f"{db}.{schema}.VULN_STANDARDS_SEARCH",
                "id_column": "document_name",
                "title_column": "document_name",
            },
        },
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_message}]},
        ],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        "X-Snowflake-Role": os.getenv("SNOWFLAKE_ROLE", "ALL_AAI_ARCHITECTS"),
    }
    if warehouse:
        headers["X-Snowflake-Warehouse"] = warehouse

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(endpoint, json=request_body, headers=headers)
            if response.status_code != 200:
                return {"answer": "Failed to analyze ontology updates.", "tools_used": []}
            return _parse_sse_response(response)
    except Exception as e:
        return {"answer": f"Analysis error: {str(e)}", "tools_used": []}


def _parse_sse_response(response) -> dict:
    """Parse SSE response from Cortex Agent."""
    text_parts = []
    tools_used = []

    for line in response.text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if "message" in event and "code" in event:
            return {"answer": f"Error: {event.get('message', '')}", "tools_used": []}

        delta = event.get("delta", {})
        for block in delta.get("content", []):
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_name = block.get("tool_use", {}).get("name", "")
                if tool_name and tool_name not in tools_used:
                    tools_used.append(tool_name)
            elif block_type == "tool_results":
                tool_name = block.get("tool_results", {}).get("name", "")
                if tool_name and tool_name not in tools_used:
                    tools_used.append(tool_name)

    return {
        "answer": "".join(text_parts).strip(),
        "tools_used": tools_used,
    }
