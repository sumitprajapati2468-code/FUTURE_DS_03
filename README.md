# Marketing Funnel & Conversion Performance Analysis

This project analyzes a marketing funnel from visitor to customer, cleans messy source data, calculates conversion and efficiency metrics, and exports charts plus a summary report. It also includes a Streamlit dashboard for interactive exploration.

## What it does

- Loads an uploaded CSV or generates a synthetic sample dataset when no input is provided.
- Cleans and standardizes funnel data.
- Builds funnel, channel, weekly, and monthly performance summaries.
- Exports charts as HTML and PNG files.
- Writes a markdown summary report with key insights and recommendations.
- Provides a Streamlit dashboard for visual inspection of the results.

## Project Layout

- `marketing_funnel_analysis.py` - end-to-end analysis pipeline and CLI entry point.
- `streamlit_dashboard.py` - Streamlit app for interactive analysis.
- `marketing_funnel_analysis.ipynb` - notebook version of the analysis.
- `data/` - source and generated CSV files.
- `charts/` - exported charts in HTML and PNG formats.
- `reports/` - markdown summary report.

## Requirements

The code uses Python with these main packages:

- pandas
- numpy
- plotly
- streamlit

Optional, but recommended for PNG chart export:

- kaleido

## Setup

Create and activate a virtual environment, then install the dependencies you need:

```bash
pip install pandas numpy plotly streamlit kaleido
```

If you only want to run the Streamlit dashboard, `streamlit` is required. If you only want the analysis script, `streamlit` is optional.

## Run the Analysis Script

Run the full pipeline from the command line:

```bash
python marketing_funnel_analysis.py
```

Optional arguments:

- `--input-csv PATH` - analyze an existing CSV instead of the bundled/generated sample.
- `--output-dir PATH` - choose where outputs are written.
- `--force-generate` - regenerate the synthetic dataset even if a raw file already exists.

Example:

```bash
python marketing_funnel_analysis.py --input-csv data\marketing_funnel_raw.csv --output-dir .
```

## Run the Streamlit Dashboard

Start the dashboard with:

```bash
streamlit run streamlit_dashboard.py
```

In the app, you can upload a CSV or generate the built-in synthetic sample data, then click Run analysis to refresh the visuals and tables.

## Outputs

Running the pipeline creates or updates these files:

- `data/marketing_funnel_raw.csv`
- `data/marketing_funnel_cleaned.csv`
- `data/dataset_inspection.csv`
- `data/funnel_summary.csv`
- `data/channel_performance.csv`
- `data/weekly_channel_trend.csv`
- `data/monthly_channel_trend.csv`
- `charts/funnel.html` and `charts/funnel.png`
- `charts/channel.html` and `charts/channel.png`
- `charts/trend.html` and `charts/trend.png`
- `charts/channel_trend.html` and `charts/channel_trend.png`
- `reports/marketing_funnel_summary.md`

## Notes

- The analysis can generate a realistic synthetic funnel dataset if no input CSV is available.
- PNG chart export may be unavailable if `kaleido` is not installed, but the HTML charts will still be written.
- The dashboard saves its temporary uploaded file and generated outputs under `streamlit_outputs/`.

## Summary

This project is useful for exploring funnel drop-off, comparing channel efficiency, and surfacing actionable marketing recommendations from messy conversion data.
