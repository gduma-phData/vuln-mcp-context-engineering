import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()


def get_snowflake_connection(role_override: str = None):
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    role = role_override or os.getenv("SNOWFLAKE_ROLE")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    db = os.getenv("SNOWFLAKE_DB")
    schema = os.getenv("SNOWFLAKE_SCHEMA")

    if not all([account, user, role, warehouse]):
        raise RuntimeError(
            "Missing required env vars: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE"
        )

    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "rsa_key.p8")
    if os.path.exists(private_key_path):
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        with open(private_key_path, "rb") as key:
            p_key = serialization.load_pem_private_key(
                key.read(), password=None, backend=default_backend()
            )
        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        kwargs = dict(
            account=_account_locator(account),
            user=user,
            role=role,
            warehouse=warehouse,
            database=db,
            schema=schema,
            private_key=pkb,
        )
        if "." in account:
            kwargs["host"] = _derive_host(account)
        return snowflake.connector.connect(**kwargs)

    kwargs = dict(
        account=_account_locator(account),
        user=user,
        role=role,
        warehouse=warehouse,
        database=db,
        schema=schema,
        authenticator="externalbrowser",
    )
    if "." in account:
        kwargs["host"] = _derive_host(account)
    return snowflake.connector.connect(**kwargs)


def _account_locator(account: str) -> str:
    if "." in account:
        return account.split(".")[0]
    return account


def _derive_host(account: str) -> str:
    return f"{account}.snowflakecomputing.com"
