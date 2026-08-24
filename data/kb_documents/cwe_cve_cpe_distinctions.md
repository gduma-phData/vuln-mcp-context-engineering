# CWE and CVE: Weakness Classes vs Vulnerability Instances

## The Core Distinction

CVE is a vulnerability INSTANCE (a specific bug in a specific product). CWE is a weakness CLASS (a category of bugs). These are fundamentally different levels of abstraction.

A single CWE (e.g., CWE-79: Cross-site Scripting) may correspond to thousands of individual CVEs. When reporting "vulnerabilities by type," you are grouping CVEs by their CWE mapping.

## CWE Abstraction Hierarchy

CWE has hierarchical abstraction levels:
- Pillar: most abstract (e.g., CWE-284: Improper Access Control)
- Class: broader category (e.g., CWE-862: Missing Authorization)
- Base: specific weakness type (e.g., CWE-639: Authorization Bypass Through User-Controlled Key)
- Variant: most specific (particular manifestation)

For analytics, Base-level CWEs provide the most useful grouping granularity.

## CWE-to-CVE Mapping

Not all CVEs have CWE mappings. NVD assigns CWEs during enrichment but some remain unmapped (listed as NVD-CWE-noinfo or NVD-CWE-Other). A CVE can map to multiple CWEs.

When counting vulnerabilities by weakness type, decide whether to count each CVE once (primary CWE only) or multiple times (all mapped CWEs). The recommended approach for a semantic model is to expose the CWE-to-CVE relationship as a bridge/junction table allowing both counts.

## CPE: Product and Vendor Identification

The Common Platform Enumeration (CPE) provides structured product identification. IMPORTANT: CPE matching is NOT the same as text search. To determine if a vulnerability affects a specific product, you MUST use CPE match criteria, NOT search the CVE description text for vendor/product names.

When building a semantic model, product/vendor identification should be derived from CPE data, not from CVE description text or KEV vendor_project fields (which are less standardized). CPE format: cpe:2.3:part:vendor:product:version:update:edition:language:sw_edition:target_sw:target_hw:other.

## EPSS Percentile Bands

EPSS percentile indicates what proportion of all CVEs have a lower EPSS score. An EPSS percentile of 0.95 means the CVE has a higher predicted exploitation probability than 95% of all other CVEs.

Recommended bands for semantic models (based on percentile, not raw score):
- Very High: >= 95th percentile
- High: 80th-95th percentile
- Medium: 50th-80th percentile
- Low: 20th-50th percentile
- Very Low: < 20th percentile

EPSS should be a separate dimension from CVSS severity to avoid conflation. Create bands based on percentile not raw score for intuitive filtering.
