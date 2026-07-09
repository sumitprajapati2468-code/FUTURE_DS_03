"""Marketing Funnel & Conversion Performance Analysis.

This script does the full end-to-end workflow:
1. Load an existing dataset if provided.
2. Generate a realistic synthetic funnel dataset when no dataset is available.
3. Clean and standardize the data.
4. Calculate funnel, channel, ROI/CAC, and trend metrics.
5. Build presentation-ready charts.
6. Export a markdown summary report and the cleaned dataset.

The code is organized so each step is reusable in a notebook, a script, or a Streamlit app.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


STAGE_ORDER = ["Visitor", "Lead", "MQL", "SQL", "Opportunity", "Customer"]
CHANNELS = ["Organic", "Paid Social", "Email", "Referral", "Paid Search"]
SEGMENTS = ["SMB", "Enterprise"]
RAW_CHANNEL_ALIASES = {
    "organic": "Organic",
    "organic search": "Organic",
    "organic_search": "Organic",
    "paid social": "Paid Social",
    "paid_social": "Paid Social",
    "paid-social": "Paid Social",
    "paid social ads": "Paid Social",
    "paid social ad": "Paid Social",
    "social ads": "Paid Social",
    "social_ads": "Paid Social",
    "email": "Email",
    "e-mail": "Email",
    "e mail": "Email",
    "e_mail": "Email",
    "referral": "Referral",
    "partner": "Referral",
    "partner referral": "Referral",
    "partner_referral": "Referral",
    "paid search": "Paid Search",
    "paid_search": "Paid Search",
    "ppc": "Paid Search",
    "search ads": "Paid Search",
    "search_ads": "Paid Search",
}
CHANNEL_SOURCE_LABELS = {
    "Organic": ["Organic Search", "organic", "Organic Search"],
    "Paid Social": ["Paid Social", "paid_social", "Social Ads"],
    "Email": ["Email", "e-mail", "EMAIL"],
    "Referral": ["Referral", "partner", "Partner Referral"],
    "Paid Search": ["Paid Search", "ppc", "Search Ads"],
}

CHANNEL_CONFIG = {
    "Organic": {
        "base_visitors": 1500,
        "lead_rate": 0.11,
        "mql_rate": 0.52,
        "sql_rate": 0.48,
        "opp_rate": 0.39,
        "cust_rate": 0.27,
        "cost_per_visitor": 0.55,
        "avg_revenue_per_customer": 1400,
        "campaign_lift": [0.92, 1.08],
        "segment_lift": {"SMB": 1.0, "Enterprise": 0.78},
    },
    "Paid Social": {
        "base_visitors": 2300,
        "lead_rate": 0.08,
        "mql_rate": 0.42,
        "sql_rate": 0.41,
        "opp_rate": 0.33,
        "cust_rate": 0.20,
        "cost_per_visitor": 1.75,
        "avg_revenue_per_customer": 1300,
        "campaign_lift": [0.88, 1.15],
        "segment_lift": {"SMB": 1.08, "Enterprise": 0.72},
    },
    "Email": {
        "base_visitors": 1100,
        "lead_rate": 0.17,
        "mql_rate": 0.58,
        "sql_rate": 0.53,
        "opp_rate": 0.46,
        "cust_rate": 0.31,
        "cost_per_visitor": 0.32,
        "avg_revenue_per_customer": 1600,
        "campaign_lift": [0.95, 1.10],
        "segment_lift": {"SMB": 0.96, "Enterprise": 1.05},
    },
    "Referral": {
        "base_visitors": 800,
        "lead_rate": 0.21,
        "mql_rate": 0.63,
        "sql_rate": 0.57,
        "opp_rate": 0.49,
        "cust_rate": 0.35,
        "cost_per_visitor": 0.18,
        "avg_revenue_per_customer": 1800,
        "campaign_lift": [0.90, 1.12],
        "segment_lift": {"SMB": 0.88, "Enterprise": 1.18},
    },
    "Paid Search": {
        "base_visitors": 1800,
        "lead_rate": 0.14,
        "mql_rate": 0.49,
        "sql_rate": 0.44,
        "opp_rate": 0.36,
        "cust_rate": 0.24,
        "cost_per_visitor": 1.30,
        "avg_revenue_per_customer": 1500,
        "campaign_lift": [0.91, 1.14],
        "segment_lift": {"SMB": 1.0, "Enterprise": 0.84},
    },
}


def ensure_directories(output_dir: Path) -> Dict[str, Path]:
    """Create the output folders used by the analysis."""

    data_dir = output_dir / "data"
    charts_dir = output_dir / "charts"
    reports_dir = output_dir / "reports"
    for folder in (data_dir, charts_dir, reports_dir):
        folder.mkdir(parents=True, exist_ok=True)
    return {"data": data_dir, "charts": charts_dir, "reports": reports_dir}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Marketing funnel analysis workflow")
    parser.add_argument("--input-csv", type=Path, default=None, help="Existing funnel dataset to analyze")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd(), help="Folder for generated outputs")
    parser.add_argument("--force-generate", action="store_true", help="Regenerate the synthetic dataset")
    return parser.parse_args()


def standardize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_channel_name(value: object) -> str:
    text_value = standardize_text(value).lower().replace("-", " ").replace("_", " ")
    text_value = " ".join(text_value.split())
    return RAW_CHANNEL_ALIASES.get(text_value, standardize_text(value).title())


def normalize_stage_name(value: object) -> str:
    text_value = standardize_text(value).strip().title()
    stage_lookup = {
        "visitor": "Visitor",
        "lead": "Lead",
        "mql": "MQL",
        "sql": "SQL",
        "opportunity": "Opportunity",
        "customer": "Customer",
    }
    return stage_lookup.get(text_value.lower(), text_value)


def seasonal_multiplier(week_number: int) -> float:
    """Simple seasonal pattern to keep the synthetic data realistic."""

    return 1.0 + 0.12 * np.sin((week_number / 26.0) * 2 * np.pi)


def generate_synthetic_funnel_data(output_csv: Path, seed: int = 42) -> pd.DataFrame:
    """Generate a realistic, messy marketing funnel dataset for testing."""

    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp.today().normalize() - pd.Timedelta(weeks=25)
    week_dates = pd.date_range(start=start_date, periods=26, freq="W-MON")
    rows: List[Dict[str, object]] = []

    for week_index, week_start in enumerate(week_dates, start=1):
        seasonality = seasonal_multiplier(week_index)
        for channel_index, channel in enumerate(CHANNELS):
            channel_config = CHANNEL_CONFIG[channel]
            for campaign_index in range(1, 3):
                campaign_lift = channel_config["campaign_lift"][campaign_index - 1]
                campaign_name = f"{channel} Campaign {campaign_index}"
                for segment in SEGMENTS:
                    segment_lift = channel_config["segment_lift"][segment]
                    visitors = int(
                        max(
                            80,
                            rng.poisson(
                                channel_config["base_visitors"]
                                * seasonality
                                * campaign_lift
                                * segment_lift
                            ),
                        )
                    )
                    lead_rate = np.clip(
                        channel_config["lead_rate"] * rng.normal(1.0, 0.06),
                        0.03,
                        0.35,
                    )
                    mql_rate = np.clip(
                        channel_config["mql_rate"] * rng.normal(1.0, 0.05),
                        0.18,
                        0.80,
                    )
                    sql_rate = np.clip(
                        channel_config["sql_rate"] * rng.normal(1.0, 0.05),
                        0.15,
                        0.80,
                    )
                    opp_rate = np.clip(
                        channel_config["opp_rate"] * rng.normal(1.0, 0.05),
                        0.10,
                        0.70,
                    )
                    cust_rate = np.clip(
                        channel_config["cust_rate"] * rng.normal(1.0, 0.05),
                        0.05,
                        0.60,
                    )

                    leads = int(rng.binomial(visitors, lead_rate))
                    mqls = int(rng.binomial(leads, mql_rate))
                    sqls = int(rng.binomial(mqls, sql_rate))
                    opportunities = int(rng.binomial(sqls, opp_rate))
                    customers = int(rng.binomial(opportunities, cust_rate))

                    cost = round(
                        visitors
                        * channel_config["cost_per_visitor"]
                        * rng.normal(1.0, 0.08),
                        2,
                    )
                    revenue = round(
                        customers
                        * channel_config["avg_revenue_per_customer"]
                        * rng.normal(1.0, 0.10),
                        2,
                    )

                    stage_counts = {
                        "Visitor": visitors,
                        "Lead": leads,
                        "MQL": mqls,
                        "SQL": sqls,
                        "Opportunity": opportunities,
                        "Customer": customers,
                    }
                    source_label = rng.choice(CHANNEL_SOURCE_LABELS[channel])
                    stage_date = week_start + pd.Timedelta(days=int(rng.integers(0, 7)))
                    for stage_order, stage in enumerate(STAGE_ORDER, start=1):
                        rows.append(
                            {
                                "date": stage_date.strftime("%Y-%m-%d"),
                                "week_start": week_start.strftime("%Y-%m-%d"),
                                "channel": channel,
                                "source": source_label,
                                "campaign": campaign_name,
                                "segment": segment,
                                "stage": stage,
                                "stage_order": stage_order,
                                "stage_count": stage_counts[stage],
                                "cost": cost if stage == "Visitor" else 0.0,
                                "revenue": revenue if stage == "Customer" else 0.0,
                                "channel_index": channel_index,
                                "campaign_index": campaign_index,
                                "week_index": week_index,
                            }
                        )

    raw_df = pd.DataFrame(rows)

    # Intentionally introduce a little mess so the cleaning step is meaningful.
    duplicate_sample = raw_df.sample(frac=0.03, random_state=seed)
    raw_df = pd.concat([raw_df, duplicate_sample], ignore_index=True)

    missing_channel_indices = raw_df.sample(frac=0.02, random_state=seed + 1).index
    raw_df.loc[missing_channel_indices, "channel"] = np.nan

    missing_campaign_indices = raw_df.sample(frac=0.01, random_state=seed + 2).index
    raw_df.loc[missing_campaign_indices, "campaign"] = np.nan

    inconsistent_stage_indices = raw_df.sample(frac=0.015, random_state=seed + 3).index
    raw_df.loc[inconsistent_stage_indices, "stage"] = raw_df.loc[inconsistent_stage_indices, "stage"].str.lower()

    inconsistent_source_indices = raw_df.sample(frac=0.02, random_state=seed + 4).index
    raw_df.loc[inconsistent_source_indices, "source"] = raw_df.loc[inconsistent_source_indices, "source"].str.replace(" ", "_")

    missing_value_columns = ["stage_count", "cost", "revenue"]
    for column_name in missing_value_columns:
        missing_indices = raw_df.sample(frac=0.01, random_state=seed + 10 + missing_value_columns.index(column_name)).index
        raw_df.loc[missing_indices, column_name] = np.nan

    raw_df.to_csv(output_csv, index=False)
    return raw_df


def load_dataset(input_csv: Optional[Path], raw_csv_path: Path, force_generate: bool = False) -> pd.DataFrame:
    """Load an existing dataset or generate the synthetic one."""

    if input_csv and input_csv.exists():
        return pd.read_csv(input_csv)

    if raw_csv_path.exists() and not force_generate:
        return pd.read_csv(raw_csv_path)

    return generate_synthetic_funnel_data(raw_csv_path)


def inspect_dataset(df: pd.DataFrame) -> pd.DataFrame:
    summary = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "missing_values": [int(df[column].isna().sum()) for column in df.columns],
            "unique_values": [int(df[column].nunique(dropna=True)) for column in df.columns],
        }
    )
    return summary


def clean_funnel_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize types, labels, and values for analysis."""

    cleaned = df.copy()
    cleaned.columns = [column.strip().lower() for column in cleaned.columns]

    if "date" in cleaned.columns:
        cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    if "week_start" in cleaned.columns:
        cleaned["week_start"] = pd.to_datetime(cleaned["week_start"], errors="coerce")
    cleaned["date"] = cleaned["date"].fillna(cleaned["week_start"])
    cleaned["date"] = cleaned["date"].fillna(pd.Timestamp.today().normalize())

    for text_column in ["channel", "source", "campaign", "segment", "stage"]:
        if text_column in cleaned.columns:
            cleaned[text_column] = cleaned[text_column].astype("string")
            cleaned[text_column] = cleaned[text_column].fillna("")
            cleaned[text_column] = cleaned[text_column].str.strip()

    cleaned["channel"] = cleaned["channel"].replace("", pd.NA)
    cleaned["channel"] = cleaned["channel"].fillna(cleaned["source"])
    cleaned["channel"] = cleaned["channel"].apply(normalize_channel_name)
    cleaned["channel"] = cleaned["channel"].replace("", "Unknown")

    cleaned["source"] = cleaned["source"].apply(standardize_text)
    cleaned.loc[cleaned["source"].eq(""), "source"] = cleaned.loc[cleaned["source"].eq(""), "channel"]
    cleaned["campaign"] = cleaned["campaign"].replace("", pd.NA)
    cleaned["campaign"] = cleaned["campaign"].fillna("Unknown Campaign")
    cleaned["segment"] = cleaned["segment"].replace("", "Unknown")
    cleaned["segment"] = cleaned["segment"].str.title()
    cleaned["stage"] = cleaned["stage"].apply(normalize_stage_name)

    numeric_columns = ["stage_count", "cost", "revenue", "stage_order", "channel_index", "campaign_index", "week_index"]
    for numeric_column in numeric_columns:
        if numeric_column in cleaned.columns:
            cleaned[numeric_column] = pd.to_numeric(cleaned[numeric_column], errors="coerce")

    cleaned["stage_count"] = cleaned["stage_count"].fillna(0).round().astype(int)
    cleaned["cost"] = cleaned["cost"].fillna(0).astype(float)
    cleaned["revenue"] = cleaned["revenue"].fillna(0).astype(float)
    cleaned["stage_order"] = cleaned["stage_order"].fillna(cleaned["stage"].map({stage: order for order, stage in enumerate(STAGE_ORDER, start=1)}))
    cleaned["stage_order"] = cleaned["stage_order"].astype(int)

    cleaned = cleaned.drop_duplicates()
    cleaned = cleaned[cleaned["stage"].isin(STAGE_ORDER)].copy()
    cleaned = cleaned.sort_values(["date", "channel", "campaign", "segment", "stage_order"]).reset_index(drop=True)
    return cleaned


def calculate_funnel_summary(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    funnel_summary = (
        cleaned_df.groupby("stage", as_index=False)
        .agg(
            total_count=("stage_count", "sum"),
            total_cost=("cost", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .set_index("stage")
        .reindex(STAGE_ORDER)
        .reset_index()
    )
    funnel_summary[["total_count", "total_cost", "total_revenue"]] = funnel_summary[["total_count", "total_cost", "total_revenue"]].fillna(0)
    funnel_summary["stage_order"] = range(1, len(funnel_summary) + 1)
    funnel_summary["stage_to_stage_conversion_rate"] = funnel_summary["total_count"].div(funnel_summary["total_count"].shift(1))
    funnel_summary.loc[0, "stage_to_stage_conversion_rate"] = 1.0
    funnel_summary["stage_drop_off_rate"] = 1 - funnel_summary["stage_to_stage_conversion_rate"]
    funnel_summary.loc[0, "stage_drop_off_rate"] = 0.0
    funnel_summary["overall_conversion_from_visitor"] = funnel_summary["total_count"] / funnel_summary.loc[0, "total_count"]
    funnel_summary.loc[0, "overall_conversion_from_visitor"] = 1.0
    return funnel_summary


def calculate_channel_performance(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cleaned_df.groupby("channel", as_index=False)
        .agg(
            visitors=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Visitor"].sum())),
            leads=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Lead"].sum())),
            mqls=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "MQL"].sum())),
            sqls=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "SQL"].sum())),
            opportunities=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Opportunity"].sum())),
            customers=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Customer"].sum())),
            cost=("cost", "sum"),
            revenue=("revenue", "sum"),
        )
        .sort_values("customers", ascending=False)
        .reset_index(drop=True)
    )
    summary["lead_to_customer_conversion_rate"] = np.where(
        summary["leads"] > 0,
        summary["customers"] / summary["leads"],
        np.nan,
    )
    summary["visitor_to_customer_conversion_rate"] = np.where(
        summary["visitors"] > 0,
        summary["customers"] / summary["visitors"],
        np.nan,
    )
    summary["cac"] = np.where(summary["customers"] > 0, summary["cost"] / summary["customers"], np.nan)
    summary["roi"] = np.where(summary["cost"] > 0, (summary["revenue"] - summary["cost"]) / summary["cost"], np.nan)
    return summary


def calculate_channel_weekly_trend(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    weekly = (
        cleaned_df.groupby([pd.Grouper(key="date", freq="W-MON"), "channel"], as_index=False)
        .agg(
            leads=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Lead"].sum())),
            customers=("stage_count", lambda series: int(series[cleaned_df.loc[series.index, "stage"] == "Customer"].sum())),
            cost=("cost", "sum"),
        )
        .rename(columns={"date": "week_start"})
    )
    weekly["lead_to_customer_conversion_rate"] = np.where(
        weekly["leads"] > 0, weekly["customers"] / weekly["leads"], np.nan
    )
    weekly["month"] = weekly["week_start"].dt.to_period("M").dt.to_timestamp()
    return weekly


def calculate_monthly_channel_trend(weekly_trend: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        weekly_trend.groupby(["month", "channel"], as_index=False)
        .agg(
            leads=("leads", "sum"),
            customers=("customers", "sum"),
            cost=("cost", "sum"),
        )
        .sort_values(["month", "channel"])
    )
    monthly["lead_to_customer_conversion_rate"] = np.where(
        monthly["leads"] > 0, monthly["customers"] / monthly["leads"], np.nan
    )
    return monthly


def create_funnel_chart(funnel_summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Funnel(
            y=funnel_summary["stage"],
            x=funnel_summary["total_count"],
            textinfo="value+percent initial",
            marker={"color": ["#0B6E99", "#1D91C0", "#41B6C4", "#7FCDBB", "#C7E9B4", "#F03B20"]},
        )
    )
    fig.update_layout(
        title="Marketing Funnel Drop-Off",
        template="plotly_white",
        font={"family": "Arial", "size": 14},
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )
    return fig


def create_channel_performance_chart(channel_summary: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=channel_summary["channel"],
            y=channel_summary["leads"],
            name="Leads",
            marker_color="#0B6E99",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=channel_summary["channel"],
            y=channel_summary["customers"],
            name="Customers",
            marker_color="#F28E2B",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=channel_summary["channel"],
            y=channel_summary["lead_to_customer_conversion_rate"],
            name="Lead to Customer Conversion Rate",
            mode="lines+markers",
            marker={"size": 10, "color": "#2CA02C"},
            line={"width": 3, "color": "#2CA02C"},
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Channel Performance: Volume and Conversion",
        template="plotly_white",
        barmode="group",
        font={"family": "Arial", "size": 14},
        margin={"l": 40, "r": 40, "t": 60, "b": 40},
    )
    fig.update_yaxes(title_text="Volume", secondary_y=False)
    fig.update_yaxes(title_text="Lead to Customer Conversion Rate", secondary_y=True, tickformat=".0%")
    return fig


def create_trend_chart(weekly_trend: pd.DataFrame) -> go.Figure:
    overall_weekly = (
        weekly_trend.groupby("week_start", as_index=False)
        .agg(leads=("leads", "sum"), customers=("customers", "sum"))
        .sort_values("week_start")
    )
    overall_weekly["lead_to_customer_conversion_rate"] = np.where(
        overall_weekly["leads"] > 0,
        overall_weekly["customers"] / overall_weekly["leads"],
        np.nan,
    )
    fig = px.line(
        overall_weekly,
        x="week_start",
        y="lead_to_customer_conversion_rate",
        title="Weekly Lead to Customer Conversion Trend",
        markers=True,
    )
    fig.update_traces(line={"color": "#0B6E99", "width": 3})
    fig.update_layout(template="plotly_white", font={"family": "Arial", "size": 14})
    fig.update_yaxes(tickformat=".0%", title="Lead to Customer Conversion Rate")
    fig.update_xaxes(title="Week")
    return fig


def create_channel_trend_chart(monthly_trend: pd.DataFrame) -> go.Figure:
    fig = px.line(
        monthly_trend,
        x="month",
        y="lead_to_customer_conversion_rate",
        color="channel",
        markers=True,
        title="Monthly Lead to Customer Conversion by Channel",
    )
    fig.update_layout(template="plotly_white", font={"family": "Arial", "size": 14})
    fig.update_yaxes(tickformat=".0%", title="Lead to Customer Conversion Rate")
    fig.update_xaxes(title="Month")
    return fig


def save_chart(fig: go.Figure, chart_dir: Path, base_name: str) -> Tuple[Optional[Path], Path]:
    html_path = chart_dir / f"{base_name}.html"
    png_path = chart_dir / f"{base_name}.png"
    fig.write_html(str(html_path))
    try:
        fig.write_image(str(png_path), scale=2)
    except Exception:
        png_path = None
    return png_path, html_path


def biggest_drop_off(funnel_summary: pd.DataFrame) -> pd.Series:
    drop_candidates = funnel_summary.loc[funnel_summary["stage_order"] > 1].copy()
    drop_candidates["drop_amount"] = drop_candidates["total_count"].shift(1) - drop_candidates["total_count"]
    drop_candidates["drop_rate"] = drop_candidates["stage_drop_off_rate"]
    return drop_candidates.sort_values("drop_rate", ascending=False).iloc[0]


def build_insights(
    funnel_summary: pd.DataFrame,
    channel_summary: pd.DataFrame,
    weekly_trend: pd.DataFrame,
    monthly_trend: pd.DataFrame,
) -> Tuple[List[str], List[str]]:
    biggest_drop = biggest_drop_off(funnel_summary)
    top_volume_channel = channel_summary.sort_values("leads", ascending=False).iloc[0]
    best_conversion_channel = channel_summary.sort_values("lead_to_customer_conversion_rate", ascending=False).iloc[0]
    best_cac_channel = channel_summary.sort_values("cac", ascending=True).iloc[0]
    worst_cac_channel = channel_summary.sort_values("cac", ascending=False).iloc[0]

    overall_weekly = (
        weekly_trend.groupby("week_start", as_index=False)
        .agg(leads=("leads", "sum"), customers=("customers", "sum"))
        .sort_values("week_start")
    )
    overall_weekly["lead_to_customer_conversion_rate"] = np.where(
        overall_weekly["leads"] > 0,
        overall_weekly["customers"] / overall_weekly["leads"],
        np.nan,
    )
    best_week = overall_weekly.loc[overall_weekly["lead_to_customer_conversion_rate"].idxmax()]
    worst_week = overall_weekly.loc[overall_weekly["lead_to_customer_conversion_rate"].idxmin()]
    distinct_monthly_channels = (
        monthly_trend.sort_values("lead_to_customer_conversion_rate", ascending=False)
        .drop_duplicates(subset=["channel"])
        .head(2)
    )
    top_monthly_channel = distinct_monthly_channels.iloc[0]["channel"]
    second_monthly_channel = distinct_monthly_channels.iloc[1]["channel"] if len(distinct_monthly_channels) > 1 else distinct_monthly_channels.iloc[0]["channel"]

    insights = [
        f"The largest funnel leak is between {biggest_drop['stage']} and the previous stage, with a {biggest_drop['stage_drop_off_rate']:.1%} drop-off.",
        f"{top_volume_channel['channel']} generates the most leads, while {best_conversion_channel['channel']} converts leads to customers at the highest rate ({best_conversion_channel['lead_to_customer_conversion_rate']:.1%}).",
        f"{best_cac_channel['channel']} has the best CAC at ${best_cac_channel['cac']:.0f}, while {worst_cac_channel['channel']} is the most expensive at ${worst_cac_channel['cac']:.0f} per customer.",
        f"Weekly conversion peaks around {best_week['week_start'].date()} at {best_week['lead_to_customer_conversion_rate']:.1%} and bottoms out around {worst_week['week_start'].date()} at {worst_week['lead_to_customer_conversion_rate']:.1%}.",
        f"Monthly trends show that {top_monthly_channel} and {second_monthly_channel} are the most efficient channels when demand is summarized by month.",
    ]

    recommendations = [
        f"Prioritize fixing the {biggest_drop['stage']} handoff by tightening qualification rules, improving follow-up speed, and testing stage-specific messaging.",
        f"Reallocate budget away from {worst_cac_channel['channel']} until its CAC moves closer to the portfolio average of ${channel_summary['cac'].mean():.0f}.",
        f"Scale {best_conversion_channel['channel']} with more budget or inventory because it has the strongest lead-to-customer efficiency.",
        "Review week-over-week fluctuations to identify campaign launches, creative fatigue, or sales capacity issues that coincide with conversion dips.",
        "Create a monthly channel scorecard that balances volume, conversion rate, CAC, and revenue so budget decisions are made on efficiency, not just traffic.",
    ]
    return insights, recommendations


def build_report_markdown(
    output_dir: Path,
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    inspection_df: pd.DataFrame,
    funnel_summary: pd.DataFrame,
    channel_summary: pd.DataFrame,
    weekly_trend: pd.DataFrame,
    monthly_trend: pd.DataFrame,
    insights: List[str],
    recommendations: List[str],
    chart_paths: Dict[str, Optional[Path]],
) -> str:
    stage_table = funnel_summary[["stage", "total_count", "stage_to_stage_conversion_rate", "stage_drop_off_rate"]].copy()
    stage_table["stage_to_stage_conversion_rate"] = stage_table["stage_to_stage_conversion_rate"].map(lambda value: f"{value:.1%}")
    stage_table["stage_drop_off_rate"] = stage_table["stage_drop_off_rate"].map(lambda value: f"{value:.1%}")

    channel_table = channel_summary[["channel", "visitors", "leads", "customers", "lead_to_customer_conversion_rate", "cac", "roi"]].copy()
    channel_table["lead_to_customer_conversion_rate"] = channel_table["lead_to_customer_conversion_rate"].map(lambda value: f"{value:.1%}")
    channel_table["cac"] = channel_table["cac"].map(lambda value: f"${value:,.0f}")
    channel_table["roi"] = channel_table["roi"].map(lambda value: f"{value:.1%}")

    top_monthly = monthly_trend.sort_values("lead_to_customer_conversion_rate", ascending=False).head(8).copy()
    top_monthly["lead_to_customer_conversion_rate"] = top_monthly["lead_to_customer_conversion_rate"].map(lambda value: f"{value:.1%}")

    def path_or_placeholder(path_value: Optional[Path]) -> str:
        if path_value is None:
            return "Chart export unavailable"
        return str(path_value.relative_to(output_dir)).replace("\\", "/")

    markdown_lines = [
        "# Marketing Funnel & Conversion Performance Summary",
        "",
        "## Executive Overview",
        f"This analysis used {len(cleaned_df):,} cleaned rows derived from {len(raw_df):,} raw rows. The dataset covers 6 months, 5 channels, 2 campaigns per channel, and 2 audience segments.",
        "",
        "## Data Quality Check",
        inspection_df.head(12).to_markdown(index=False),
        "",
        "## Funnel Performance",
        stage_table.to_markdown(index=False),
        "",
        "## Channel Performance",
        channel_table.to_markdown(index=False),
        "",
        "## Weekly and Monthly Trends",
        "The weekly trend chart highlights short-term conversion movement. The monthly channel table below shows which channels hold efficiency over time.",
        "",
        top_monthly.to_markdown(index=False),
        "",
        "## Key Insights",
    ]
    for insight in insights:
        markdown_lines.append(f"- {insight}")
    markdown_lines.extend(
        [
            "",
            "## Recommendations",
        ]
    )
    for recommendation in recommendations:
        markdown_lines.append(f"- {recommendation}")
    markdown_lines.extend(
        [
            "",
            "## Charts",
            f"![Funnel Chart]({path_or_placeholder(chart_paths.get('funnel_png'))})",
            f"![Channel Performance Chart]({path_or_placeholder(chart_paths.get('channel_png'))})",
            f"![Weekly Trend Chart]({path_or_placeholder(chart_paths.get('trend_png'))})",
            f"![Monthly Trend Chart]({path_or_placeholder(chart_paths.get('channel_trend_png'))})",
            "",
            "## Notes for Stakeholders",
            "The highest-volume channel is not always the most efficient. Use the CAC and conversion columns together when deciding where to scale budget.",
        ]
    )
    return "\n".join(markdown_lines)


def run_pipeline(input_csv: Optional[Path], output_dir: Path, force_generate: bool = False) -> Dict[str, object]:
    folders = ensure_directories(output_dir)
    raw_csv_path = folders["data"] / "marketing_funnel_raw.csv"
    cleaned_csv_path = folders["data"] / "marketing_funnel_cleaned.csv"
    inspection_csv_path = folders["data"] / "dataset_inspection.csv"
    funnel_csv_path = folders["data"] / "funnel_summary.csv"
    channel_csv_path = folders["data"] / "channel_performance.csv"
    weekly_csv_path = folders["data"] / "weekly_channel_trend.csv"
    monthly_csv_path = folders["data"] / "monthly_channel_trend.csv"
    report_path = folders["reports"] / "marketing_funnel_summary.md"

    raw_df = load_dataset(input_csv=input_csv, raw_csv_path=raw_csv_path, force_generate=force_generate)
    inspection_df = inspect_dataset(raw_df)
    cleaned_df = clean_funnel_data(raw_df)
    funnel_summary = calculate_funnel_summary(cleaned_df)
    channel_summary = calculate_channel_performance(cleaned_df)
    weekly_trend = calculate_channel_weekly_trend(cleaned_df)
    monthly_trend = calculate_monthly_channel_trend(weekly_trend)

    cleaned_df.to_csv(cleaned_csv_path, index=False)
    inspection_df.to_csv(inspection_csv_path, index=False)
    funnel_summary.to_csv(funnel_csv_path, index=False)
    channel_summary.to_csv(channel_csv_path, index=False)
    weekly_trend.to_csv(weekly_csv_path, index=False)
    monthly_trend.to_csv(monthly_csv_path, index=False)

    funnel_fig = create_funnel_chart(funnel_summary)
    channel_fig = create_channel_performance_chart(channel_summary)
    trend_fig = create_trend_chart(weekly_trend)
    channel_trend_fig = create_channel_trend_chart(monthly_trend)

    chart_paths: Dict[str, Optional[Path]] = {}
    for base_name, fig in {
        "funnel": funnel_fig,
        "channel": channel_fig,
        "trend": trend_fig,
        "channel_trend": channel_trend_fig,
    }.items():
        png_path, html_path = save_chart(fig, folders["charts"], base_name)
        chart_paths[f"{base_name}_png"] = png_path
        chart_paths[f"{base_name}_html"] = html_path

    insights, recommendations = build_insights(funnel_summary, channel_summary, weekly_trend, monthly_trend)
    report_markdown = build_report_markdown(
        output_dir=output_dir,
        raw_df=raw_df,
        cleaned_df=cleaned_df,
        inspection_df=inspection_df,
        funnel_summary=funnel_summary,
        channel_summary=channel_summary,
        weekly_trend=weekly_trend,
        monthly_trend=monthly_trend,
        insights=insights,
        recommendations=recommendations,
        chart_paths=chart_paths,
    )
    report_path.write_text(report_markdown, encoding="utf-8")

    return {
        "raw_df": raw_df,
        "inspection_df": inspection_df,
        "cleaned_df": cleaned_df,
        "funnel_summary": funnel_summary,
        "channel_summary": channel_summary,
        "weekly_trend": weekly_trend,
        "monthly_trend": monthly_trend,
        "insights": insights,
        "recommendations": recommendations,
        "chart_paths": chart_paths,
        "report_path": report_path,
        "cleaned_csv_path": cleaned_csv_path,
        "raw_csv_path": raw_csv_path,
    }


def main() -> None:
    args = parse_args()
    results = run_pipeline(input_csv=args.input_csv, output_dir=args.output_dir, force_generate=args.force_generate)
    funnel_summary = results["funnel_summary"]
    channel_summary = results["channel_summary"]
    report_path = results["report_path"]

    print("Synthetic dataset and analysis completed successfully.")
    print(f"Cleaned data saved to: {results['cleaned_csv_path']}")
    print(f"Summary report saved to: {report_path}")
    print("\nTop funnel drop-off:")
    print(funnel_summary[["stage", "total_count", "stage_drop_off_rate"]].to_string(index=False))
    print("\nChannel performance:")
    display_columns = ["channel", "customers", "lead_to_customer_conversion_rate", "cac", "roi"]
    channel_display = channel_summary[display_columns].copy()
    channel_display["lead_to_customer_conversion_rate"] = channel_display["lead_to_customer_conversion_rate"].map(lambda value: f"{value:.1%}")
    channel_display["cac"] = channel_display["cac"].map(lambda value: f"${value:,.0f}")
    channel_display["roi"] = channel_display["roi"].map(lambda value: f"{value:.1%}")
    print(channel_display.to_string(index=False))


if __name__ == "__main__":
    main()
