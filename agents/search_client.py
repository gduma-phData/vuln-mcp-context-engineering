"""Cortex Search client for KB queries."""
import os
from dotenv import load_dotenv
from snowflake.core import Root
from shared.snowflake_conn import get_snowflake_connection

load_dotenv()


def search_kb(query: str, limit: int = 5) -> list[dict]:
    conn = get_snowflake_connection()
    try:
        root = Root(conn)
        db = os.getenv("SNOWFLAKE_DB")
        schema = os.getenv("SNOWFLAKE_SCHEMA")

        search_service = (
            root.databases[db]
            .schemas[schema]
            .cortex_search_services["VULN_STANDARDS_SEARCH"]
        )

        resp = search_service.search(
            query=query,
            columns=["chunk_text", "document_name", "section_title"],
            limit=limit,
        )

        results = []
        for row in resp.results:
            results.append({
                "text": row["chunk_text"],
                "source": row["document_name"],
                "section": row.get("section_title", ""),
            })
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []
    finally:
        conn.close()
