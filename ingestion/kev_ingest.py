"""Ingest CISA Known Exploited Vulnerabilities catalog."""
import os
import sys
import pathlib
import requests
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def main():
    print("Fetching CISA KEV catalog...")
    resp = requests.get(KEV_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    vulns = data["vulnerabilities"]
    print(f"  Retrieved {len(vulns)} KEV entries")

    rows = []
    for v in vulns:
        rows.append({
            "CVE_ID": v.get("cveID"),
            "VENDOR_PROJECT": v.get("vendorProject"),
            "PRODUCT": v.get("product"),
            "VULNERABILITY_NAME": v.get("vulnerabilityName"),
            "DATE_ADDED": v.get("dateAdded"),
            "SHORT_DESCRIPTION": v.get("shortDescription"),
            "REQUIRED_ACTION": v.get("requiredAction"),
            "DUE_DATE": v.get("dueDate"),
            "KNOWN_RANSOMWARE_CAMPAIGN_USE": v.get("knownRansomwareCampaignUse"),
            "NOTES": v.get("notes", ""),
            "CWES": str(v.get("cwes", [])),
        })

    df = pd.DataFrame(rows)
    df["DATE_ADDED"] = pd.to_datetime(df["DATE_ADDED"]).dt.strftime("%Y-%m-%d")
    df["DUE_DATE"] = pd.to_datetime(df["DUE_DATE"]).dt.strftime("%Y-%m-%d")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("TRUNCATE TABLE IF EXISTS RAW_CISA_KEV")
        print(f"Loading {len(df)} rows into RAW_CISA_KEV...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="RAW_CISA_KEV", quote_identifiers=False
        )
        print(f"  Success: {nrows} rows loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
