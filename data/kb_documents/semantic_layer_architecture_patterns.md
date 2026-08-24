# Semantic Layer Architecture Patterns

## Anti-Pattern: One Semantic View Per Dashboard

Many organizations create a new semantic view for each reporting need. This leads to semantic sprawl: inconsistent metric definitions, duplicated logic, maintenance burden, and governance gaps. A dashboard showing "vulnerability count by severity" should NOT require its own semantic view separate from one showing "KEV remediation compliance by vendor."

## Best Practice: One Semantic View Per Business Domain

A vulnerability intelligence domain should have ONE comprehensive semantic view that covers all analytical use cases: triage, remediation tracking, weakness analysis, vendor exposure, compliance reporting, and executive dashboards. Multiple dashboards consume the same semantic view through different dimension slices and metric subsets.

## What a Reusable Semantic View Includes

1. ALL relevant fact and dimension tables in the domain (not just those needed for one report)
2. Comprehensive relationships between tables enabling any valid join path
3. Pre-defined metrics with business-approved definitions
4. Rich synonyms so different teams can use their own terminology
5. The CA extension with sample values for Cortex Analyst accuracy

## When to Extend vs Create New

EXTEND the existing semantic view when:
- A new dashboard needs columns from tables already in the SV
- New metrics are derivable from existing facts

Create a NEW semantic view only when:
- The domain is genuinely different (e.g., vulnerability intelligence vs HR analytics)
- Data governance requires strict separation
- The tables have no logical relationship to the existing model

## Relationship Design

The relationships clause is the backbone of a reusable semantic view. Define ALL valid join paths, not just those needed today. Name relationships descriptively (e.g., 'VULN_TO_WEAKNESS' not 'REL_1'). Cortex Analyst uses relationships to auto-generate JOINs -- missing relationships mean unanswerable questions.

## Metrics vs Raw Facts

Raw facts are individual numeric columns (cvss_base_score, epss_score). Metrics are pre-defined aggregation expressions (avg_cvss = AVG(cvss_base_score)). A reusable semantic view should expose BOTH: raw facts for flexible ad-hoc analysis, AND pre-defined metrics for consistent reporting.

## Coverage Assessment

When a user requests a new dashboard, the first question should be: "Can our existing semantic view answer this?" Assess coverage by checking:
1. Are the needed columns exposed as facts or dimensions?
2. Are the needed join paths defined in relationships?
3. Are the needed aggregations available as metrics?

If yes to all three, no new semantic view is needed -- just a new query against the existing one.
