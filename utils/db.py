"""Databricks SQL connection and query helpers.

Works in Databricks Apps (automatic OAuth), notebooks (token), and
local development (PAT via env vars).
"""
import os
import streamlit as st
import pandas as pd
from databricks import sql as dbsql
from config import WAREHOUSE_HTTP_PATH


@st.cache_resource(ttl=1800)
def get_connection():
    """Return a reusable Databricks SQL connection."""
    server = os.getenv("DATABRICKS_SERVER_HOSTNAME", "")
    if not server:
        server = os.getenv("DATABRICKS_HOST", "")
    server = server.replace("https://", "").replace("http://", "").rstrip("/")
    token = os.getenv("DATABRICKS_TOKEN", "")

    kwargs: dict = {
        "server_hostname": server,
        "http_path": WAREHOUSE_HTTP_PATH,
    }
    if token:
        kwargs["access_token"] = token
    else:
        # Databricks Apps / SDK credential provider
        try:
            from databricks.sdk.core import Config
            cfg = Config()
            kwargs["server_hostname"] = cfg.host.replace("https://", "")
            kwargs["credentials_provider"] = lambda: cfg.authenticate()
        except Exception:
            pass
    return dbsql.connect(**kwargs)


def run_query(query: str) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(query)
        cols = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


def execute_statement(query: str) -> None:
    """Execute a DML statement (INSERT / DELETE / MERGE) without result."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(query)
