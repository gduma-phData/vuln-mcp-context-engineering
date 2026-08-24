USE DATABASE SANDBOX;
USE SCHEMA GDUMA;

CREATE OR REPLACE CORTEX SEARCH SERVICE VULN_STANDARDS_SEARCH
  ON chunk_text
  ATTRIBUTES section_title, document_name
  WAREHOUSE = DEFAULT_USER_WH
  TARGET_LAG = '1 hour'
  AS (
    SELECT
      chunk_text,
      document_name,
      section_title
    FROM KB_VULN_STANDARDS
  );
