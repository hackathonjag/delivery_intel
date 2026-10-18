"""AI similarity search across historical projects.

Search priority ("auto" mode):
  1. Vector Search  —  VECTOR_SEARCH() against vs_project_corpus_idx
  2. ai_similarity  —  Databricks AI Functions SQL scalar
  3. TF-IDF         —  scikit-learn fallback (no infra needed)
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Tuple

from utils.db import run_query, execute_statement
from config import TABLE_INTAKES, TABLE_MATCHES, TABLE_CORPUS

# Vector Search index names (created by scripts/04_create_indexes.py)
VS_CORPUS_INDEX = "dpm_dev.mlops.vs_project_corpus_idx"
VS_INTAKE_INDEX = "dpm_dev.mlops.vs_project_intakes_idx"


# ======================================================================
# Build combined search text
# ======================================================================
def build_search_text(
    intake_row: pd.Series | None = None,
    transcript_context: str = "",
    free_text: str = "",
) -> str:
    """Merge intake fields, transcript discussion, and free-text input."""
    parts: list[str] = []
    if intake_row is not None:
        for col in [
            "project_name",
            "problem_statement_and_desired_outcome",
            "overall_scope",
            "affected_systems",
            "business_strategy",
            "request_category",
            "estimated_complexity",
            "known_business_risks",
            "known_business_dependencies",
        ]:
            val = intake_row.get(col, "")
            if val and str(val).strip():
                parts.append(str(val))
    if transcript_context.strip():
        parts.append(transcript_context)
    if free_text.strip():
        parts.append(free_text)
    return " ".join(parts)


# ======================================================================
# Method 1 (preferred): Vector Search via SQL VECTOR_SEARCH()
# ======================================================================
def _search_vector(search_text: str, top_k: int) -> pd.DataFrame:
    """Query the VS corpus index through the SQL warehouse."""
    safe = search_text.replace("'", "''")[:8000]
    query = f"""
    SELECT
        project_id   AS historical_project_id,
        project_name AS historical_project_name,
        ROUND(score * 100, 1) AS similarity_score,
        line_of_business,
        project_size AS estimated_complexity,
        workitem_tags AS affected_systems
    FROM VECTOR_SEARCH(
        index => '{VS_CORPUS_INDEX}',
        query => '{safe}',
        num_results => {top_k}
    )
    WHERE project_id LIKE 'HIST-%%'
    """
    return run_query(query)


# ======================================================================
# Method 2: Databricks ai_similarity()
# ======================================================================
def _search_ai_similarity(search_text: str, top_k: int) -> pd.DataFrame:
    safe = search_text.replace("'", "''")[:4000]

    # Try corpus table first (includes transcript + planview + tags)
    try:
        query = f"""
        SELECT
            project_id   AS historical_project_id,
            project_name AS historical_project_name,
            ROUND(ai_similarity('{safe}', search_text) * 100, 1)
                         AS similarity_score,
            workitem_tags AS affected_systems,
            line_of_business,
            project_size  AS estimated_complexity
        FROM {TABLE_CORPUS}
        WHERE project_id LIKE 'HIST-%%'
        ORDER BY similarity_score DESC
        LIMIT {top_k}
        """
        return run_query(query)
    except Exception:
        pass  # corpus table not yet created; fall back to intakes

    # Fallback: project_intakes only (no transcript content)
    query = f"""
    WITH historical AS (
        SELECT
            project_id,
            project_name,
            CONCAT_WS(' ',
                problem_statement_and_desired_outcome,
                overall_scope, affected_systems,
                request_category, estimated_complexity,
                line_of_business, business_strategy,
                known_business_risks
            ) AS project_text,
            affected_systems,
            line_of_business,
            estimated_complexity
        FROM {TABLE_INTAKES}
        WHERE project_id LIKE 'HIST-%%'
    )
    SELECT
        project_id   AS historical_project_id,
        project_name AS historical_project_name,
        ROUND(ai_similarity('{safe}', project_text) * 100, 1)
                     AS similarity_score,
        affected_systems,
        line_of_business,
        estimated_complexity
    FROM historical
    ORDER BY similarity_score DESC
    LIMIT {top_k}
    """
    return run_query(query)


# ======================================================================
# Fallback: TF-IDF + cosine similarity
# ======================================================================
def _search_tfidf(search_text: str, top_k: int) -> pd.DataFrame:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    # Try corpus table first (includes transcript + planview + tags)
    try:
        query = f"""
        SELECT
            project_id   AS historical_project_id,
            project_name AS historical_project_name,
            search_text  AS project_text,
            workitem_tags AS affected_systems,
            line_of_business,
            project_size  AS estimated_complexity
        FROM {TABLE_CORPUS}
        WHERE project_id LIKE 'HIST-%%'
        """
        df = run_query(query)
    except Exception:
        df = pd.DataFrame()  # corpus not available

    # Fallback: project_intakes only
    if df.empty:
        query = f"""
        SELECT
            project_id   AS historical_project_id,
            project_name AS historical_project_name,
            CONCAT_WS(' ',
                problem_statement_and_desired_outcome,
                overall_scope, affected_systems,
                request_category, estimated_complexity,
                line_of_business, business_strategy,
                known_business_risks
            ) AS project_text,
            affected_systems,
            line_of_business,
            estimated_complexity
        FROM {TABLE_INTAKES}
        WHERE project_id LIKE 'HIST-%%'
        """
        df = run_query(query)

    if df.empty:
        return df

    corpus = [search_text] + df["project_text"].tolist()
    vec = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf = vec.fit_transform(corpus)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    df["similarity_score"] = np.round(sims * 100, 1)
    df = df.sort_values("similarity_score", ascending=False).head(top_k)
    return df.drop(columns=["project_text"])


# ======================================================================
# Public entry point
# ======================================================================
def run_similarity_search(
    search_text: str,
    top_k: int = 5,
    method: str = "auto",
) -> Tuple[pd.DataFrame, str]:
    """Run a similarity search; returns (matches_df, method_used).

    Method priority for 'auto':
      vector_search -> ai_similarity -> tfidf
    """
    attempts: list[tuple[str, callable]] = []

    if method == "vector_search":
        attempts = [("vector_search", lambda: _search_vector(search_text, top_k))]
    elif method == "ai_similarity":
        attempts = [("ai_similarity", lambda: _search_ai_similarity(search_text, top_k))]
    elif method == "tfidf":
        attempts = [("tfidf", lambda: _search_tfidf(search_text, top_k))]
    else:  # auto
        attempts = [
            ("vector_search", lambda: _search_vector(search_text, top_k)),
            ("ai_similarity", lambda: _search_ai_similarity(search_text, top_k)),
            ("tfidf", lambda: _search_tfidf(search_text, top_k)),
        ]

    last_exc = None
    for name, fn in attempts:
        try:
            df = fn()
            if not df.empty:
                return df, name
        except Exception as exc:
            last_exc = exc
            if len(attempts) > 1:
                st.info(f"{name} unavailable ({exc}); trying next method.")
            else:
                raise
    # All methods exhausted
    return pd.DataFrame(), attempts[-1][0] if attempts else "none"


# ======================================================================
# Persist matches
# ======================================================================
def save_matches(
    target_id: str,
    target_name: str,
    matches: pd.DataFrame,
    method: str,
) -> int:
    """Write ranked matches to the similar_project_matches table."""
    safe_target = target_name.replace("'", "''")

    # Remove previous matches for this target
    try:
        execute_statement(
            f"DELETE FROM {TABLE_MATCHES} "
            f"WHERE target_project_id = '{target_id}'"
        )
    except Exception:
        pass

    written = 0
    for rank_idx, (_, row) in enumerate(matches.iterrows(), start=1):
        hist_name = str(row.get("historical_project_name", "")).replace("'", "''")
        score = row.get("similarity_score", 0)
        signals = "; ".join(
            filter(None, [
                str(row.get("affected_systems", "") or ""),
                str(row.get("line_of_business", "") or ""),
            ])
        ).replace("'", "''")
        diff = f"Historical complexity={row.get('estimated_complexity', 'N/A')}"
        expl = f"Matched via {method} (score {score})"

        sql = (
            f"INSERT INTO {TABLE_MATCHES} "
            f"(target_project_id, target_project_name, rank, "
            f" historical_project_id, historical_project_name, "
            f" similarity_score, matching_signals, difference_notes, explanation) "
            f"VALUES ("
            f"  '{target_id}', '{safe_target}', {rank_idx}, "
            f"  '{row.get('historical_project_id','')}', '{hist_name}', "
            f"  {score}, '{signals}', '{diff}', '{expl}')"
        )
        try:
            execute_statement(sql)
            written += 1
        except Exception as exc:
            st.warning(f"Row {rank_idx} write failed: {exc}")
    return written
