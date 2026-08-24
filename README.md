# Vulnerability Intelligence - MCP Context Engineering Demo

Cortex Agents + Native MCP (GitHub) + Semantic View + Cortex Search, hosted on AWS EKS.

## What This Is

A client-facing demo showing how Snowflake Cortex Agents can use **native MCP connectors** to extend their knowledge beyond structured data. The agent combines:

1. **Semantic View** (Cortex Analyst) -- vulnerability data: CVEs, CVSS scores, EPSS probability, CISA KEV, CWE weaknesses, ATT&CK tactics
2. **Cortex Search** (RAG) -- 10 standards documents covering NVD, CVSS, EPSS, KEV, CWE, ATT&CK
3. **GitHub MCP** -- 50 dummy repos simulating an infosec team's patch tracking system

The demo moment: "Have we pushed a patch for the latest KEV critical vulnerabilities?" -- the agent queries the SV for KEV criticals, then uses GitHub MCP tools to check patch status in the org's repos.

## Architecture

```
Frontend (Next.js 14) :3000          Backend (FastAPI) :8000
+---------------------------+        +---------------------------+
| Tab: Agent Chat (hero)    |------->| POST /agent/chat          |
| Tab: Semantic Layer       |        | POST /search-kb           |
| Tab: Knowledge Base       |        | GET  /semantic-view/*     |
+---------------------------+        +---------------------------+
                                              |
                                     Snowflake Cortex Agent
                                     (ad-hoc /api/v2/cortex/agent:run)
                                              |
                          +-------------------+-------------------+
                          |                   |                   |
                   Semantic View       Cortex Search       GitHub MCP
                   (text-to-SQL)       (RAG over KB)       (patch repos)
                          |                   |                   |
              VULNERABILITY_INTELLIGENCE  VULN_STANDARDS_SEARCH  GITHUB_PATCH_REPOS
```

## Live URLs

| Service | URL |
|---------|-----|
| API (AWS EKS) | `http://af47646dd8025463088e07462513bd8e-1955463065.us-east-1.elb.amazonaws.com` |
| Frontend (AWS EKS) | `http://a864e64759de04dd9bea65a4fd86c6bb-1432444262.us-east-1.elb.amazonaws.com` |
| GitHub Repo | `https://github.com/gduma-phData/vuln-mcp-context-engineering` |
| Patch Repos (50) | `https://github.com/gduma-phData?tab=repositories&q=patch-CVE` |

Note: ELB URLs change after weekly AWS cleanup/rebuild. See CORTEX.md.

## Quick Start (Local)

```bash
# Prerequisites: conda, node 20+, Snowflake key-pair auth
cp .env.example .env  # Edit with your credentials
make create_conda_env && conda activate vuln-mcp
make frontend-install
make backend    # Terminal 1 - API on :8000
make frontend   # Terminal 2 - UI on :3000
```

Or with Docker:
```bash
make docker-up  # Starts both services
```

## Snowflake Objects

| Object | Type | Purpose |
|--------|------|---------|
| `SANDBOX.GDUMA.VULNERABILITY_INTELLIGENCE` | Semantic View | 4 tables, 5 metrics, 19 dimensions |
| `SANDBOX.GDUMA.VULN_STANDARDS_SEARCH` | Cortex Search | 134 chunks, 10 documents |
| `SANDBOX.GDUMA.VULN_INTELLIGENCE_AGENT` | Named Agent | SV + Search + MCP tools |
| `SANDBOX.GDUMA.GITHUB_PATCH_REPOS` | External MCP Server | GitHub connector |
| `github_mcp_api_integration` | API Integration | OAuth for GitHub (ACCOUNTADMIN owned) |

## Data

- 7,977 NVD CVEs (30-day window)
- 1,629 CISA KEV entries
- 343,508 EPSS scores
- 969 CWE weaknesses
- 52 CWE-to-ATT&CK mappings
- 134 KB chunks across 10 documents
- 50 GitHub patch repos (dummy CMDB simulation)

## GitHub MCP Connector

The GitHub App credentials:
- Client ID: `Iv23liyRuSENCxUvzaLu`
- App name: `vuln-mcp-snowflake`
- MCP Server URL: `https://api.githubcopilot.com/mcp`

The MCP connector requires user OAuth authentication. In CoWork/Snowsight, users click "Connect" on the GitHub connector. For the REST API, use `SYSTEM$START_USER_OAUTH_FLOW('github_mcp_api_integration')`.

## AWS Hosting

Hosted on phData POC account (637119802057, us-east-1). Services may be deleted weekly. See `CORTEX.md` for full rebuild instructions.

| Component | Resource |
|-----------|----------|
| Container Registry | ECR: `vuln-mcp-api`, `vuln-mcp-frontend` |
| Cluster | EKS: `vuln-mcp` (2x t3.medium nodes) |
| State | S3: `vuln-mcp-terraform-state` |
| Deployments | Helm chart in `./helm/` |

## Project Structure

```
vuln-mcp-context-engineering/
├── api.py                          # FastAPI backend (4 endpoints)
├── agents/
│   ├── named_agent_client.py       # Calls Cortex Agent REST API (ad-hoc endpoint)
│   └── search_client.py            # Cortex Search client
├── shared/snowflake_conn.py        # Connection helper (key-pair auth)
├── frontend/                       # Next.js 14 (3-tab layout)
│   ├── app/page.tsx                # Tab container
│   ├── app/components/ChatTab.tsx  # Agent chat (hero tab)
│   ├── app/components/SemanticLayerTab.tsx
│   ├── app/components/KBTab.tsx
│   └── lib/api.ts                  # API client
├── snowflake/ddl/                  # All Snowflake DDL
│   ├── 001_create_schemas.sql
│   ├── 010_create_raw_tables.sql
│   ├── 020_create_mart_views.sql
│   ├── 040_create_search_service.sql
│   ├── 045_create_semantic_view.sql
│   ├── 050_create_mcp_server.sql   # Requires ACCOUNTADMIN
│   └── 060_create_agent.sql
├── ingestion/                      # Data pipeline scripts
├── scripts/
│   ├── create_dummy_patch_repos.sh # Creates 50 GitHub patch repos
│   ├── apply_snowflake_ddl.py
│   ├── deploy_semantic_view.py
│   └── create_agent.py
├── terraform/                      # ECR repos
├── helm/                           # K8s deployment manifests
├── CORTEX.md                       # Weekly AWS rebuild guide
├── HANDOFF.md                      # Session handoff document
├── Dockerfile, docker-compose.yml, makefile, environment.yml
└── .env.example
```

## Key Design Decisions

1. **Ad-hoc vs Named Agent**: The custom frontend uses `/api/v2/cortex/agent:run` (ad-hoc) because the named agent endpoint requires user-level OAuth for MCP tools. The named agent works in CoWork where OAuth is handled by the UI.

2. **MCP for GitHub**: Native Snowflake MCP connector (not a custom bridge). The agent discovers GitHub tools at runtime and can search repos, read files, list PRs.

3. **3-Tab Frontend**: Simplified from the original 3-panel app. Chat is the hero; SV and KB are supporting tabs for the demo.

4. **Weekly Rebuild**: AWS resources on a PoC account that auto-deletes. All infra is re-creatable via `make aws-deploy`. Snowflake objects persist.
