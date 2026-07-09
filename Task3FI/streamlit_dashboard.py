from __future__ import annotations

from pathlib import Path

import streamlit as st

from marketing_funnel_analysis import run_pipeline


st.set_page_config(page_title="Marketing Funnel Dashboard", layout="wide")
st.title("Marketing Funnel & Conversion Performance Dashboard")
st.caption("Upload a CSV or use the built-in synthetic dataset to explore funnel drop-off, channel performance, and conversion trends.")

output_dir = Path.cwd() / "streamlit_outputs"
uploaded_file = st.sidebar.file_uploader("Upload a marketing funnel CSV", type=["csv"])
force_generate = st.sidebar.checkbox("Regenerate synthetic sample data", value=False)
run_button = st.sidebar.button("Run analysis")

if "results" not in st.session_state:
    st.session_state.results = None

if run_button:
    input_path = None
    temp_input_path = None
    if uploaded_file is not None:
        temp_input_path = output_dir / "uploaded_input.csv"
        temp_input_path.parent.mkdir(parents=True, exist_ok=True)
        temp_input_path.write_bytes(uploaded_file.getbuffer())
        input_path = temp_input_path

    st.session_state.results = run_pipeline(
        input_csv=input_path,
        output_dir=output_dir,
        force_generate=force_generate,
    )

results = st.session_state.results

if results is None:
    st.info("Click Run analysis to generate the funnel metrics and charts.")
else:
    funnel_summary = results["funnel_summary"]
    channel_summary = results["channel_summary"]
    weekly_trend = results["weekly_trend"]
    monthly_trend = results["monthly_trend"]

    top_metrics = st.columns(4)
    top_metrics[0].metric("Cleaned rows", f"{len(results['cleaned_df']):,}")
    top_metrics[1].metric("Total visitors", f"{int(funnel_summary.loc[funnel_summary['stage'] == 'Visitor', 'total_count'].iloc[0]):,}")
    top_metrics[2].metric("Total customers", f"{int(funnel_summary.loc[funnel_summary['stage'] == 'Customer', 'total_count'].iloc[0]):,}")
    top_metrics[3].metric("Summary report", "Generated")

    st.subheader("Funnel Chart")
    if results["chart_paths"]["funnel_png"] is not None:
        st.image(str(results["chart_paths"]["funnel_png"]), use_container_width=True)

    st.subheader("Channel Performance Chart")
    if results["chart_paths"]["channel_png"] is not None:
        st.image(str(results["chart_paths"]["channel_png"]), use_container_width=True)

    st.subheader("Weekly Conversion Trend")
    if results["chart_paths"]["trend_png"] is not None:
        st.image(str(results["chart_paths"]["trend_png"]), use_container_width=True)

    st.subheader("Monthly Channel Trend")
    if results["chart_paths"]["channel_trend_png"] is not None:
        st.image(str(results["chart_paths"]["channel_trend_png"]), use_container_width=True)

    st.subheader("Channel Performance Table")
    st.dataframe(channel_summary, use_container_width=True)

    st.subheader("Weekly Trend Data")
    st.dataframe(weekly_trend.head(20), use_container_width=True)

    st.subheader("Monthly Trend Data")
    st.dataframe(monthly_trend, use_container_width=True)

    st.subheader("Key Insights")
    for insight in results["insights"]:
        st.write(f"- {insight}")

    st.subheader("Recommendations")
    for recommendation in results["recommendations"]:
        st.write(f"- {recommendation}")

    st.sidebar.success(f"Report saved to {results['report_path']}")
