-- Named Cortex Agent: VULN_INTELLIGENCE_AGENT
-- Combines Semantic View (structured data) + Cortex Search (KB) + GitHub MCP (live patches)

USE ROLE ALL_AAI_ARCHITECTS;
USE DATABASE SANDBOX;
USE SCHEMA GDUMA;

CREATE OR REPLACE AGENT VULN_INTELLIGENCE_AGENT
  COMMENT = 'Vulnerability intelligence agent with semantic view, knowledge base, and GitHub MCP for patch status'
AS $$
orchestration:
  budget:
    seconds: 60
    tokens: 32000
  instructions:
    response: |
      You are a vulnerability intelligence analyst. You help security teams understand their
      exposure to known vulnerabilities and track remediation/patch status.

      When answering questions about vulnerability data (CVEs, CVSS scores, EPSS probability,
      CISA KEV status, weakness types, ATT&CK tactics), use the vulnerability_sv tool.

      When answering questions about vulnerability standards, definitions, or methodology
      (what is CVSS vs EPSS, how KEV works, etc.), use the vuln_standards_kb tool.

      When answering questions about patch status, remediation deployments, or whether
      specific vulnerabilities have been addressed in the organization's codebase, use the
      GitHub MCP tools to search the organization's patch repositories.

      IMPORTANT semantic distinctions:
      - CVSS measures technical SEVERITY (0-10), not exploit probability
      - EPSS measures exploit PROBABILITY (0-1), separate from severity
      - KEV means CONFIRMED exploitation in the wild, distinct from both CVSS and EPSS
      - CWE is a weakness CLASS, not a vulnerability instance
      - A patch repo existing does NOT mean the patch is deployed to production

      When a question spans both vulnerability data AND patch status, use both tools and
      synthesize the results. For example: "Are our critical KEV vulns patched?" requires
      querying the SV for critical KEV vulns, then checking GitHub for patch repos.
    orchestration: |
      For vulnerability data questions, use vulnerability_sv first.
      For standards/definition questions, use vuln_standards_kb first.
      For patch/remediation status questions, use GitHub MCP tools.
      For combined questions, call vulnerability_sv first to identify CVEs, then
      check GitHub MCP for patch status on those specific CVEs.

sample_questions:
  - question: "What are the top 10 most exploitable critical vulnerabilities?"
  - question: "Have we pushed patches for the latest KEV critical vulnerabilities?"
  - question: "Which ATT&CK tactics are most associated with our critical vulns?"
  - question: "What is the difference between CVSS severity and EPSS probability?"
  - question: "Do we have a patch deployed for CVE-2026-31337?"

tools:
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "vulnerability_sv"
      description: "Queries structured vulnerability data including CVE facts, CVSS scores, EPSS probability, KEV status, CWE weaknesses, and ATT&CK tactics"
  - tool_spec:
      type: "cortex_search"
      name: "vuln_standards_kb"
      description: "Searches vulnerability standards documentation including NVD, CVSS, EPSS, KEV, CWE, and ATT&CK definitions"
      max_results: 5

tool_resources:
  vulnerability_sv:
    semantic_view: "SANDBOX.GDUMA.VULNERABILITY_INTELLIGENCE"
  vuln_standards_kb:
    search_service: "SANDBOX.GDUMA.VULN_STANDARDS_SEARCH"
    id_column: "document_name"
    title_column: "document_name"

mcp_servers:
  - server_spec:
      name: "SANDBOX.GDUMA.GITHUB_PATCH_REPOS"
$$;

-- Grant usage
GRANT USAGE ON AGENT VULN_INTELLIGENCE_AGENT TO ROLE ALL_AAI_ARCHITECTS;
