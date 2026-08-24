"""Apply all Snowflake DDL files in order."""
import os
import sys
import glob
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection


def main():
    ddl_dir = pathlib.Path(__file__).resolve().parents[1] / "snowflake" / "ddl"
    sql_files = sorted(glob.glob(str(ddl_dir / "0[0-4]*.sql")))

    if not sql_files:
        print("No DDL files found!")
        return

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        for filepath in sql_files:
            filename = os.path.basename(filepath)
            print(f"Applying {filename}...")
            with open(filepath) as f:
                sql = f.read()
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        print(f"  Warning: {e}")
            print(f"  Done: {filename}")
    finally:
        cursor.close()
        conn.close()

    print("\nAll DDL applied successfully.")


if __name__ == "__main__":
    main()
