"""Named Cortex Agent client -- calls /api/v2/databases/{db}/schemas/{schema}/agents/{name}:run"""
import os
import sys
import json
import time
import hashlib
import pathlib
from base64 import b64encode
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
load_dotenv()

import jwt
import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def _load_private_key():
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "rsa_key.p8")
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


def _get_public_key_fingerprint(private_key):
    public_key_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    sha256 = hashlib.sha256(public_key_der).digest()
    return "SHA256:" + b64encode(sha256).decode("utf-8")


def _generate_jwt_token():
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    account_locator = account.split(".")[0].upper() if "." in account else account.upper()
    qualified_user = f"{account_locator}.{user.upper()}"

    private_key = _load_private_key()
    fingerprint = _get_public_key_fingerprint(private_key)

    now = int(time.time())
    payload = {
        "iss": f"{qualified_user}.{fingerprint}",
        "sub": qualified_user,
        "iat": now,
        "exp": now + 3600,
    }

    private_key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def _get_agent_endpoint():
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    host = f"{account}.snowflakecomputing.com"
    # Use ad-hoc endpoint for now; switch to named agent endpoint once MCP is configured:
    # return f"https://{host}/api/v2/databases/{db}/schemas/{schema}/agents/{agent_name}:run"
    return f"https://{host}/api/v2/cortex/agent:run"


def call_named_agent(question: str, role: str = None, thread_id: int = None, parent_message_id: int = None) -> dict:
    """Call Cortex Agent with SV + Search tools (uses ad-hoc endpoint; named agent for MCP)."""
    db = os.getenv("SNOWFLAKE_DB", "SANDBOX")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "GDUMA")
    model = os.getenv("CORTEX_MODEL", "openai-gpt-4.1")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "DEFAULT_USER_WH")

    token = _generate_jwt_token()
    endpoint = _get_agent_endpoint()

    request_body = {
        "model": model,
        "tools": [
            {"tool_spec": {"name": "vulnerability_sv", "type": "cortex_analyst_text_to_sql"}},
            {"tool_spec": {"name": "vuln_standards_kb", "type": "cortex_search"}},
        ],
        "tool_resources": {
            "vulnerability_sv": {"semantic_view": f"{db}.{schema}.VULNERABILITY_INTELLIGENCE"},
            "vuln_standards_kb": {
                "search_service": f"{db}.{schema}.VULN_STANDARDS_SEARCH",
                "id_column": "document_name",
                "title_column": "document_name",
            },
        },
        "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
    }
    if role:
        headers["X-Snowflake-Role"] = role
    if warehouse:
        headers["X-Snowflake-Warehouse"] = warehouse

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(endpoint, json=request_body, headers=headers)
            if response.status_code != 200:
                return {
                    "answer": f"Agent API error: HTTP {response.status_code}",
                    "tools_used": [],
                    "sql": "",
                    "data": [],
                    "error": response.text[:1000],
                }
            return _parse_agent_response(response)
    except Exception as e:
        return {
            "answer": f"Agent connection error: {str(e)}",
            "tools_used": [],
            "sql": "",
            "data": [],
            "error": str(e),
        }


def _parse_agent_response(response) -> dict:
    """Parse SSE response from named Cortex Agent."""
    text_parts = []
    sql = ""
    data = []
    tools_used = []

    for line in response.text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if "message" in event and "code" in event:
            return {
                "answer": f"Agent error: {event.get('message', '')}",
                "tools_used": [],
                "sql": "",
                "data": [],
                "error": event.get("message", ""),
            }

        delta = event.get("delta", {})
        for block in delta.get("content", []):
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_name = block.get("tool_use", {}).get("name", "")
                if tool_name:
                    tools_used.append(tool_name)
            elif block_type == "tool_results":
                tool_results = block.get("tool_results", {})
                tool_name = tool_results.get("name", "")
                if tool_name and tool_name not in tools_used:
                    tools_used.append(tool_name)
                for item in tool_results.get("content", []):
                    if item.get("type") == "json":
                        json_data = item.get("json", {})
                        if "sql" in json_data:
                            sql = json_data["sql"]
                        if "text" in json_data:
                            text_parts.append(json_data["text"])
                        if "results" in json_data:
                            raw = json_data["results"]
                            if isinstance(raw, list):
                                data = [{k: str(v) if v is not None else None for k, v in row.items()} for row in raw[:50]]
                    elif item.get("type") == "text":
                        text_parts.append(item.get("text", ""))

    full_text = "\n".join(t for t in text_parts if t).strip()

    if sql and not data:
        data = _execute_sql(sql)

    return {
        "answer": full_text or ("Query returned " + str(len(data)) + " rows." if data else "Agent returned empty response."),
        "tools_used": tools_used,
        "sql": sql,
        "data": data,
    }


def _execute_sql(sql: str) -> list:
    """Execute SQL returned by Cortex Agent."""
    from shared.snowflake_conn import get_snowflake_connection
    import snowflake.connector
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{k: str(v) if v is not None else None for k, v in row.items()} for row in rows[:50]]
    except Exception as e:
        print(f"SQL execution error: {e}")
        return []
    finally:
        conn.close()
