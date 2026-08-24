"""Ingest NVD CVEs from the NVD 2.0 API (recent 90 days)."""
import os
import sys
import json
import time
import pathlib
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
PAGE_SIZE = 2000
DAYS_BACK = 30


def fetch_nvd_cves():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=DAYS_BACK)

    params = {
        "pubStartDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
        "pubEndDate": end_date.strftime("%Y-%m-%dT23:59:59.999"),
        "resultsPerPage": PAGE_SIZE,
        "startIndex": 0,
    }

    all_cves = []
    total = None

    while True:
        print(f"  Fetching from index {params['startIndex']}...")
        resp = requests.get(NVD_API, params=params, timeout=30)
        if resp.status_code == 403:
            print("  Rate limited, waiting 30s...")
            time.sleep(30)
            continue
        resp.raise_for_status()
        data = resp.json()

        if total is None:
            total = data.get("totalResults", 0)
            print(f"  Total CVEs to fetch: {total}")

        vulnerabilities = data.get("vulnerabilities", [])
        all_cves.extend(vulnerabilities)

        if len(all_cves) >= total:
            break

        params["startIndex"] += PAGE_SIZE
        time.sleep(6)

    return all_cves


def parse_cve(item: dict) -> dict:
    cve = item.get("cve", {})
    cve_id = cve.get("id", "")
    source = cve.get("sourceIdentifier", "")
    published = cve.get("published", "")
    modified = cve.get("lastModified", "")
    status = cve.get("vulnStatus", "")

    descriptions = cve.get("descriptions", [])
    desc_en = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

    metrics = cve.get("metrics", {})
    cvss31 = metrics.get("cvssMetricV31", [{}])
    cvss_data = cvss31[0].get("cvssData", {}) if cvss31 else {}
    exploitability = cvss31[0].get("exploitabilityScore") if cvss31 else None
    impact = cvss31[0].get("impactScore") if cvss31 else None

    weaknesses = cve.get("weaknesses", [])
    cwe_ids = []
    for w in weaknesses:
        for d in w.get("description", []):
            if d.get("value", "").startswith("CWE-"):
                cwe_ids.append(d["value"])

    configs = cve.get("configurations", [])
    cpe_list = []
    for cfg in configs:
        for node in cfg.get("nodes", []):
            for match in node.get("cpeMatch", []):
                cpe_list.append(match.get("criteria", ""))

    refs = cve.get("references", [])
    ref_list = [{"url": r.get("url"), "source": r.get("source")} for r in refs[:10]]

    return {
        "CVE_ID": cve_id,
        "SOURCE_IDENTIFIER": source,
        "PUBLISHED_DATE": published,
        "LAST_MODIFIED_DATE": modified,
        "VULN_STATUS": status,
        "DESCRIPTION": desc_en[:16000],
        "CVSS_V31_VECTOR": cvss_data.get("vectorString", ""),
        "CVSS_V31_BASE_SCORE": cvss_data.get("baseScore"),
        "CVSS_V31_SEVERITY": cvss_data.get("baseSeverity", ""),
        "CVSS_V31_EXPLOITABILITY_SCORE": exploitability,
        "CVSS_V31_IMPACT_SCORE": impact,
        "CWE_IDS": ", ".join(cwe_ids),
        "CPE_CRITERIA": ", ".join(cpe_list[:20]),
        "REFERENCES_JSON": json.dumps(ref_list),
    }


def main():
    print(f"Fetching NVD CVEs (last {DAYS_BACK} days)...")
    raw_cves = fetch_nvd_cves()
    print(f"  Fetched {len(raw_cves)} CVE records")

    rows = [parse_cve(item) for item in raw_cves]
    df = pd.DataFrame(rows)

    for col in ["PUBLISHED_DATE", "LAST_MODIFIED_DATE"]:
        df[col] = pd.to_datetime(df[col], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("TRUNCATE TABLE IF EXISTS RAW_NVD_CVES")
        print(f"Loading {len(df)} rows into RAW_NVD_CVES...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="RAW_NVD_CVES", quote_identifiers=False
        )
        print(f"  Success: {nrows} rows loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
