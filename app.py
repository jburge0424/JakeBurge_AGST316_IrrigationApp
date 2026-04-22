"""
Irrigation Scheduling App
AGST 316 - Python Coding
Author: Jake

A Streamlit app that analyzes weather data (precipitation, ET, temperature)
from a CSV file and recommends a daily irrigation schedule. Users can
customize the irrigation threshold, application amount, and log irrigation
events that have already been applied.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Irrigation Scheduler",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Color palette (Midnight & Mint)
COLOR_PRIMARY = "#0F172A"     # midnight navy
COLOR_PRECIP = "#10B981"      # mint green
COLOR_ET = "#FB923C"          # soft orange
COLOR_IRRIG = "#3B82F6"       # blue
COLOR_MANUAL = "#8B5CF6"      # purple for manual entries
COLOR_ACCENT = "#F59E0B"      # amber

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("💧 Irrigation Scheduling App")
st.caption(
    "Upload daily weather data and get customized irrigation recommendations "
    "based on precipitation, evapotranspiration, and your own irrigation log."
)
st.divider()

# ---------------------------------------------------------------------------
# Sidebar: file upload and user controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("1. Upload Data")
    uploaded_file = st.file_uploader(
        "Upload your weather CSV file",
        type="csv",
        help="File must contain Month, Date, Year, Precipitation_inches, and ET_inches columns.",
    )

    st.subheader("2. Irrigation Parameters")
    threshold = st.slider(
        "Deficit threshold (inches)",
        min_value=0.25,
        max_value=3.0,
        value=1.0,
        step=0.25,
        help="Irrigate when cumulative ET exceeds cumulative water input by this amount.",
    )
    application_amount = st.slider(
        "Application amount per event (inches)",
        min_value=0.25,
        max_value=3.0,
        value=1.0,
        step=0.25,
        help="How much water to apply each time irrigation is triggered.",
    )

    st.subheader("3. Manual Irrigation Log")
    st.caption("Record irrigation you've already applied. These are included in the water balance.")

# Initialize a place to store manual irrigation entries across reruns
if "manual_irrigation" not in st.session_state:
    st.session_state.manual_irrigation = []

# ---------------------------------------------------------------------------
# Main content — only runs if a file has been uploaded
# ---------------------------------------------------------------------------
if uploaded_file is None:
    st.info("👈 Upload a weather CSV file in the sidebar to get started.")
    st.markdown(
        """
        ### What this app does
        - Reads daily weather records (precipitation, evapotranspiration, temperature)
        - Calculates cumulative water balance throughout the year
        - Recommends irrigation when cumulative ET exceeds water inputs by your chosen threshold
        - Lets you log irrigation you've already applied and re-run the schedule
        - Provides interactive charts and a daily decision viewer

        ### Required CSV columns
        `Month`, `Date`, `Year`, `Time`, `Temperature_High_F`, `Temperature_Low_F`,
        `Relative_Humidity_%`, `Soil_Temperature_4_inch_deep`, `Wind_Speed_mi_per_hr`,
        `Solar_Radiation_Lang`, `Precipitation_inches`, `ET_inches`
        """
    )
    st.stop()

# ---------------------------------------------------------------------------
# Data loading and preparation (algorithms preserved from base assignment)
# ---------------------------------------------------------------------------
try:
    df = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"Could not read CSV file: {e}")
    st.stop()

required_cols = {"Month", "Date", "Year", "Precipitation_inches", "ET_inches"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Missing required columns: {', '.join(missing)}")
    st.stop()

# Build a proper datetime column, preserve the numeric month for later
df["Date_String"] = (
    df["Year"].astype(str) + "-" + df["Month"].astype(str) + "-" + df["Date"].astype(str)
)
df["Date_YMD"] = pd.to_datetime(df["Date_String"], format="%Y-%m-%d")
df["MonthName"] = df["Date_YMD"].dt.strftime("%B")
df["Day"] = df["Date_YMD"].dt.day
df.drop(columns=["Date_String", "Date", "Time"], inplace=True, errors="ignore")

# Temperature average
if "Temperature_High_F" in df.columns and "Temperature_Low_F" in df.columns:
    df["Temp_Avg"] = (df["Temperature_High_F"] + df["Temperature_Low_F"]) / 2

# Cumulative totals
df["Precip_Cum"] = df["Precipitation_inches"].cumsum()
df["ET_Cum"] = df["ET_inches"].cumsum()

# ---------------------------------------------------------------------------
# Manual irrigation — add a column from session state entries
# ---------------------------------------------------------------------------
df["Manual_Irrigation"] = 0.0
for entry in st.session_state.manual_irrigation:
    entry_date = pd.to_datetime(entry["date"])
    mask = df["Date_YMD"] == entry_date
    if mask.any():
        df.loc[mask, "Manual_Irrigation"] = entry["amount"]

# ---------------------------------------------------------------------------
# Irrigation decision algorithm (same logic as base assignment, with user-
# adjustable threshold and application amount, and manual entries mixed in)
# ---------------------------------------------------------------------------
df["Irrigation_daily"] = 0.0
df["Irrigation_Cum"] = 0.0

for i in range(len(df)):
    manual_today = df.loc[df.index[i], "Manual_Irrigation"]

    if i == 0:
        df.loc[df.index[i], "Irrigation_daily"] = manual_today
        df.loc[df.index[i], "Irrigation_Cum"] = manual_today
        continue

    et_cum = df.loc[df.index[i], "ET_Cum"]
    precip_cum = df.loc[df.index[i], "Precip_Cum"]
    prev_irrig_cum = df.loc[df.index[i - 1], "Irrigation_Cum"]

    # Water input side = precipitation + previous cumulative irrigation + any manual today
    water_in = precip_cum + prev_irrig_cum + manual_today

    if et_cum >= (water_in + threshold):
        df.loc[df.index[i], "Irrigation_daily"] = application_amount + manual_today
    else:
        df.loc[df.index[i], "Irrigation_daily"] = manual_today

    df.loc[df.index[i], "Irrigation_Cum"] = (
        prev_irrig_cum + df.loc[df.index[i], "Irrigation_daily"]
    )

df["Irrig_Precip_Cum"] = df["Precip_Cum"] + df["Irrigation_Cum"]

# ---------------------------------------------------------------------------
# Manual irrigation input form (sidebar, after df is loaded so date range is known)
# ---------------------------------------------------------------------------
with st.sidebar:
    min_date = df["Date_YMD"].min().date()
    max_date = df["Date_YMD"].max().date()

    with st.form("manual_irrig_form", clear_on_submit=True):
        log_date = st.date_input(
            "Date applied",
            min_value=min_date,
            max_value=max_date,
            value=min_date,
        )
        log_amount = st.number_input(
            "Amount (inches)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.25,
        )
        submitted = st.form_submit_button("➕ Add irrigation event")
        if submitted and log_amount > 0:
            st.session_state.manual_irrigation.append(
                {"date": str(log_date), "amount": log_amount}
            )
            st.rerun()

    if st.session_state.manual_irrigation:
        st.caption("**Logged irrigation events:**")
        for idx, entry in enumerate(st.session_state.manual_irrigation):
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"{entry['date']} — {entry['amount']} in")
            if col_b.button("🗑️", key=f"del_{idx}"):
                st.session_state.manual_irrigation.pop(idx)
                st.rerun()
        if st.button("Clear all"):
            st.session_state.manual_irrigation = []
            st.rerun()

# ---------------------------------------------------------------------------
# Main area: tabs
# ---------------------------------------------------------------------------
tab_overview, tab_schedule, tab_daily, tab_data = st.tabs(
    ["📊 Overview", "💦 Irrigation Schedule", "📅 Daily Decision", "📋 Data"]
)

# ---------- Tab 1: Overview ----------
with tab_overview:
    st.subheader("Daily & Cumulative Precipitation and ET")

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])

    fig1.add_trace(
        go.Bar(
            x=df["Date_YMD"],
            y=df["Precipitation_inches"],
            name="Daily precipitation",
            marker_color=COLOR_PRECIP,
            opacity=0.7,
        ),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Scatter(
            x=df["Date_YMD"],
            y=df["Precip_Cum"],
            name="Cumulative precipitation",
            line=dict(color=COLOR_PRECIP, width=3),
        ),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Scatter(
            x=df["Date_YMD"],
            y=df["ET_Cum"],
            name="Cumulative ET",
            line=dict(color=COLOR_ET, width=3),
        ),
        secondary_y=True,
    )
    fig1.add_trace(
        go.Scatter(
            x=df["Date_YMD"],
            y=df["ET_inches"],
            name="Daily ET",
            line=dict(color=COLOR_ET, width=1, dash="dot"),
            opacity=0.6,
        ),
        secondary_y=True,
    )

    fig1.update_layout(
        template="plotly_white",
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig1.update_xaxes(title_text="Date")
    fig1.update_yaxes(title_text="Precipitation (inches)", secondary_y=False, color=COLOR_PRECIP)
    fig1.update_yaxes(title_text="ET (inches)", secondary_y=True, color=COLOR_ET)

    st.plotly_chart(fig1, use_container_width=True)

# ---------- Tab 2: Irrigation Schedule ----------
with tab_schedule:
    st.subheader("Cumulative Precipitation + Irrigation vs. ET")

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])

    fig2.add_trace(
        go.Bar(
            x=df["Date_YMD"],
            y=df["Precipitation_inches"],
            name="Daily precipitation",
            marker_color=COLOR_PRECIP,
            opacity=0.6,
        ),
        secondary_y=False,
    )
    fig2.add_trace(
        go.Bar(
            x=df["Date_YMD"],
            y=df["Irrigation_daily"] - df["Manual_Irrigation"],
            name="Recommended irrigation",
            marker_color=COLOR_IRRIG,
        ),
        secondary_y=False,
    )
    if df["Manual_Irrigation"].sum() > 0:
        fig2.add_trace(
            go.Bar(
                x=df["Date_YMD"],
                y=df["Manual_Irrigation"],
                name="Manual irrigation (logged)",
                marker_color=COLOR_MANUAL,
            ),
            secondary_y=False,
        )
    fig2.add_trace(
        go.Scatter(
            x=df["Date_YMD"],
            y=df["Irrig_Precip_Cum"],
            name="Cumulative water input",
            line=dict(color=COLOR_IRRIG, width=3),
        ),
        secondary_y=True,
    )
    fig2.add_trace(
        go.Scatter(
            x=df["Date_YMD"],
            y=df["ET_Cum"],
            name="Cumulative ET",
            line=dict(color=COLOR_ET, width=3),
        ),
        secondary_y=True,
    )

    fig2.update_layout(
        template="plotly_white",
        height=500,
        hovermode="x unified",
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig2.update_xaxes(title_text="Date")
    fig2.update_yaxes(title_text="Daily amount (inches)", secondary_y=False)
    fig2.update_yaxes(title_text="Cumulative (inches)", secondary_y=True)

    st.plotly_chart(fig2, use_container_width=True)

    # Download button for the schedule
    schedule_df = df[
        ["Date_YMD", "Precipitation_inches", "ET_inches", "Manual_Irrigation", "Irrigation_daily"]
    ].copy()
    schedule_df.columns = ["Date", "Precipitation_in", "ET_in", "Manual_Irrigation_in", "Total_Irrigation_in"]
    csv_bytes = schedule_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download schedule as CSV",
        data=csv_bytes,
        file_name="irrigation_schedule.csv",
        mime="text/csv",
    )

# ---------- Tab 3: Daily Decision ----------
with tab_daily:
    st.subheader("Look up a specific day")

    col1, col2 = st.columns(2)
    with col1:
        months_in_order = df.sort_values("Date_YMD")["MonthName"].unique().tolist()
        selected_month = st.selectbox("Month", months_in_order)
    filtered = df[df["MonthName"] == selected_month]
    with col2:
        selected_day = st.selectbox("Day", sorted(filtered["Day"].unique()))

    day_row = filtered[filtered["Day"] == selected_day].iloc[0]

    st.markdown("#### Recommendation")
    irrig_amt = day_row["Irrigation_daily"]
    if irrig_amt > 0:
        st.success(f"💧 Apply **{irrig_amt:.2f} inches** of irrigation on {selected_month} {selected_day}.")
    else:
        st.info(f"✅ No irrigation needed on {selected_month} {selected_day}.")

    c1, c2, c3 = st.columns(3)
    c1.metric("ET today", f"{day_row['ET_inches']:.3f} in")
    c2.metric("Precipitation today", f"{day_row['Precipitation_inches']:.3f} in")
    c3.metric("Manual irrigation logged", f"{day_row['Manual_Irrigation']:.2f} in")

    if "Temp_Avg" in df.columns:
        c4, c5, c6 = st.columns(3)
        c4.metric("Avg temperature", f"{day_row['Temp_Avg']:.1f} °F")
        c5.metric("Cumulative ET", f"{day_row['ET_Cum']:.2f} in")
        c6.metric("Cumulative water in", f"{day_row['Irrig_Precip_Cum']:.2f} in")

# ---------- Tab 4: Data ----------
with tab_data:
    st.subheader("Processed data")
    st.caption("All calculated columns are included. Use the search/sort controls on the table.")
    display_cols = [
        c for c in [
            "Date_YMD", "MonthName", "Day",
            "Temperature_High_F", "Temperature_Low_F", "Temp_Avg",
            "Precipitation_inches", "Precip_Cum",
            "ET_inches", "ET_Cum",
            "Manual_Irrigation", "Irrigation_daily", "Irrigation_Cum",
            "Irrig_Precip_Cum",
        ] if c in df.columns
    ]
    st.dataframe(df[display_cols], use_container_width=True, height=500)

st.divider()
st.caption("Built with Streamlit • AGST 316")
