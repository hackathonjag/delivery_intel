"""Project Intake Workflow — Streamlit App.

Processes new IT project intakes through a 4-step workflow:
  1. Intake Details   — view or enter project metadata
  2. RAM Transcript   — load a Resource Allocation Meeting transcript
  3. Similarity Search — AI search for comparable historical projects
  4. Estimates         — generate a starting estimate from matches

Designed for deployment as a Databricks App against the
"IT Project and Workforce Management" Genie Agent tables.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from config import (
    DEFAULT_PROJECT_ID, DEFAULT_PROJECT_NAME,
    TABLE_ESTIMATES, TABLE_ROLE_ESTIMATES, TABLE_WORKITEMS,
    TABLE_MATCHES, TABLE_ASSIGNMENTS, TABLE_APPROVALS,
    TABLE_INTAKES, TABLE_PLANVIEW, TABLE_CAPACITY,
    TRANSCRIPT_VOLUME,
)
from utils.db import run_query, execute_statement
from utils.transcript_parser import parse_transcript
from utils.ai_search import build_search_text, run_similarity_search, save_matches

# ======================================================================
# Page config
# ======================================================================
st.set_page_config(
    page_title="Project Intake Workflow",
    page_icon="\U0001F3D7",
    layout="wide",
)

st.title("\U0001F3D7\uFE0F  IT Project Intake Workflow")
st.caption(
    "Process a new project intake: search for historical matches, "
    "write results to Unity Catalog, and generate a starting estimate."
)

# ======================================================================
# Sidebar — Project Selection & Settings
# ======================================================================
with st.sidebar:
    st.header("Project")
    project_id = st.text_input("Project ID", value=DEFAULT_PROJECT_ID)
    project_name = st.text_input("Project Name", value=DEFAULT_PROJECT_NAME)

    st.divider()
    st.header("Search Settings")
    search_method = st.selectbox(
        "Similarity method",
        ["auto", "vector_search", "ai_similarity", "tfidf"],
        help="auto tries vector_search -> ai_similarity -> TF-IDF.",
    )
    top_k = st.slider("Top-K matches", min_value=3, max_value=10, value=5)

    st.divider()
    st.caption("Warehouse: OPM Queries")
    st.caption("Catalog: dpm_dev.mlops")


# ======================================================================
# Helper loaders (cached per project)
# ======================================================================
@st.cache_data(ttl=300)
def load_estimate(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT * FROM {TABLE_ESTIMATES} WHERE project_id = '{pid}'"
    )

@st.cache_data(ttl=300)
def load_role_estimates(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT role, p50_hours, p80_hours, actual_hours, average_fte, "
        f"skill_level, allocation_note "
        f"FROM {TABLE_ROLE_ESTIMATES} WHERE project_id = '{pid}'"
    )

@st.cache_data(ttl=300)
def load_workitems(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT workitem_id, title, workitemtype, state, "
        f"scheduling_effort, tags "
        f"FROM {TABLE_WORKITEMS} WHERE prjnumber = '{pid}' "
        f"ORDER BY workitemtype, workitem_id"
    )

@st.cache_data(ttl=300)
def load_matches(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT * FROM {TABLE_MATCHES} "
        f"WHERE target_project_id = '{pid}' ORDER BY rank"
    )

@st.cache_data(ttl=300)
def load_assignments(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT resource_name, role, planned_hours, allocation_percent, "
        f"availability_at_start, capacity_conflict, constraint_note "
        f"FROM {TABLE_ASSIGNMENTS} WHERE project_id = '{pid}'"
    )

@st.cache_data(ttl=300)
def load_intake(pid: str) -> pd.DataFrame:
    return run_query(
        f"SELECT * FROM {TABLE_INTAKES} WHERE project_id = '{pid}'"
    )

@st.cache_data(ttl=600)
def list_transcripts() -> pd.DataFrame:
    return run_query(f"LIST '{TRANSCRIPT_VOLUME}/'")

@st.cache_data(ttl=600)
def read_transcript_file(path: str) -> str:
    df = run_query(
        f"SELECT value FROM read_files('{path}', format => 'text')"
    )
    return "\n".join(df["value"].tolist()) if not df.empty else ""


# ======================================================================
# TABS
# ======================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "\U0001F4CB Intake Details",
    "\U0001F399\uFE0F RAM Transcript",
    "\U0001F50D Similarity Search",
    "\U0001F4CA Estimates & Workflow",
])

# ------------------------------------------------------------------
# TAB 1 — Intake Details
# ------------------------------------------------------------------
with tab1:
    st.subheader("Project Overview")

    est_df = load_estimate(project_id)
    intake_df = load_intake(project_id)

    if not est_df.empty:
        e = est_df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("P50 Hours", f"{e.get('p50_hours', 'N/A'):,}")
        c2.metric("P80 Hours", f"{e.get('p80_hours', 'N/A'):,}")
        c3.metric("Duration", f"{e.get('duration_weeks', '?')} weeks")
        c4.metric("Confidence", f"{e.get('confidence_score', '?')}")

        with st.expander("Estimate detail", expanded=False):
            st.dataframe(est_df, use_container_width=True)
    else:
        st.info("No estimate record found. Run Similarity Search to generate one.")

    if not intake_df.empty:
        row = intake_df.iloc[0]
        with st.expander("Intake form fields", expanded=True):
            for col in [
                "problem_statement_and_desired_outcome",
                "overall_scope", "affected_systems",
                "business_strategy", "estimated_complexity",
                "request_category", "line_of_business",
                "known_business_risks", "known_business_dependencies",
            ]:
                val = row.get(col, "")
                if val and str(val).strip():
                    st.markdown(f"**{col.replace('_', ' ').title()}**")
                    st.write(str(val))
    else:
        st.info(
            "No intake record in project_intakes for this ID. "
            "Enter context via the free-text field or RAM Transcript tab."
        )

    # Resource assignments
    asgn = load_assignments(project_id)
    if not asgn.empty:
        st.subheader("Resource Assignments")
        st.dataframe(asgn, use_container_width=True)

# ------------------------------------------------------------------
# TAB 2 — RAM Transcript
# ------------------------------------------------------------------
with tab2:
    st.subheader("Resource Allocation Meeting Transcript")
    st.markdown(
        "Load a RAM call transcript to extract context for the similarity search. "
        "Transcripts are stored in the UC Volume or can be pasted directly."
    )

    input_mode = st.radio(
        "Input mode", ["Select from Volume", "Paste text"], horizontal=True
    )

    transcript_text = ""

    if input_mode == "Select from Volume":
        try:
            files_df = list_transcripts()
            if not files_df.empty:
                names = files_df["name"].tolist()
                selected = st.selectbox("Select transcript", names)
                if selected and st.button("Load transcript"):
                    path = f"{TRANSCRIPT_VOLUME}/{selected}"
                    transcript_text = read_transcript_file(path)
                    st.session_state["transcript_text"] = transcript_text
            else:
                st.warning("No files found in the transcript volume.")
        except Exception as exc:
            st.error(f"Could not list transcripts: {exc}")
    else:
        transcript_text = st.text_area(
            "Paste transcript markdown", height=300,
            placeholder="# Resource Allocation Meeting (RAM) - New Project Intake\n...",
        )
        if transcript_text:
            st.session_state["transcript_text"] = transcript_text

    # Use previously loaded transcript if available
    transcript_text = st.session_state.get("transcript_text", transcript_text)

    if transcript_text:
        parsed = parse_transcript(transcript_text)
        st.session_state["parsed_transcript"] = parsed

        st.success(
            f"Parsed: **{parsed.project_name}** ({parsed.project_id}) "
            f"| {parsed.meeting_date}"
        )
        st.markdown(f"**Decision:** {parsed.decision}")

        col_a, col_b = st.columns(2)
        with col_a:
            with st.expander("Participants", expanded=False):
                if parsed.participants:
                    st.table(pd.DataFrame(parsed.participants))
        with col_b:
            with st.expander("Sections", expanded=False):
                for sec in parsed.sections:
                    st.markdown(f"**{sec.time} — {sec.title}**")
                    st.write(sec.content[:500])

        with st.expander("Search context extracted", expanded=False):
            st.text(parsed.search_context[:2000])

# ------------------------------------------------------------------
# TAB 3 — Similarity Search
# ------------------------------------------------------------------
with tab3:
    st.subheader("AI Similarity Search")
    st.markdown(
        "Combine intake fields, RAM transcript, and free-text to find "
        "the most comparable historical projects."
    )

    free_text = st.text_area(
        "Additional search context (optional)",
        placeholder="e.g. AI/ML platform, real-time scoring, multi-system integration...",
        height=100,
    )

    # Build search text
    intake_row = None
    intake_df = load_intake(project_id)
    if not intake_df.empty:
        intake_row = intake_df.iloc[0]

    transcript_ctx = ""
    parsed_t = st.session_state.get("parsed_transcript")
    if parsed_t:
        transcript_ctx = parsed_t.search_context

    search_text = build_search_text(
        intake_row=intake_row,
        transcript_context=transcript_ctx,
        free_text=free_text or project_name,
    )

    with st.expander("Combined search text", expanded=False):
        st.text(search_text[:3000])

    col1, col2 = st.columns([1, 3])
    with col1:
        run_search = st.button(
            "\U0001F50E Run Search", type="primary", use_container_width=True
        )

    if run_search:
        with st.spinner("Searching historical projects..."):
            matches_df, method_used = run_similarity_search(
                search_text, top_k=top_k, method=search_method
            )
        st.session_state["matches_df"] = matches_df
        st.session_state["method_used"] = method_used

    matches_df = st.session_state.get("matches_df")
    method_used = st.session_state.get("method_used", "")

    if matches_df is not None and not matches_df.empty:
        st.success(
            f"Found {len(matches_df)} matches via **{method_used}**"
        )
        st.dataframe(
            matches_df[
                ["historical_project_id", "historical_project_name",
                 "similarity_score", "line_of_business",
                 "estimated_complexity"]
            ].reset_index(drop=True),
            use_container_width=True,
        )

        # Bar chart
        fig = px.bar(
            matches_df,
            x="historical_project_name",
            y="similarity_score",
            color="similarity_score",
            labels={"similarity_score": "Score",
                    "historical_project_name": "Project"},
            title="Similarity Scores",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Save button
        if st.button(
            f"\U0001F4BE Save matches to {TABLE_MATCHES}",
            type="secondary",
        ):
            with st.spinner("Writing to Unity Catalog..."):
                n = save_matches(
                    target_id=project_id,
                    target_name=project_name,
                    matches=matches_df,
                    method=method_used,
                )
            st.success(f"Wrote {n} matches for {project_id}.")
            st.cache_data.clear()

    # Show existing saved matches
    existing = load_matches(project_id)
    if not existing.empty:
        with st.expander(
            f"Saved matches in {TABLE_MATCHES} ({len(existing)} rows)",
            expanded=False,
        ):
            st.dataframe(existing, use_container_width=True)

# ------------------------------------------------------------------
# TAB 4 — Estimates & Workflow
# ------------------------------------------------------------------
with tab4:
    st.subheader("Estimate Summary")

    est_df = load_estimate(project_id)
    if est_df.empty:
        st.warning("No estimate found for this project.")
    else:
        e = est_df.iloc[0]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("P50 Hours", f"{e.get('p50_hours', 0):,}")
        m2.metric("P80 Hours", f"{e.get('p80_hours', 0):,}")
        m3.metric("Duration", f"{e.get('duration_weeks', '?')} wks")
        m4.metric("Confidence", f"{e.get('confidence_score', 0):.0%}")
        m5.metric("Contingency", f"{e.get('contingency_percent', 0)}%")

        st.markdown(f"**Estimate basis:** {e.get('estimate_basis', '')}")
        st.markdown(f"**Assumptions:** {e.get('assumptions', '')}")
        st.markdown(f"**Primary risks:** {e.get('primary_risks', '')}")

    # ---- Role breakdown ----
    st.subheader("Role Breakdown")
    roles_df = load_role_estimates(project_id)
    if not roles_df.empty:
        st.dataframe(roles_df, use_container_width=True)
        fig_roles = px.bar(
            roles_df, x="role", y=["p50_hours", "p80_hours"],
            barmode="group",
            title="Effort by Role (P50 vs P80)",
            labels={"value": "Hours", "role": "Role"},
        )
        st.plotly_chart(fig_roles, use_container_width=True)
    else:
        st.info("No role estimates available.")

    # ---- Historical comparison ----
    st.subheader("Historical Comparison")
    saved_matches = load_matches(project_id)
    if not saved_matches.empty:
        hist_ids = saved_matches["historical_project_id"].tolist()
        ids_str = ",".join(f"'{h}'" for h in hist_ids)
        hist_est = run_query(
            f"SELECT project_id, project_name, project_size, "
            f"p50_hours, p80_hours, actual_hours, duration_weeks "
            f"FROM {TABLE_ESTIMATES} WHERE project_id IN ({ids_str})"
        )
        if not hist_est.empty:
            # Add current project row for comparison
            if not est_df.empty:
                cur = est_df[["project_id", "project_name", "project_size",
                              "p50_hours", "p80_hours", "actual_hours",
                              "duration_weeks"]].copy()
                cur["project_name"] = cur["project_name"] + " (CURRENT)"
                compare = pd.concat([cur, hist_est], ignore_index=True)
            else:
                compare = hist_est
            st.dataframe(compare, use_container_width=True)

            fig_cmp = px.bar(
                compare,
                x="project_name", y=["p50_hours", "p80_hours", "actual_hours"],
                barmode="group",
                title="Current vs Historical Estimates",
            )
            st.plotly_chart(fig_cmp, use_container_width=True)
    else:
        st.info("Run Similarity Search first to populate comparisons.")

    # ---- Work items ----
    st.subheader("Azure DevOps Work Items")
    wi = load_workitems(project_id)
    if not wi.empty:
        type_counts = wi["workitemtype"].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Epics", int(type_counts.get("Epic", 0)))
        c2.metric("Features", int(type_counts.get("Feature", 0)))
        c3.metric("User Stories", int(type_counts.get("User Story", 0)))
        c4.metric("Tasks", int(type_counts.get("Task", 0)))

        total_effort = wi["scheduling_effort"].sum()
        st.metric("Total Scheduling Effort", f"{total_effort:,} pts")

        with st.expander("Work item details", expanded=False):
            st.dataframe(wi, use_container_width=True)
    else:
        st.info("No work items found for this project.")

    # ---- 7-Stage Lifecycle ----
    st.subheader("7-Stage Delivery Lifecycle")
    try:
        lifecycle = run_query(f"""
        WITH e  AS (SELECT * FROM {TABLE_ESTIMATES}    WHERE project_id = '{project_id}'),
             a  AS (SELECT * FROM {TABLE_ASSIGNMENTS}  WHERE project_id = '{project_id}'),
             ap AS (SELECT * FROM {TABLE_APPROVALS}    WHERE project_id = '{project_id}'),
             sm AS (SELECT * FROM {TABLE_MATCHES}      WHERE target_project_id = '{project_id}' AND rank = 1)
        SELECT 1 AS stage, 'Estimate'          AS name,
               (SELECT CONCAT(MAX(estimate_status),' | P50 ',MAX(p50_hours),'h / P80 ',MAX(p80_hours),'h | confidence ',MAX(confidence_score),' | ',MAX(duration_weeks),' wks') FROM e) AS detail
        UNION ALL SELECT 2, 'Capacity',
               (SELECT CONCAT(COUNT_IF(capacity_conflict),' of ',COUNT(*),' assignments with capacity conflicts') FROM a)
        UNION ALL SELECT 3, 'Commit',
               (SELECT CONCAT(COUNT_IF(status='Approved'),' of ',COUNT(*),' approvals complete') FROM ap)
        UNION ALL SELECT 4, 'Sync',
               (SELECT CONCAT(COUNT(DISTINCT worker_id),' workers, ',SUM(planned_hours),' planned hours') FROM a)
        UNION ALL SELECT 5, 'Operational Block',
               (SELECT CONCAT(COUNT_IF(status<>'Approved'),' open gates') FROM ap)
        UNION ALL SELECT 6, 'Variance',
               (SELECT CASE WHEN MAX(actual_hours) IS NULL THEN 'No actuals yet' ELSE CONCAT(ROUND(100.0*(MAX(actual_hours)-MAX(p50_hours))/MAX(p50_hours),1),'%% vs P50') END FROM e)
        UNION ALL SELECT 7, 'Re-plan',
               (SELECT CONCAT('Closest match: ',MAX(historical_project_name),' (score ',MAX(similarity_score),')') FROM sm)
        ORDER BY stage
        """)
        if not lifecycle.empty:
            for _, row in lifecycle.iterrows():
                st.markdown(
                    f"**Stage {int(row['stage'])} — {row['name']}:** "
                    f"{row.get('detail', 'N/A')}"
                )
    except Exception as exc:
        st.warning(f"Could not load lifecycle: {exc}")
