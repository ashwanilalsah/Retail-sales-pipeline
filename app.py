
import os
import sys
import json
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

st.set_page_config(
    page_title="RetailFlow | ETL Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Each browser session gets its own temporary output directory.
if "etl_temp_dir" not in st.session_state:
    st.session_state.etl_temp_dir = tempfile.mkdtemp(
        prefix="retailflow_"
    )

TEMP_DIR = Path(st.session_state.etl_temp_dir)
INPUT_DIR = TEMP_DIR / "input"
PROCESSED_DIR = TEMP_DIR / "processed"
REJECTED_DIR = TEMP_DIR / "rejected"

for folder in (INPUT_DIR, PROCESSED_DIR, REJECTED_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# Configure output paths before importing the existing pipeline.
os.environ["PROCESSED_PATH"] = str(PROCESSED_DIR)
os.environ["REJECTED_PATH"] = str(REJECTED_DIR)
os.environ["LOG_FILE"] = str(TEMP_DIR / "pipeline.jsonl")
os.environ["LOG_LEVEL"] = "INFO"

from src.pipeline import process_csv_file

# --------------------------------------------------
# 2. DARK THEME STYLING
# --------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: #0b1020;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #101729;
        border-right: 1px solid #263149;
    }

    [data-testid="stHeader"] {
        background: rgba(11, 16, 32, 0.9);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1450px;
    }

    .hero {
        padding: 25px 28px;
        border: 1px solid #293653;
        border-radius: 18px;
        background: linear-gradient(120deg, #17233d, #111827 65%, #172554);
        margin-bottom: 22px;
    }

    .hero-kicker {
        color: #93c5fd;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .hero h1 {
        color: #f8fafc;
        font-size: 32px;
        margin: 8px 0;
    }

    .hero p {
        color: #aab8ce;
        margin: 0;
        font-size: 14px;
    }

    .section-title {
        color: #f1f5f9;
        font-size: 20px;
        font-weight: 700;
        margin: 12px 0 14px 0;
    }

    .metric-card {
        background: #111a2d;
        border: 1px solid #293653;
        border-radius: 15px;
        padding: 18px;
        min-height: 125px;
    }

    .metric-label {
        color: #9caec8;
        font-size: 13px;
        font-weight: 600;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 30px;
        font-weight: 750;
        margin: 8px 0 4px 0;
    }

    .metric-note {
        color: #8294af;
        font-size: 12px;
    }

    .panel {
        background: #111a2d;
        border: 1px solid #293653;
        border-radius: 15px;
        padding: 18px;
    }

    .status-pill {
        display: inline-block;
        background: #12392f;
        color: #86efac;
        border: 1px solid #22634e;
        border-radius: 30px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 700;
    }

    div.stButton > button[kind="primary"] {
        background: #3b82f6;
        border: 1px solid #60a5fa;
        color: white;
        border-radius: 9px;
        font-weight: 700;
        min-height: 44px;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #2563eb;
        border-color: #93c5fd;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 9px;
        min-height: 42px;
    }

    div[data-testid="stMetric"] {
        background: #111a2d;
        border: 1px solid #293653;
        border-radius: 12px;
        padding: 14px;
    }

    hr {
        border-color: #293653;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def metric_card(label, value, note):
    """Render a styled dashboard metric."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value:,}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def percentage(part, total):
    return (part / total * 100) if total else 0.0


# --------------------------------------------------
# 3. SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown("## 📊 RetailFlow")
    st.caption("DATA ENGINEERING WORKSPACE")
    st.divider()

    st.markdown("### Pipeline")
    st.markdown("1. Upload source CSV")
    st.markdown("2. Validate records")
    st.markdown("3. Normalize accepted data")
    st.markdown("4. Export processing results")

    st.divider()
    st.markdown("### Runtime")
    st.markdown("**Engine:** Python ETL")
    st.markdown("**Storage:** Local files")
    st.markdown("**Database:** Not required")

    st.divider()
    st.caption("Retail Sales Pipeline · Portfolio Edition")


# --------------------------------------------------
# 4. HERO HEADER
# --------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">DATA QUALITY • ETL • ANALYTICS</div>
        <h1>Retail Sales Intelligence</h1>
        <p>
            Transform raw retail data into clean, validated datasets.
            Monitor pipeline outcomes and export your results.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 5. CSV UPLOAD AND PIPELINE EXECUTION
# --------------------------------------------------
st.markdown(
    '<div class="section-title">01 / Source Data</div>',
    unsafe_allow_html=True,
)

upload_col, info_col = st.columns([1.6, 1])

with upload_col:
    uploaded_file = st.file_uploader(
        "Upload a retail sales CSV file",
        type=["csv"],
        help="Choose a CSV file containing your retail sales records.",
    )

with info_col:
    st.markdown(
        """
        <div class="panel">
            <b>Supported input</b><br><br>
            CSV files<br>
            Local ETL processing<br>
            Cleaned CSV + rejected JSON
        </div>
        """,
        unsafe_allow_html=True,
    )

if uploaded_file is not None:
    st.caption(
        f"Selected: {uploaded_file.name} · "
        f"{uploaded_file.size / 1024:.1f} KB"
    )

    if st.button(
        "▶  Run ETL Pipeline",
        type="primary",
        use_container_width=True,
    ):
        try:
            safe_name = Path(uploaded_file.name).name
            input_path = INPUT_DIR / safe_name
            input_path.write_bytes(uploaded_file.getvalue())

            with st.spinner("Extracting, validating and transforming records..."):
                result = process_csv_file(input_path)

                cleaned_path = Path(result["cleaned_path"])
                rejected_path = Path(result["rejected_path"])

                cleaned_bytes = cleaned_path.read_bytes()
                rejected_bytes = rejected_path.read_bytes()

                # Keep file contents in session state for downloads.
                st.session_state.etl_result = result
                st.session_state.etl_cleaned_bytes = cleaned_bytes
                st.session_state.etl_rejected_bytes = rejected_bytes
                st.session_state.etl_cleaned_name = cleaned_path.name
                st.session_state.etl_rejected_name = rejected_path.name

            st.success("Pipeline execution completed successfully.")

        except Exception as exc:
            st.error(f"Pipeline failed: {type(exc).__name__}: {exc}")

# --------------------------------------------------
# 6. DASHBOARD RESULTS
# --------------------------------------------------
result = st.session_state.get("etl_result")

if result:
    input_count = result["input_count"]
    accepted_count = result["accepted_count"]
    rejected_count = result["rejected_count"]
    duplicate_count = result["duplicate_count"]

    st.divider()

    st.markdown(
        '<div class="section-title">02 / Pipeline Overview</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span class="status-pill">● SUCCESS — RUN COMPLETED</span>',
        unsafe_allow_html=True,
    )

    st.caption(f"Run ID: `{result['run_id']}`")

    k1, k2, k3, k4 = st.columns(4, gap="medium")

    with k1:
        metric_card("TOTAL INPUT", input_count, "Records read from source")

    with k2:
        metric_card("ACCEPTED", accepted_count, "Records passing validation")

    with k3:
        metric_card("REJECTED", rejected_count, "Records not accepted")

    with k4:
        metric_card("DUPLICATES", duplicate_count, "Duplicate records detected")

    st.markdown("")

    # Data quality rates
    accepted_rate = percentage(accepted_count, input_count)
    rejected_rate = percentage(rejected_count, input_count)

    quality_col, status_col = st.columns([1.3, 1], gap="large")

    with quality_col:
        st.markdown(
            '<div class="section-title">03 / Data Quality</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**Acceptance rate** · {accepted_rate:.1f}%"
        )
        st.progress(accepted_rate / 100)

        st.markdown(
            f"**Rejection rate** · {rejected_rate:.1f}%"
        )
        st.progress(rejected_rate / 100)

        st.caption(
            "Duplicate records are included in rejected records when "
            "the pipeline classifies them as rejected. These counts "
            "should not be added together."
        )

    with status_col:
        st.markdown(
            '<div class="section-title">Pipeline Health</div>',
            unsafe_allow_html=True,
        )

        checks = [
            ("Source file read", True),
            ("ETL execution completed", True),
            ("Cleaned output generated", bool(st.session_state.etl_cleaned_bytes)),
            ("Rejected output generated", bool(st.session_state.etl_rejected_bytes)),
        ]

        for label, passed in checks:
            icon = "✅" if passed else "❌"
            st.markdown(f"{icon}  {label}")

    # Charts
    st.divider()
    st.markdown(
        '<div class="section-title">04 / Record Analytics</div>',
        unsafe_allow_html=True,
    )

    chart_col1, chart_col2 = st.columns(2, gap="large")

    chart_data = pd.DataFrame(
        {
            "Category": ["Accepted", "Rejected", "Duplicates"],
            "Records": [
                accepted_count,
                rejected_count,
                duplicate_count,
            ],
        }
    )

    bar_chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusEnd=6)
        .encode(
            x=alt.X("Category:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Records:Q", title="Number of records", scale=alt.Scale(domainMin=0)),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(
                    domain=["Accepted", "Rejected", "Duplicates"],
                    range=["#34d399", "#fb7185", "#fbbf24"],
                ),
                legend=None,
            ),
            tooltip=["Category:N", "Records:Q"],
        )
        .properties(height=300)
    )

    # The categories overlap conceptually: duplicate records can also be rejected.
    # The chart is intended for comparison, not to sum categories.
    with chart_col1:
        st.markdown("**Record Counts**")
        st.altair_chart(bar_chart, use_container_width=True)

    with chart_col2:
        st.markdown("**Accepted vs Rejected**")

        outcome_data = pd.DataFrame(
            {
                "Outcome": ["Accepted", "Rejected"],
                "Records": [accepted_count, rejected_count],
            }
        )

        donut_chart = (
            alt.Chart(outcome_data)
            .mark_arc(innerRadius=78, outerRadius=125)
            .encode(
                theta=alt.Theta("Records:Q"),
                color=alt.Color(
                    "Outcome:N",
                    scale=alt.Scale(
                        domain=["Accepted", "Rejected"],
                        range=["#34d399", "#fb7185"],
                    ),
                    legend=alt.Legend(orient="bottom"),
                ),
                tooltip=["Outcome:N", "Records:Q"],
            )
            .properties(height=300)
        )

        st.altair_chart(donut_chart, use_container_width=True)

    # --------------------------------------------------
    # 7. OUTPUT DOWNLOADS AND PREVIEWS
    # --------------------------------------------------
    st.divider()
    st.markdown(
        '<div class="section-title">05 / Export & Inspect</div>',
        unsafe_allow_html=True,
    )

    cleaned_bytes = st.session_state.etl_cleaned_bytes
    rejected_bytes = st.session_state.etl_rejected_bytes

    download1, download2 = st.columns(2, gap="medium")

    with download1:
        st.markdown("**Cleaned dataset**")
        st.caption("Validated and normalized records")
        st.download_button(
            "⬇  Download Cleaned CSV",
            data=cleaned_bytes,
            file_name=st.session_state.etl_cleaned_name,
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

    with download2:
        st.markdown("**Rejected records**")
        st.caption("Rejected rows with their reason codes")
        st.download_button(
            "⬇  Download Rejected JSON",
            data=rejected_bytes,
            file_name=st.session_state.etl_rejected_name,
            mime="application/json",
            use_container_width=True,
        )

    with st.expander("Preview cleaned dataset", expanded=False):
        cleaned_df = pd.read_csv(
            pd.io.common.BytesIO(cleaned_bytes)
        )
        st.caption(f"{len(cleaned_df)} accepted rows")
        st.dataframe(cleaned_df, use_container_width=True, hide_index=True)

    with st.expander("Inspect rejected records", expanded=False):
        rejected_records = json.loads(rejected_bytes.decode("utf-8"))

        if rejected_records:
            rejected_df = pd.json_normalize(
                rejected_records,
                sep=".",
            )
            st.caption(f"{len(rejected_df)} rejected rows")
            st.dataframe(
                rejected_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("No rejected records in this run.")

else:
    st.divider()
    st.markdown(
        '<div class="section-title">02 / Pipeline Overview</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Your dashboard is ready. Upload a CSV file and run the pipeline "
        "to populate the metrics, charts and downloadable reports."
    )

    empty1, empty2, empty3 = st.columns(3)

    with empty1:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">'
            'TOTAL INPUT</div><div class="metric-value">—</div>'
            '<div class="metric-note">Awaiting data</div></div>',
            unsafe_allow_html=True,
        )

    with empty2:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">'
            'ACCEPTED</div><div class="metric-value">—</div>'
            '<div class="metric-note">Awaiting processing</div></div>',
            unsafe_allow_html=True,
        )

    with empty3:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">'
            'REJECTED</div><div class="metric-value">—</div>'
            '<div class="metric-note">Awaiting validation</div></div>',
            unsafe_allow_html=True,
        )

# --------------------------------------------------
# 8. FOOTER
# --------------------------------------------------
st.divider()
st.caption(
    "RetailFlow · Retail Sales ETL · "
    "Local processing only · Built with Python and Streamlit"
)
