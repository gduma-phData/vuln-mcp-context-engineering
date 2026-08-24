"""Ingest MITRE ATT&CK Enterprise techniques from STIX JSON."""
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

ATTACK_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def main():
    print("Fetching MITRE ATT&CK Enterprise data (STIX 2.1)...")
    resp = requests.get(ATTACK_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    objects = data.get("objects", [])
    techniques = [o for o in objects if o.get("type") == "attack-pattern" and not o.get("revoked")]
    print(f"  Retrieved {len(techniques)} active techniques")

    rows = []
    for t in techniques:
        ext_refs = t.get("external_references", [])
        technique_id = ""
        for ref in ext_refs:
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id", "")
                break

        tactics = [kc.get("phase_name", "") for kc in t.get("kill_chain_phases", [])]
        platforms = t.get("x_mitre_platforms", [])

        rows.append({
            "TECHNIQUE_ID": technique_id,
            "TECHNIQUE_NAME": t.get("name", ""),
            "DESCRIPTION": (t.get("description", "") or "")[:16000],
            "TACTICS": ", ".join(tactics),
            "PLATFORMS": ", ".join(platforms),
            "IS_SUBTECHNIQUE": "." in technique_id,
            "CREATED": t.get("created", "")[:10],
            "MODIFIED": t.get("modified", "")[:10],
        })

    df = pd.DataFrame(rows)
    print(f"  Parsed {len(df)} technique records")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("CREATE TABLE IF NOT EXISTS RAW_ATTACK_TECHNIQUES ("
                       "TECHNIQUE_ID VARCHAR, TECHNIQUE_NAME VARCHAR, DESCRIPTION VARCHAR, "
                       "TACTICS VARCHAR, PLATFORMS VARCHAR, IS_SUBTECHNIQUE BOOLEAN, "
                       "CREATED VARCHAR, MODIFIED VARCHAR, "
                       "INGESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP())")
        cursor.execute("TRUNCATE TABLE IF EXISTS RAW_ATTACK_TECHNIQUES")
        print(f"Loading {len(df)} rows into RAW_ATTACK_TECHNIQUES...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="RAW_ATTACK_TECHNIQUES", quote_identifiers=False
        )
        print(f"  Success: {nrows} rows loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
