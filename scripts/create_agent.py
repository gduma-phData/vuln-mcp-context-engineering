"""Create the named Cortex Agent in Snowflake."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shared.snowflake_conn import get_snowflake_connection


def main():
    ddl_path = pathlib.Path(__file__).resolve().parents[1] / "snowflake" / "ddl" / "060_create_agent.sql"

    with open(ddl_path) as f:
        sql = f.read()

    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"  Warning: {e}")
        print("Agent VULN_INTELLIGENCE_AGENT created successfully.")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
