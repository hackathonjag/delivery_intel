"""AI similarity search across historical projects.

Primary: Databricks ai_similarity() SQL function.
Fallback: scikit-learn TF-IDF + cosine similarity.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Tuple

from utils.db import run_query, execute_statement
from config import TABLE_INTAKES, TABLE_MATCHES


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
# Primary: Databricks ai_similarity()
# ======================================================================
def _search_ai_similarity(search_text: str, top_k: int) -> pd.DataFrame:
    safe = search_text.replace("'", "''")[:4000]
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
    """Run a similarity search; returns (matches_df, method_used)."""
    if method in ("ai_similarity", "auto"):
        try:
            return _search_ai_similarity(search_text, top_k), "ai_similarity"
        except Exception as exc:
            if method == "ai_similarity":
                raise
            st.info(f"ai_similarity unavailable ({exc}); falling back to TF-IDF.")
    return _search_tfidf(search_text, top_k), "tfidf"


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
