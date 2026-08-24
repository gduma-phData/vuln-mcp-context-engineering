"""Ingest FIRST EPSS daily scores."""
import os
import sys
import pathlib
import gzip
import io
import requests
import pandas as pd
from datetime import date
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

EPSS_URL = "https://epss.cyentia.com/epss_scores-current.csv.gz"


def main():
    print("Fetching EPSS scores (latest)...")
    resp = requests.get(EPSS_URL, timeout=60)
    resp.raise_for_status()

    decompressed = gzip.decompress(resp.content)
    lines = decompressed.decode("utf-8").splitlines()

    # First line is a comment with the date: #model_version:...,score_date:YYYY-MM-DD
    header_line = lines[0]
    score_date = date.today()
    if "score_date:" in header_line:
        score_date_str = header_line.split("score_date:")[1].strip().rstrip(",")
        score_date = pd.to_datetime(score_date_str).date()

    csv_data = "\n".join(lines[1:])
    df = pd.read_csv(io.StringIO(csv_data))

    df.columns = [c.strip().upper() for c in df.columns]
    df = df.rename(columns={"CVE": "CVE_ID", "EPSS": "EPSS_SCORE"})
    df["SCORE_DATE"] = score_date
    df = df[["CVE_ID", "EPSS_SCORE", "PERCENTILE", "SCORE_DATE"]]

    print(f"  Retrieved {len(df)} EPSS scores for {score_date}")

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DB')}")
        cursor.execute(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')}")
        cursor.execute("TRUNCATE TABLE IF EXISTS RAW_EPSS_SCORES")
        print(f"Loading {len(df)} rows into RAW_EPSS_SCORES...")
        success, nchunks, nrows, _ = write_pandas(
            conn=conn, df=df, table_name="RAW_EPSS_SCORES", quote_identifiers=False
        )
        print(f"  Success: {nrows} rows loaded.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
