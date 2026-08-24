-- Semantic View: VULNERABILITY_INTELLIGENCE
-- One semantic view per business domain pattern
USE DATABASE SANDBOX;
USE SCHEMA GDUMA;

CREATE OR REPLACE SEMANTIC VIEW VULNERABILITY_INTELLIGENCE
  COMMENT = 'Comprehensive vulnerability intelligence semantic view covering CVE facts, EPSS probability, KEV exploitation, CWE weaknesses, and ATT&CK tactics.'
AS $$
name: VULNERABILITY_INTELLIGENCE
tables:
  - name: V_FACT_VULNERABILITY
    base_table:
      database: SANDBOX
      schema: GDUMA
      table: V_FACT_VULNERABILITY
    primary_key: CVE_ID
    dimensions:
      - name: CVE_ID
        expr: CVE_ID
        description: "Unique CVE identifier (e.g., CVE-2026-12345)"
        sample_values: ["CVE-2026-10520", "CVE-2026-20253", "CVE-2025-47029"]
      - name: SEVERITY_BAND
        expr: SEVERITY_BAND
        description: "CVSS severity classification: CRITICAL (9.0+), HIGH (7.0-8.9), MEDIUM (4.0-6.9), LOW (0.1-3.9), NONE"
        sample_values: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]
      - name: EPSS_BAND
        expr: EPSS_BAND
        description: "Exploit probability band based on EPSS percentile"
        sample_values: ["VERY HIGH", "HIGH", "MEDIUM", "LOW", "VERY LOW"]
      - name: IS_KNOWN_EXPLOITED
        expr: IS_KNOWN_EXPLOITED
        description: "Whether this CVE is in CISA KEV (confirmed exploited in the wild)"
        sample_values: ["true", "false"]
      - name: KEV_VENDOR
        expr: KEV_VENDOR
        description: "Vendor of the exploited product (from CISA KEV)"
        sample_values: ["Ivanti", "Splunk", "Oracle", "Cisco", "Microsoft"]
      - name: KEV_PRODUCT
        expr: KEV_PRODUCT
        description: "Product name from CISA KEV"
        sample_values: ["Connect Secure", "Splunk Enterprise", "WebLogic Server"]
      - name: KNOWN_RANSOMWARE_CAMPAIGN_USE
        expr: KNOWN_RANSOMWARE_CAMPAIGN_USE
        description: "Whether vulnerability is known to be used in ransomware campaigns"
        sample_values: ["Known", "Unknown"]
      - name: PUBLISHED_YEAR
        expr: PUBLISHED_YEAR
        description: "Year the CVE was published"
        sample_values: ["2026", "2025", "2024"]
      - name: PUBLISHED_QUARTER
        expr: PUBLISHED_QUARTER
        description: "Quarter the CVE was published"
        sample_values: ["1", "2", "3", "4"]
      - name: PUBLISHED_MONTH
        expr: PUBLISHED_MONTH
        description: "Month the CVE was published (1-12)"
      - name: KEV_REMEDIATION_OVERDUE
        expr: KEV_REMEDIATION_OVERDUE
        description: "Whether the KEV remediation due date has passed"
        sample_values: ["true", "false"]
      - name: VULN_STATUS
        expr: VULN_STATUS
        description: "NVD processing status"
        sample_values: ["Analyzed", "Modified", "Awaiting Analysis"]
    facts:
      - name: CVSS_V31_BASE_SCORE
        expr: CVSS_V31_BASE_SCORE
        description: "CVSS v3.1 base severity score (0-10). Measures technical severity, NOT exploit probability."
      - name: CVSS_V31_EXPLOITABILITY_SCORE
        expr: CVSS_V31_EXPLOITABILITY_SCORE
        description: "CVSS exploitability subscore"
      - name: CVSS_V31_IMPACT_SCORE
        expr: CVSS_V31_IMPACT_SCORE
        description: "CVSS impact subscore"
      - name: EPSS_SCORE
        expr: EPSS_SCORE
        description: "EPSS exploit probability (0-1). Measures likelihood of exploitation in next 30 days. Separate from CVSS severity."
      - name: EPSS_PERCENTILE
        expr: EPSS_PERCENTILE
        description: "EPSS relative ranking among all scored CVEs"

  - name: V_DIM_WEAKNESS
    base_table:
      database: SANDBOX
      schema: GDUMA
      table: V_DIM_WEAKNESS
    primary_key: CWE_ID
    dimensions:
      - name: CWE_ID
        expr: CWE_ID
        description: "CWE weakness identifier"
        sample_values: ["CWE-79", "CWE-89", "CWE-416", "CWE-787"]
      - name: WEAKNESS_NAME
        expr: WEAKNESS_NAME
        description: "Human-readable weakness name"
        sample_values: ["Cross-site Scripting", "SQL Injection", "Use After Free"]
      - name: ABSTRACTION
        expr: ABSTRACTION
        description: "CWE abstraction level"
        sample_values: ["Base", "Class", "Variant", "Pillar"]

  - name: V_CVE_ATTACK_TACTICS
    base_table:
      database: SANDBOX
      schema: GDUMA
      table: V_CVE_ATTACK_TACTICS
    dimensions:
      - name: TECHNIQUE_ID
        expr: TECHNIQUE_ID
        description: "MITRE ATT&CK technique identifier"
        sample_values: ["T1190", "T1059", "T1068", "T1566.002"]
      - name: TECHNIQUE_NAME
        expr: TECHNIQUE_NAME
        description: "ATT&CK technique name"
        sample_values: ["Exploit Public-Facing Application", "Spearphishing Link"]
      - name: TACTIC
        expr: TACTIC
        description: "ATT&CK tactic category"
        sample_values: ["initial-access", "execution", "privilege-escalation", "credential-access"]

  - name: V_PHISHING_RELEVANCE
    base_table:
      database: SANDBOX
      schema: GDUMA
      table: V_PHISHING_RELEVANCE
    dimensions:
      - name: PHISHING_CATEGORY
        expr: PHISHING_CATEGORY
        description: "Classification of phishing relevance"
        sample_values: ["DIRECT_PHISHING", "PHISHING_ENABLER"]

relationships:
  - name: ATTACK_TO_VULN
    left_table: V_CVE_ATTACK_TACTICS
    right_table: V_FACT_VULNERABILITY
    join_columns:
      - left_column: CVE_ID
        right_column: CVE_ID
    relationship_type: many_to_one
  - name: PHISHING_TO_VULN
    left_table: V_PHISHING_RELEVANCE
    right_table: V_FACT_VULNERABILITY
    join_columns:
      - left_column: CVE_ID
        right_column: CVE_ID
    relationship_type: many_to_one

metrics:
  - name: VULNERABILITY_COUNT
    expr: COUNT(DISTINCT V_FACT_VULNERABILITY.CVE_ID)
    description: "Total distinct vulnerabilities"
  - name: AVG_CVSS
    expr: AVG(V_FACT_VULNERABILITY.CVSS_V31_BASE_SCORE)
    description: "Average CVSS severity score"
  - name: AVG_EPSS
    expr: AVG(V_FACT_VULNERABILITY.EPSS_SCORE)
    description: "Average EPSS exploit probability"
  - name: MAX_CVSS
    expr: MAX(V_FACT_VULNERABILITY.CVSS_V31_BASE_SCORE)
    description: "Worst CVSS severity in set"
  - name: MAX_EPSS
    expr: MAX(V_FACT_VULNERABILITY.EPSS_SCORE)
    description: "Highest exploit probability in set"
$$;
