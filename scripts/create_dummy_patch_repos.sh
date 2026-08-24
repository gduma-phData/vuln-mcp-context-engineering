#!/usr/bin/env bash
# Creates dummy GitHub repos simulating an infosec patch tracking system.
# Each repo represents a patch/remediation for a known vulnerability.
# The GitHub MCP connector will search these repos when the agent is asked about patches.

set -euo pipefail

GITHUB_ORG="gduma-phData"
REPO_PREFIX="patch"

# Realistic CVE + product combinations based on actual 2025-2026 KEV entries
declare -a PATCHES=(
  "CVE-2026-31337|Ivanti Connect Secure|RCE via authentication bypass|Critical|2026-08-15|deployed"
  "CVE-2026-28001|Splunk Enterprise|Remote code execution in SPL parsing|Critical|2026-07-22|deployed"
  "CVE-2026-22024|Oracle WebLogic Server|Deserialization vulnerability|Critical|2026-07-01|deployed"
  "CVE-2026-19843|Cisco IOS XE|Privilege escalation via web UI|High|2026-06-15|deployed"
  "CVE-2026-15502|Microsoft Exchange Server|SSRF leading to RCE|Critical|2026-06-01|in-review"
  "CVE-2026-14290|Palo Alto PAN-OS|Command injection in GlobalProtect|Critical|2026-05-20|deployed"
  "CVE-2026-12087|Fortinet FortiOS|Heap overflow in SSL-VPN|Critical|2026-05-10|deployed"
  "CVE-2026-11553|VMware vCenter|Authentication bypass|Critical|2026-04-28|deployed"
  "CVE-2026-10520|Apache Struts|OGNL injection|Critical|2026-04-15|in-review"
  "CVE-2026-09881|Atlassian Confluence|Template injection RCE|High|2026-04-01|deployed"
  "CVE-2026-08742|Citrix ADC|Buffer overflow|Critical|2026-03-20|deployed"
  "CVE-2026-07219|F5 BIG-IP|iControl REST vulnerability|Critical|2026-03-08|deployed"
  "CVE-2026-06555|SonicWall SMA|Path traversal|High|2026-02-25|deployed"
  "CVE-2026-05890|Juniper Junos|Improper authentication|High|2026-02-10|deployed"
  "CVE-2026-04321|Zyxel firewall|OS command injection|Critical|2026-01-28|deployed"
  "CVE-2026-03200|Progress MOVEit|SQL injection|Critical|2026-01-15|deployed"
  "CVE-2026-02777|Barracuda ESG|Remote command injection|Critical|2026-01-05|deployed"
  "CVE-2026-01443|Adobe ColdFusion|Deserialization|Critical|2025-12-20|deployed"
  "CVE-2025-47029|Ivanti EPMM|Authentication bypass|Critical|2025-12-01|deployed"
  "CVE-2025-44810|Zoho ManageEngine|RCE via SAML|Critical|2025-11-15|deployed"
  "CVE-2025-42558|Mitel MiCollab|Path traversal|High|2025-11-01|deployed"
  "CVE-2025-40123|Veeam Backup|Deserialization RCE|Critical|2025-10-20|deployed"
  "CVE-2025-38900|SolarWinds Orion|SQL injection|High|2025-10-05|deployed"
  "CVE-2025-37654|Zimbra Collaboration|XSS leading to RCE|Critical|2025-09-22|deployed"
  "CVE-2025-36001|GitLab CE/EE|SSRF via import|High|2025-09-10|in-review"
  "CVE-2025-34555|Kubernetes API Server|Privilege escalation|Critical|2025-08-28|deployed"
  "CVE-2025-33210|Redis|Heap buffer overflow|High|2025-08-15|deployed"
  "CVE-2025-31800|Grafana|Directory traversal|High|2025-08-01|deployed"
  "CVE-2025-30456|Jenkins|Arbitrary file read|High|2025-07-20|deployed"
  "CVE-2025-29111|HashiCorp Vault|Authentication bypass|Critical|2025-07-08|deployed"
  "CVE-2025-27890|Elastic Kibana|Prototype pollution|High|2025-06-25|deployed"
  "CVE-2025-26543|MongoDB|Privilege escalation|High|2025-06-12|deployed"
  "CVE-2025-25200|PostgreSQL|SQL injection in pg_dump|Critical|2025-05-30|deployed"
  "CVE-2025-24001|Nginx|HTTP request smuggling|High|2025-05-18|deployed"
  "CVE-2025-22777|Docker Engine|Container escape|Critical|2025-05-05|deployed"
  "CVE-2025-21340|Linux Kernel|Use-after-free|High|2025-04-22|deployed"
  "CVE-2025-20115|OpenSSL|Buffer overread|High|2025-04-10|deployed"
  "CVE-2025-19000|Apache Log4j|JNDI injection variant|Critical|2025-03-28|deployed"
  "CVE-2025-17650|Spring Framework|SpEL injection|Critical|2025-03-15|deployed"
  "CVE-2025-16333|Node.js|HTTP header injection|High|2025-03-01|deployed"
  "CVE-2025-15100|Python pip|Arbitrary code execution|High|2025-02-18|deployed"
  "CVE-2025-14001|Terraform|Provider credential leak|High|2025-02-05|deployed"
  "CVE-2025-12890|AWS CLI|Credential exposure|Medium|2025-01-22|deployed"
  "CVE-2025-11555|npm registry|Supply chain injection|Critical|2025-01-10|deployed"
  "CVE-2025-10200|PyPI|Typosquatting via namespace|High|2024-12-28|deployed"
  "CVE-2024-99001|Chromium|V8 type confusion|Critical|2024-12-15|deployed"
  "CVE-2024-88555|Firefox|Use-after-free in DOM|Critical|2024-12-01|deployed"
  "CVE-2024-77200|Safari WebKit|Memory corruption|Critical|2024-11-18|deployed"
  "CVE-2024-66001|Windows Print Spooler|Privilege escalation|High|2024-11-05|deployed"
  "CVE-2024-55890|macOS Kernel|Sandbox escape|Critical|2024-10-22|deployed"
)

echo "Creating ${#PATCHES[@]} dummy patch repos under ${GITHUB_ORG}..."
echo ""

for entry in "${PATCHES[@]}"; do
  IFS='|' read -r cve product description severity patch_date status <<< "$entry"
  
  repo_name="${REPO_PREFIX}-${cve}"
  
  echo "Creating ${repo_name}..."
  
  # Create the repo (skip if already exists)
  if ! gh repo view "${GITHUB_ORG}/${repo_name}" &>/dev/null; then
    gh repo create "${GITHUB_ORG}/${repo_name}" \
      --public \
      --description "Patch: ${description} (${product})" \
      --clone=false 2>/dev/null || true
    
    # Create README via API
    readme_content=$(cat <<EOF
# Patch: ${cve}

## Vulnerability Details
- **CVE**: ${cve}
- **Product**: ${product}
- **Description**: ${description}
- **Severity**: ${severity}
- **CISA KEV**: Yes (confirmed exploited in the wild)

## Patch Status: $(echo "$status" | tr '[:lower:]' '[:upper:]')

| Field | Value |
|-------|-------|
| Patch Date | ${patch_date} |
| Status | ${status} |
| Deployed To | Production (all regions) |
| Validated By | SecOps Team |
| Rollback Plan | Yes (documented in RUNBOOK.md) |

## Remediation Steps
1. Applied vendor patch from ${product} security advisory
2. Validated in staging environment
3. Deployed to production via CI/CD pipeline
4. Confirmed remediation via vulnerability scan
5. Closed tracking ticket

## References
- [NVD Entry](https://nvd.nist.gov/vuln/detail/${cve})
- [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- Internal Ticket: VULN-$(echo $cve | grep -oP '\d+$')
EOF
)
    
    # Push README
    echo "$readme_content" | gh api "repos/${GITHUB_ORG}/${repo_name}/contents/README.md" \
      --method PUT \
      --field message="Initial patch documentation for ${cve}" \
      --field content="$(echo "$readme_content" | base64)" \
      2>/dev/null || true
    
    echo "  Created: ${repo_name} (${product}, ${status})"
  else
    echo "  Exists: ${repo_name} (skipped)"
  fi
  
  # Rate limit protection
  sleep 1
done

echo ""
echo "Done! Created patch repos for ${#PATCHES[@]} CVEs."
echo "The GitHub MCP connector will discover these repos when the agent searches for patch status."
