"""Ingest CWE weakness taxonomy from MITRE."""
import os
import sys
import pathlib
import zipfile
import io
import requests
import pandas as pd
from xml.etree import ElementTree
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

CWE_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"


def main():
    print("Fetching CWE weakness catalog...")
    resp = requests.get(CWE_URL, timeout=60)
    resp.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_name = [n for n in z.namelist() if n.endswith(".xml")][0]
    xml_content = z.read(xml_name)

    print("  Parsing XML...")
    root = ElementTree.fromstring(xml_content)
    ns = {"cwe": "http://cwe.mitre.org/cwe-7"}

    rows = []
    for weakness in root.findall(".//cwe:Weakness", ns):
        cwe_id = f"CWE-{weakness.get('ID')}"
        name = weakness.get("Name", "")
        abstraction = weakness.get("Abstraction", "")
        status = weakness.get("Status", "")

        desc_el = weakness.find("cwe:Description", ns)
        description = desc_el.text if desc_el is not None and desc_el.text else ""

        ext_desc_el = weakness.find("cwe:Extended_Description", ns)
        ext_desc = ""
        if ext_desc_el is not None:
            ext_desc = ElementTree.tostring(ext_desc_el, encoding="unicode", method="text").strip()

        related = []
        for rel in weakness.findall(".//cwe:Related_Weakness", ns):
            related.append(f"{rel.get('Nature')}:CWE-{rel.get('CWE_ID')}")

        rows.append({
            "CWE_ID": cwe_id,
            "NAME": name,
            "DESCRIPTION": description[:16000],
            "EXTENDED_DESCRIPTION": ext_desc[:16000],
            "ABSTRACTION": abstraction,
            "STATUS": status,
            "RELATED_WEAKNESSES": ", ".join(related[:20]),
        })

    df = pd.DataFrame(rows)
    print(f"  Parsed {len(df)} CWE weaknesses")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("TRUNCATE TABLE IF EXISTS RAW_CWE_WEAKNESSES")
        print(f"Loading {len(df)} rows into RAW_CWE_WEAKNESSES...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="RAW_CWE_WEAKNESSES", quote_identifiers=False
        )
        print(f"  Success: {nrows} rows loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
