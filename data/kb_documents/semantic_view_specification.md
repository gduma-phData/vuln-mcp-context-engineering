# Snowflake Semantic View Specification

## DDL Syntax

Snowflake Semantic Views define a governed semantic layer over physical tables. The DDL syntax is:

```sql
CREATE [OR REPLACE] SEMANTIC VIEW <name>
  TABLES (
    <db>.<schema>.<table1> PRIMARY KEY (<pk_col>),
    <db>.<schema>.<table2> PRIMARY KEY (<pk_col>)
  )
  RELATIONSHIPS (
    <rel_name> AS <table1>(<fk_col>) REFERENCES <table2>(<pk_col>)
  )
  FACTS (
    <table>.<column> AS <alias> WITH synonyms=('alt1','alt2') comment='description'
  )
  DIMENSIONS (
    <table>.<column> AS <alias> WITH synonyms=('alt1','alt2') comment='description'
  )
```

## Facts vs Dimensions

FACTS are numeric/measurable columns intended for aggregation (SUM, AVG, COUNT, MIN, MAX). Examples: revenue, score, count, duration.

DIMENSIONS are categorical/grouping columns used for filtering and GROUP BY. Examples: year, category, status, name. Date, string, and boolean columns are typically dimensions.

## Relationships

The RELATIONSHIPS clause defines how tables join. This enables Cortex Analyst to automatically generate correct JOINs when users ask questions spanning multiple tables. Missing relationships mean unanswerable questions.

Syntax: `REL_NAME AS TABLE1(FK_COL) REFERENCES TABLE2(PK_COL)`

Use bridge/junction tables for many-to-many relationships.

## Synonyms

The WITH clause supports synonyms that help Cortex Analyst understand alternative terminology:
`column_ref AS ALIAS WITH synonyms=('syn1','syn2') comment='description'`

Example: vulnerability_count might have synonyms ('vuln_count', 'cve_count', 'number_of_vulnerabilities').

## Best Practices for Vulnerability Semantic Views

1. Separate severity (CVSS) from probability (EPSS) from confirmed exploitation (KEV) as distinct facts/dimensions
2. Use the fact_vulnerability as the central fact table with relationships to weakness, product, and temporal dimensions
3. Expose EPSS_PERCENTILE as a dimension band, not a raw fact, for intuitive filtering
4. KEV status should be a boolean dimension (IS_KNOWN_EXPLOITED), not a fact
5. Include 3-5 representative sample values per dimension in the CA extension
