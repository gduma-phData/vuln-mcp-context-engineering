"""OAuth flow for GitHub MCP connector via Snowflake SYSTEM$ functions.

For external apps (not running inside Snowflake), the flow is:
1. Our app redirects user to GitHub OAuth authorize URL directly
2. GitHub redirects back to our callback with ?code=...&state=...
3. We call SYSTEM$FINISH_OAUTH_FLOW with the code+state to let Snowflake store the token
"""
import os
import sys
import pathlib
import secrets

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from shared.snowflake_conn import get_snowflake_connection


INTEGRATION_NAME = "github_mcp_api_integration"
GITHUB_CLIENT_ID = os.getenv("GITHUB_MCP_CLIENT_ID", "Iv23liyRuSENCxUvzaLu")
GITHUB_OAUTH_SCOPES = "repo read:org"

# In-memory state store (in production, use Redis or similar)
_oauth_states: dict[str, str] = {}


def start_oauth_flow(callback_url: str = None) -> dict:
    """Call SYSTEM$START_USER_OAUTH_FLOW to get the Snowflake-hosted authorization URL.
    
    The returned URL is hosted on Snowflake and requires the user to have an active
    Snowsight session in their browser. Snowflake handles the full OAuth round-trip:
    redirect to GitHub, capture the callback, exchange code for token, store token.
    """
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT SYSTEM$START_USER_OAUTH_FLOW('{INTEGRATION_NAME}')"
        )
        row = cursor.fetchone()
        snowflake_url = row[0] if row else None
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()

    if not snowflake_url:
        return {"status": "error", "error": "No authorization URL returned from Snowflake"}

    return {
        "status": "success",
        "authorization_url": snowflake_url,
    }


def finish_oauth_flow(query_string: str = "", code: str = "", state: str = "") -> dict:
    """Pass the GitHub OAuth callback query string to Snowflake via SYSTEM$FINISH_OAUTH_FLOW.
    
    Snowflake will exchange the code for an access token and store it for the user.
    Accepts either the full query_string or individual code/state parameters.
    """
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        # Use full query string if provided, otherwise build from code/state
        if not query_string:
            query_string = f"code={code}"
            if state:
                query_string += f"&state={state}"

        # Escape single quotes for SQL safety
        safe_qs = query_string.replace("'", "\\'")
        cursor.execute(
            f"SELECT SYSTEM$FINISH_OAUTH_FLOW('{safe_qs}')"
        )
        row = cursor.fetchone()
        if row and row[0]:
            import json
            try:
                result = json.loads(row[0])
                # Check for error indicators
                result_str = str(row[0]).lower()
                if "error" in result_str or "fail" in result_str:
                    return {"connected": False, "error": row[0]}
                return {"connected": True, **result}
            except (json.JSONDecodeError, TypeError):
                msg = str(row[0]).lower()
                if "error" in msg or "fail" in msg:
                    return {"connected": False, "error": row[0]}
                return {"connected": True, "message": row[0]}
        return {"connected": True, "message": "OAuth flow completed"}
    except Exception as e:
        error_str = str(e)
        if "access token request failed" in error_str.lower():
            return {"connected": False, "error": "GitHub rejected the authorization code. It may have expired -- please try again."}
        return {"connected": False, "error": error_str}
    finally:
        conn.close()


def check_oauth_status() -> dict:
    """Check if the current user has a valid OAuth token for the GitHub MCP integration."""
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()

        # Try SYSTEM$VERIFY_EXTERNAL_OAUTH_TOKEN
        try:
            cursor.execute(
                f"SELECT SYSTEM$VERIFY_EXTERNAL_OAUTH_TOKEN('{INTEGRATION_NAME}')"
            )
            row = cursor.fetchone()
            if row and row[0]:
                result_str = str(row[0]).lower()
                if "failed" in result_str or "invalid" in result_str:
                    return {"connected": False, "reason": "No valid GitHub token -- click Connect GitHub to authorize."}
                if "valid" in result_str or "success" in result_str:
                    return {"connected": True}
                return {"connected": False, "raw": row[0]}
        except Exception:
            pass

        # Try SYSTEM$CHECK_USER_OAUTH_STATUS
        try:
            cursor.execute(
                f"SELECT SYSTEM$CHECK_USER_OAUTH_STATUS('{INTEGRATION_NAME}')"
            )
            row = cursor.fetchone()
            if row and row[0]:
                import json
                try:
                    result = json.loads(row[0])
                    connected = result.get("status", "").lower() in ("connected", "valid", "active")
                    return {"connected": connected, **result}
                except (json.JSONDecodeError, TypeError):
                    result_str = str(row[0]).lower()
                    connected = "connected" in result_str or "valid" in result_str
                    return {"connected": connected, "raw": row[0]}
        except Exception:
            pass

        return {"connected": False, "error": "Unable to determine OAuth status."}
    finally:
        conn.close()


def validate_state(state: str) -> bool:
    """Validate that the OAuth state parameter matches one we issued."""
    return state in _oauth_states
