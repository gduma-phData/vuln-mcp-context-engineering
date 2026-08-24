"""Ingest vulnerability standards documentation into the KB table for Cortex Search."""
import os
import sys
import uuid
import pathlib
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150

KB_DOCUMENTS = [
    {
        "document_name": "NVD_National_Vulnerability_Database",
        "section_title": "NVD Overview and Data Sources",
        "chunks": [
            "The National Vulnerability Database (NVD) is the U.S. government repository of standards-based vulnerability management data. NVD is maintained by NIST (National Institute of Standards and Technology). NVD is the authoritative source for CVE enrichment data including CVSS severity scores, CWE weakness mappings, and CPE affected product configurations. NVD ingests CVE records from the CVE Program and enriches them with additional analysis.",
            "NVD provides the NVD REST API (version 2.0) for programmatic access to vulnerability data. The API returns CVE records in JSON format with fields including: descriptions, CVSS metrics (v2, v3.0, v3.1, v4.0), CWE weakness mappings, CPE applicability configurations, references, and vulnerability status. The API supports filtering by publication date, modification date, keyword, CVE ID, CWE ID, and CVSS severity.",
            "A CVE (Common Vulnerabilities and Exposures) is a unique identifier for a specific security vulnerability. The format is CVE-YYYY-NNNNN (e.g., CVE-2026-12345). CVE IDs are assigned by CVE Numbering Authorities (CNAs) and then enriched by NVD with scoring, classification, and affected product data. The CVE Program and NVD are complementary: CVE provides identification, NVD provides enrichment and analysis.",
            "NVD vulnerability status indicates the stage of NVD analysis: 'Received' (new, not yet analyzed), 'Awaiting Analysis' (queued), 'Undergoing Analysis' (in progress), 'Analyzed' (complete, scores assigned), 'Modified' (updated after initial analysis), 'Deferred' (will not be analyzed), 'Rejected' (invalid CVE). Only 'Analyzed' and 'Modified' CVEs have complete CVSS and CWE data.",
        ],
    },
    {
        "document_name": "CVSS_Specification_v3.1",
        "section_title": "CVSS Overview and Scoring",
        "chunks": [
            "The Common Vulnerability Scoring System (CVSS) is a framework for communicating the characteristics and severity of software vulnerabilities. CVSS captures the principal technical characteristics of software, hardware, and firmware vulnerabilities. Its output is a numerical score (0-10) reflecting severity, which can be translated into qualitative representations (None, Low, Medium, High, Critical). CVSS is NOT a measure of risk. CVSS does not factor in the probability that a vulnerability will be exploited. It measures technical severity only.",
            "CVSS Base Score reflects the intrinsic qualities of a vulnerability that are constant over time and across user environments. It is composed of two sub-scores: Exploitability (Attack Vector, Attack Complexity, Privileges Required, User Interaction) and Impact (Confidentiality, Integrity, Availability). A CVSS Base Score of 9.0-10.0 is Critical, 7.0-8.9 is High, 4.0-6.9 is Medium, 0.1-3.9 is Low.",
            "IMPORTANT SEMANTIC DISTINCTION: CVSS measures SEVERITY (how bad the vulnerability could be if exploited), NOT exploit probability (how likely it is to be exploited). For exploit probability, use EPSS. For confirmation of active exploitation in the wild, use CISA KEV. These three dimensions (severity, probability, known exploitation) are complementary and must not be conflated.",
            "The CVSS Temporal Metrics capture characteristics that change over time but not across environments: Exploit Code Maturity, Remediation Level, and Report Confidence. The Environmental Metrics allow customization based on the user's specific environment. In practice, most vulnerability databases report only the Base Score.",
            "CVSS v2, v3.0, v3.1, and v4.0 scoring systems are NOT interchangeable. A CVSS v2 score of 7.5 is NOT equivalent to a CVSS v3.1 score of 7.5. They use different formulas, different metric groups, and produce different score distributions. When comparing vulnerabilities, always use scores from the same CVSS version.",
        ],
    },
    {
        "document_name": "EPSS_Model_Documentation",
        "section_title": "Exploit Prediction Scoring System",
        "chunks": [
            "The Exploit Prediction Scoring System (EPSS) is a data-driven model that estimates the probability (0-1) that a software vulnerability will be exploited in the wild within the next 30 days. EPSS is published daily by FIRST (Forum of Incident Response and Security Teams). EPSS provides both a raw probability score and a percentile ranking relative to all scored CVEs.",
            "EPSS DOES NOT measure severity. It measures LIKELIHOOD of exploitation. A vulnerability with a low CVSS score (e.g., 3.5) can have a high EPSS score (e.g., 0.85) if exploit code is widely available and the vulnerability is actively being targeted. Conversely, a Critical CVSS vulnerability (9.8) may have very low EPSS (0.01) if it requires highly specific conditions to exploit.",
            "EPSS percentile indicates what proportion of all CVEs have a lower EPSS score. An EPSS percentile of 0.95 means the CVE has a higher predicted exploitation probability than 95% of all other CVEs. This is the recommended field for creating 'exploit likelihood bands' in analytics.",
            "Best practices for using EPSS in semantic models: Create bands based on percentile (not raw score). Recommended bands: Very High (>=95th), High (80-95th), Medium (50-80th), Low (20-50th), Very Low (<20th). EPSS should be a separate dimension from CVSS severity to avoid conflation.",
        ],
    },
    {
        "document_name": "CISA_KEV_Documentation",
        "section_title": "Known Exploited Vulnerabilities Catalog",
        "chunks": [
            "The CISA Known Exploited Vulnerabilities (KEV) Catalog is the authoritative source of vulnerabilities that have been exploited in the wild. Inclusion in KEV means there is reliable evidence of active exploitation. KEV is maintained by the Cybersecurity and Infrastructure Security Agency (CISA) of the United States government.",
            "KEV inclusion criteria: (1) The vulnerability has an assigned CVE ID, (2) There is reliable evidence that the vulnerability has been actively exploited in the wild, and (3) There is a clear remediation action available (patch, configuration change, or vendor guidance). KEV is NOT comprehensive of all exploited vulnerabilities; it represents confirmed cases with remediation paths.",
            "KEV provides: date_added (when CISA confirmed exploitation), due_date (remediation deadline for federal agencies), required_action (specific remediation guidance), and known_ransomware_campaign_use (Yes/Unknown). The due_date field is binding for US federal agencies under BOD 22-01 but serves as a strong prioritization signal for all organizations.",
            "SEMANTIC DISTINCTION: A vulnerability being in KEV means it IS being exploited (confirmed fact). A high EPSS score means it is LIKELY to be exploited (probability estimate). A high CVSS score means it COULD be severe IF exploited (technical potential). These represent past/present (KEV), future probability (EPSS), and theoretical impact (CVSS) respectively.",
            "When building a semantic model for vulnerability triage, KEV status should be a BOOLEAN dimension (is_known_exploited), NOT a metric. It represents a categorical fact, not a measurable quantity. The date_added and due_date fields are temporal dimensions for tracking remediation timelines.",
        ],
    },
    {
        "document_name": "CPE_Naming_Specification",
        "section_title": "Common Platform Enumeration",
        "chunks": [
            "The Common Platform Enumeration (CPE) is a structured naming scheme for information technology systems, software, and packages. CPE provides a standardized method of describing and identifying classes of applications, operating systems, and hardware devices. CPE names follow the format: cpe:2.3:part:vendor:product:version:update:edition:language:sw_edition:target_sw:target_hw:other.",
            "IMPORTANT: CPE matching is NOT the same as text search. To determine if a vulnerability affects a specific product, you MUST use CPE match criteria, NOT search the CVE description text for vendor/product names. The NVD provides structured CPE match data (cpe_match with criteria, versionStartIncluding, versionEndExcluding) for precise version-range matching.",
            "When building a semantic model, product/vendor identification should be derived from CPE data, NOT from CVE description text. The CPE fields in NVD data provide: vendor, product, version ranges, and platform specifics. A single CVE can affect multiple CPE entries (multiple products/versions).",
            "The CPE Dictionary is the official list of CPE names maintained by NVD. It maps structured CPE URIs to human-readable titles. When exposing 'vendor' and 'product' dimensions in a semantic view, extract them from CPE criteria rather than from KEV vendor_project/product fields (which are less standardized).",
        ],
    },
    {
        "document_name": "CWE_Weakness_Taxonomy",
        "section_title": "Common Weakness Enumeration",
        "chunks": [
            "The Common Weakness Enumeration (CWE) is a category system for hardware and software weaknesses and vulnerabilities. CWE classifies the TYPE or CLASS of vulnerability, while CVE identifies SPECIFIC instances. A single CWE (e.g., CWE-79: Cross-site Scripting) may correspond to thousands of individual CVEs.",
            "SEMANTIC DISTINCTION: CVE is a vulnerability INSTANCE (a specific bug in a specific product). CWE is a weakness CLASS (a category of bugs). When reporting 'vulnerabilities by type', you are grouping CVEs by their CWE mapping. Not all CVEs have CWE mappings; NVD assigns CWEs during enrichment but some remain unmapped (listed as NVD-CWE-noinfo or NVD-CWE-Other).",
            "CWE has hierarchical abstraction levels: Pillar (most abstract, e.g., CWE-284: Improper Access Control), Class (e.g., CWE-862: Missing Authorization), Base (e.g., CWE-639: Authorization Bypass Through User-Controlled Key), and Variant (most specific). For analytics, Base-level CWEs provide the most useful grouping granularity.",
            "A CVE can map to multiple CWEs. When counting vulnerabilities by weakness type, decide whether to count each CVE once (primary CWE only) or multiple times (all mapped CWEs). The recommended approach for a semantic model is to expose the CWE-to-CVE relationship as a bridge/junction, allowing both counts.",
        ],
    },
    {
        "document_name": "MITRE_ATTACK_Framework",
        "section_title": "ATT&CK Adversary Tactics and Techniques",
        "chunks": [
            "MITRE ATT&CK (Adversarial Tactics, Techniques, and Common Knowledge) is a globally-accessible knowledge base of adversary tactics and techniques based on real-world observations. ATT&CK describes HOW adversaries behave after gaining access -- what tactics they use (their goals) and what techniques they employ (their methods). ATT&CK is organized as a matrix of Tactics (columns) and Techniques (rows).",
            "ATT&CK Tactics represent the adversary's tactical goals -- the WHY of an attack step. The Enterprise ATT&CK tactics are: Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion (Stealth), Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, and Impact. A single technique may serve multiple tactics.",
            "ATT&CK Techniques represent HOW an adversary achieves a tactical goal. There are ~709 active techniques (e.g., T1055: Process Injection, T1078: Valid Accounts, T1190: Exploit Public-Facing Application). Techniques have sub-techniques for more specific variants. Each technique includes: description, platforms affected, detection methods, and mitigations.",
            "RELATIONSHIP TO VULNERABILITIES: ATT&CK does NOT directly map to CVEs. The linkage is indirect: CVE -> CWE (weakness type) -> CAPEC (attack pattern) -> ATT&CK Technique. In practice, this mapping is sparse. The most useful integration is at the TACTIC level: 'Initial Access' techniques often exploit public-facing vulnerabilities (T1190), making KEV vulnerabilities relevant to Initial Access defense. ATT&CK provides BEHAVIORAL context that complements the TECHNICAL context from CVSS/EPSS/KEV.",
            "In a semantic model, ATT&CK data serves as an optional enrichment dimension providing threat-behavior context. The primary use cases are: (1) Mapping vulnerability exploitation to adversary kill-chain stages, (2) Prioritizing remediation based on which tactics the organization is most exposed to, (3) Connecting vulnerability data to detection/response capabilities. ATT&CK techniques are available as STIX 2.1 JSON from the MITRE CTI GitHub repository.",
        ],
    },
    {
        "document_name": "Snowflake_Semantic_View_Specification",
        "section_title": "Semantic View DDL Syntax",
        "chunks": [
            "Snowflake Semantic Views define a governed semantic layer over physical tables. The DDL syntax is: CREATE [OR REPLACE] SEMANTIC VIEW <name> TABLES (...) [RELATIONSHIPS (...)] [FACTS (...)] [DIMENSIONS (...)]. Tables are referenced by fully-qualified name with PRIMARY KEY declarations. Relationships define joins between tables.",
            "The FACTS clause defines numeric/measurable columns. Syntax: TABLE_ALIAS.COLUMN as ALIAS [with synonyms=('alt1','alt2') comment='description']. Facts are intended for aggregation (SUM, AVG, COUNT). Examples: FACT_SALES.REVENUE as REVENUE with comment='Total revenue in USD'.",
            "The DIMENSIONS clause defines categorical/grouping columns. Same syntax as facts. Dimensions are used for filtering and GROUP BY operations. Examples: DIM_DATE.YEAR as YEAR with comment='Calendar year'. Date, string, and boolean columns are typically dimensions.",
            "The RELATIONSHIPS clause defines how tables join. Syntax: REL_NAME as TABLE1(FK_COL) references TABLE2(PK_COL). This enables Cortex Analyst to automatically generate correct JOINs when users ask questions spanning multiple tables.",
            "Best practices for vulnerability semantic views: (1) Separate severity (CVSS) from probability (EPSS) from confirmed exploitation (KEV) as distinct facts/dimensions. (2) Use the fact_vulnerability as the central fact table with relationships to weakness, product, and temporal dimensions. (3) Expose EPSS_PERCENTILE as a dimension band, not a raw fact, for intuitive filtering. (4) KEV status should be a boolean dimension (IS_KNOWN_EXPLOITED), not a fact.",
            "Semantic views support synonyms via the WITH clause: column_ref as ALIAS with synonyms=('syn1','syn2') comment='description'. Synonyms help Cortex Analyst understand alternative names users might use (e.g., synonyms for 'vulnerability_count' might include 'vuln_count', 'cve_count', 'number_of_vulnerabilities').",
        ],
    },
    {
        "document_name": "Vulnerability_Data_Model_Best_Practices",
        "section_title": "Semantic Modeling Patterns",
        "chunks": [
            "When modeling vulnerability data for analytics, the central fact table should be at CVE grain (one row per vulnerability). Enrich with: CVSS metrics (severity), EPSS scores (probability), KEV status (confirmed exploitation), CWE mappings (weakness type), and CPE matches (affected products). This star-schema pattern enables multi-dimensional analysis.",
            "Recommended dimension hierarchies: (1) Time: year > quarter > month > date, based on published_date. (2) Severity: severity_band (Critical/High/Medium/Low/None) derived from CVSS base score. (3) Exploit Likelihood: epss_band (Very High/High/Medium/Low/Very Low) derived from EPSS percentile. (4) Weakness: CWE abstraction > CWE category > specific CWE. (5) Product: vendor > product > version (from CPE).",
            "Common metric definitions for a vulnerability semantic model: vulnerability_count = COUNT(DISTINCT cve_id). critical_count = COUNT(DISTINCT cve_id) WHERE cvss >= 9.0. known_exploited_count = COUNT(DISTINCT cve_id) WHERE is_known_exploited = TRUE. high_epss_count = COUNT(DISTINCT cve_id) WHERE epss_percentile >= 0.80. avg_cvss = AVG(cvss_base_score). avg_epss = AVG(epss_score).",
            "Anti-patterns to avoid: (1) Using CVSS score as a proxy for exploit risk (use EPSS instead). (2) Text-searching CVE descriptions for product names (use CPE structured data). (3) Treating KEV as equivalent to 'critical CVSS' (many KEV entries have Medium CVSS scores). (4) Mixing CVSS versions in aggregate calculations. (5) Counting CVEs multiple times when they map to multiple CWEs without acknowledging the bridge relationship.",
        ],
    },
    {
        "document_name": "Semantic_Layer_Architecture_Patterns",
        "section_title": "Reusable Semantic View Design",
        "chunks": [
            "ANTI-PATTERN: One semantic view per dashboard. Many organizations create a new semantic view for each reporting need. This leads to semantic sprawl: inconsistent metric definitions, duplicated logic, maintenance burden, and governance gaps. A dashboard showing 'vulnerability count by severity' should NOT require its own semantic view separate from one showing 'KEV remediation compliance by vendor'.",
            "BEST PRACTICE: One semantic view per business domain. A vulnerability intelligence domain should have ONE comprehensive semantic view that covers all analytical use cases: triage, remediation tracking, weakness analysis, vendor exposure, compliance reporting, and executive dashboards. Multiple dashboards consume the same semantic view through different dimension slices and metric subsets.",
            "A reusable semantic view includes: (1) ALL relevant fact and dimension tables in the domain, not just those needed for one report. (2) Comprehensive relationships between tables, enabling any valid join path. (3) Pre-defined metrics with business-approved definitions (e.g., 'vulnerability_count' always means COUNT(DISTINCT cve_id), never COUNT(*)). (4) Rich synonyms so different teams can use their own terminology. (5) The CA extension with sample values for Cortex Analyst accuracy.",
            "WHEN TO EXTEND vs CREATE NEW: Extend the existing semantic view when a new dashboard needs columns from tables already in the SV, or needs new metrics derivable from existing facts. Create a NEW semantic view only when: (a) the domain is genuinely different (e.g., vulnerability intelligence vs. HR analytics), (b) data governance requires strict separation, or (c) the tables have no logical relationship to the existing model.",
            "RELATIONSHIP DESIGN: The relationships clause is the backbone of a reusable semantic view. Define ALL valid join paths, not just those needed today. Use bridge/junction tables for many-to-many relationships (e.g., CVE-to-CWE via a bridge view). Name relationships descriptively (e.g., 'VULN_TO_WEAKNESS' not 'REL_1'). Cortex Analyst uses relationships to auto-generate JOINs -- missing relationships mean unanswerable questions.",
            "METRICS vs RAW FACTS: Raw facts are individual numeric columns (cvss_base_score, epss_score). Metrics are pre-defined aggregation expressions (avg_cvss = AVG(cvss_base_score), vulnerability_count = COUNT(DISTINCT cve_id)). A reusable semantic view should expose BOTH: raw facts for flexible ad-hoc analysis, AND pre-defined metrics for consistent reporting. The metrics clause ensures every team uses the same calculation.",
            "THE CA EXTENSION: The 'with extension (CA=...)' clause provides sample values that dramatically improve Cortex Analyst's query generation accuracy. Without it, the LLM must guess valid column values. With it, queries like 'show me Critical vulnerabilities' correctly map to SEVERITY_BAND = 'CRITICAL' rather than trying CVSS_V31_SEVERITY = 'critical'. Always include 3-5 representative sample values per dimension.",
            "COVERAGE ASSESSMENT: When a user requests a new dashboard or report, the first question should be: 'Can our existing semantic view answer this?' Assess coverage by checking: (1) Are the needed columns exposed as facts or dimensions? (2) Are the needed join paths defined in relationships? (3) Are the needed aggregations available as metrics? If yes to all three, no new semantic view is needed -- just a new query against the existing one.",
        ],
    },
]


def build_chunks() -> list[dict]:
    all_chunks = []
    for doc in KB_DOCUMENTS:
        for i, chunk_text in enumerate(doc["chunks"]):
            all_chunks.append({
                "ID": str(uuid.uuid4()),
                "DOCUMENT_NAME": doc["document_name"],
                "SECTION_TITLE": doc["section_title"],
                "CHUNK_TEXT": chunk_text,
                "CHUNK_METADATA": f'{{"chunk_index": {i}, "document": "{doc["document_name"]}"}}',
            })
    return all_chunks


def main():
    print("Building KB chunks from vulnerability standards documentation...")
    chunks = build_chunks()
    print(f"  Generated {len(chunks)} chunks from {len(KB_DOCUMENTS)} documents")

    df = pd.DataFrame(chunks)

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("TRUNCATE TABLE IF EXISTS KB_VULN_STANDARDS")
        print(f"Loading {len(df)} chunks into KB_VULN_STANDARDS...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="KB_VULN_STANDARDS", quote_identifiers=False
        )
        print(f"  Success: {nrows} chunks loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
