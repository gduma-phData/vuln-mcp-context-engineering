# Session Handoff

Last updated: 2026-08-24 (Monday morning)

## Current State: Fully Deployed and Working

Everything is live:
- AWS EKS cluster with 4 pods (2 API, 2 frontend) serving on LoadBalancers
- Snowflake agent with SV + Search + GitHub MCP connector
- 50 GitHub patch repos created under gduma-phData
- Frontend builds and serves the 3-tab UI
- Agent successfully answers vulnerability questions via Semantic View

## What Works Right Now

| Feature | Status | Endpoint |
|---------|--------|----------|
| Agent Chat (SV queries) | Working | `POST /agent/chat` via ad-hoc endpoint |
| KB Search | Working | `POST /search-kb` via Cortex Search |
| SV Summary | Working | `GET /semantic-view/summary` |
| Frontend (local) | Working | `make frontend` on :3000 |
| Frontend (AWS) | Working | ELB URL in README |
| API (AWS) | Working | ELB URL in README |
| GitHub MCP in CoWork | Ready (untested) | Named agent in Snowsight |

## What Needs Attention

### 1. MCP OAuth Flow for Custom Frontend
The named agent REST API (`/agents/{name}:run`) returns empty responses because MCP tools require user-level OAuth authentication. Two paths:
- **CoWork/Snowsight**: Works out of the box (OAuth handled by UI). Users click "Connect" on GitHub connector.
- **Custom frontend**: Needs `SYSTEM$START_USER_OAUTH_FLOW('github_mcp_api_integration')` implementation. This returns an authorization URL the user visits, then `SYSTEM$FINISH_OAUTH_FLOW('<query_string>')` completes it.

### 2. Frontend API URL for AWS
The frontend Docker image was built with `NEXT_PUBLIC_API_URL=http://localhost:8000`. For the AWS deployment to make agent calls, rebuild with the API ELB URL:
```bash
API_URL="http://af47646dd8025463088e07462513bd8e-1955463065.us-east-1.elb.amazonaws.com"
docker buildx build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL=$API_URL \
  -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-frontend:latest --push ./frontend
kubectl rollout restart deployment vuln-mcp-frontend -n vuln-mcp
```

### 3. Demo Polish
- Add loading states for tool badges (show which tool the agent is calling)
- Add "MCP not connected" indicator when GitHub OAuth isn't authenticated
- Consider adding a CoWork embed or link for the MCP demo portion

## Key Credentials & Accounts

| Resource | Details |
|----------|---------|
| Snowflake Account | `ra89421.east-us-2.azure` |
| Snowflake User | `GDUMA@PHDATA.IO` |
| Snowflake Role | `ALL_AAI_ARCHITECTS` |
| Snowflake DB/Schema | `SANDBOX.GDUMA` |
| RSA Key | `/Users/gduma/Documents/client_work/GAIG/agent-eval-best-practices/rsa_key.p8` |
| AWS Account | `637119802057` (phdata-poc) |
| AWS Profile | `phdata-poc` |
| GitHub User | `gduma-phData` |
| GitHub App Client ID | `Iv23liyRuSENCxUvzaLu` |
| GitHub App Client Secret | `0d266c89c05ebe2417edeec453ab28a63e60d54a` |

## Architecture Notes

### Agent Endpoint Strategy
- **Ad-hoc** (`/api/v2/cortex/agent:run`): Used by our FastAPI backend. Supports SV + Search tools. Does NOT support MCP (requires inline tool definitions, MCP is only on named agents).
- **Named agent** (`/api/v2/databases/SANDBOX/schemas/GDUMA/agents/VULN_INTELLIGENCE_AGENT:run`): Has MCP wired in but requires user OAuth for MCP tools. Returns empty response if MCP auth not completed.
- **CoWork**: The named agent works perfectly in CoWork where the UI handles OAuth.

### The Demo Flow
1. Open frontend (Chat tab) -- show agent answering vulnerability questions via SV
2. Ask about patches -- agent says it can check GitHub (or redirects to CoWork for MCP)
3. Switch to CoWork in Snowsight -- same agent, connect GitHub, ask "Do we have a patch for CVE-2026-31337?"
4. Agent uses GitHub MCP to find the patch repo, reads the README, confirms patch deployed

### File Dependencies
- `.env` must exist with Snowflake credentials (not in git)
- RSA key at path specified by `SNOWFLAKE_PRIVATE_KEY_PATH`
- `frontend/node_modules/` needs `npm install` (not in git)
- AWS SSO must be refreshed: `aws sso login --profile phdata-poc`

## Rebuild Commands

### If AWS was cleaned up:
```bash
export AWS_PROFILE=phdata-poc
make aws-deploy  # Full rebuild: ECR + S3 + EKS + Helm + expose
```
Or follow step-by-step in `CORTEX.md`.

### If Snowflake agent needs recreation:
```bash
make setup_snowflake  # DDL + search service + SV + agent
```
Note: MCP server creation requires ACCOUNTADMIN. SQL in `snowflake/ddl/050_create_mcp_server.sql`.

### If patch repos need recreation:
```bash
make create_dummy_repos  # Creates 50 GitHub repos
```

## Session History

### Session 1 (2026-08-23/24, Sunday night)
- Created repo `gduma-phData/vuln-mcp-context-engineering`
- Built full project: FastAPI + Next.js + Snowflake DDL + Terraform + Helm
- Created 50 dummy patch repos on GitHub
- Deployed to EKS (4 pods, 2 LoadBalancers)
- Confirmed ad-hoc agent works (SV + Search)
- Created GitHub App via manifest flow (Client ID: Iv23liyRuSENCxUvzaLu)
- Had ACCOUNTADMIN create MCP server + API integration
- Wired MCP server into named agent
- Discovered named agent needs OAuth for MCP (works in CoWork, not REST without auth flow)
