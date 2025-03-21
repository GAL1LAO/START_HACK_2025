import streamlit as st
import pandas as pd
import altair as alt
import streamlit_shadcn_ui as ui
from local_components import card_container

# CONFIGS
DATA_URL2 = "device_data_analysis_2years.csv"
BAR_CHART_COLOR = "#ffffff"

st.set_page_config(page_title="Energy Dashboard", page_icon="📈", layout="wide")

options = [
    "14e5bc06-9e32-4938-96df-82a070581e7d"
    "26245f9f-8f9f-41b8-90bc-fa47640395f2",
    "25ff3a33-6eba-4238-9b8f-c0dea3f2e2c3",
    "5dd3b941-aab6-44de-bdb6-b5e82026cc54",
    "96e6013a-9e90-4dbd-9070-d6b4732f42b8",
    "968cc402-586d-4d47-ba8b-97c065762d0d"
]

col1, col2, col3 = st.columns(3)

with col1:
    st.title(f"Energy Dashboard", anchor=False)

with col3:
    selected_option = st.selectbox("Select an ID", options)

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Load Monthly Summary Data
@st.cache_data
def load_monthly_summary():
    file_path = "monthly_summary.csv"
    df = pd.read_csv(file_path)
    return df

monthly_summary_df = load_monthly_summary()

# Calculate Maximum Power for Each Year
yearly_max_power = monthly_summary_df.groupby(monthly_summary_df["month"].str[:4])["power"].max().reset_index()
yearly_max_power.rename(columns={"month": "year", "power": "max_power"}, inplace=True)

# Define seasons mapping
def get_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"

# Process Seasonal Averages
monthly_summary_df["season"] = monthly_summary_df["month"].str[-2:].astype(int).apply(get_season)
seasonal_avg_power = monthly_summary_df.groupby("season")["power"].mean().reset_index()
seasonal_avg_power.rename(columns={"power": "avg_power"}, inplace=True)

@st.cache_data
def load_recent_weekly_data():
    df = pd.read_csv("device_data_analysis_weekly_30min.csv")  # Replace with actual file name
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["week"] = df["start_time"].dt.isocalendar().week
    df["year"] = df["start_time"].dt.year
    return df

recent_df = load_recent_weekly_data()


# Load Power Data
def load_data():
    file_path = "device_data_analysis_2years.csv"
    df = pd.read_csv(file_path)
    df["day"] = pd.to_datetime(df["day"])
    df["season"] = df["day"].dt.month.apply(get_season)
    return df

df = load_data()

# Identify Anomalies for Power
def detect_anomalies(df, column="avg_abs_power", threshold=3):
    df["z_score"] = (df[column] - df[column].mean()) / df[column].std()
    df["is_anomaly"] = df["z_score"].abs() > threshold
    return df

df = detect_anomalies(df)

# Load Flow Data
def load_flow_data():
    file_path = "device_data_analysis_2years.csv"
    df = pd.read_csv(file_path)
    df["day"] = pd.to_datetime(df["day"])
    df["season"] = df["day"].dt.month.apply(get_season)
    return df

flow_df = load_flow_data()

# Identify Anomalies for Flow Data
def detect_flow_anomalies(df, column="avg_abs_flow", threshold=3):
    df["z_score_flow"] = (df[column] - df[column].mean()) / df[column].std()
    df["is_flow_anomaly"] = df["z_score_flow"].abs() > threshold
    return df

flow_df = detect_flow_anomalies(flow_df)

## Process Seasonal Averages for Flow
seasonal_avg_flow = flow_df.groupby("season")["avg_abs_flow"].mean().reset_index()
seasonal_avg_flow.rename(columns={"avg_abs_flow": "avg_flow"}, inplace=True)

# Ensure correct season order
season_order = ["Winter", "Spring", "Summer", "Fall"]
seasonal_avg_power = seasonal_avg_power.set_index("season").reindex(season_order).reset_index()
seasonal_avg_flow = seasonal_avg_flow.set_index("season").reindex(season_order).reset_index()

# **Display Yearly Maximum Power, Seasonal Avg Power, and Flow**
st.subheader("Seasonal Averages: Power & Flow")

# **First Row: Power**
col_winter, col_spring, col_summer, col_fall = st.columns(4)
for col, season in zip([col_winter, col_spring, col_summer, col_fall], season_order):
    with col:
        power_value = seasonal_avg_power[seasonal_avg_power["season"] == season]["avg_power"].values[0]
        ui.metric_card(
            title=f"{season} Power",
            content=f"{power_value:,.2f} W",
            description="Avg Power",
            key=f"seasonal_power_{season}"
        )

# **Second Row: Flow**
col_winter, col_spring, col_summer, col_fall = st.columns(4)
for col, season in zip([col_winter, col_spring, col_summer, col_fall], season_order):
    with col:
        flow_value = seasonal_avg_flow[seasonal_avg_flow["season"] == season]["avg_flow"].values[0]
        ui.metric_card(
            title=f"{season} Flow",
            content=f"{flow_value*1000:,.2f} cm³/s",
            description="Avg Flow",
            key=f"seasonal_flow_{season}"
        )

# POWER ANALYSIS SECTION
st.subheader("Power Analysis")
# Year selector - directly aligned left without columns
year = st.selectbox("Select Year for Power Analysis:", 
                    sorted(df["day"].dt.year.unique(), reverse=True))

# Filter Data for Selected Year for Power
yearly_data = df[df["day"].dt.year == year]

# Create two columns for Power Analysis
col1, col2 = st.columns(2)

# Plot 1: Daily Average Absolute Power Over Time
with col1:
    st.subheader("Daily Average Power Over Time")
    base = alt.Chart(df).encode(x=alt.X("day:T", title="Date"), y=alt.Y("avg_abs_power:Q", title="Power (W)"))
    
    line = base.mark_line().encode(tooltip=["day:T", "avg_abs_power:Q"])
    anomalies = base.mark_circle(color="red", size=50).encode(
        tooltip=["day:T", "avg_abs_power:Q"]
    ).transform_filter(
        alt.datum.is_anomaly == True
    )
    
    chart1 = (line + anomalies).properties(width=400, height=400, title="Daily Avg Absolute Power")
    st.altair_chart(chart1, use_container_width=True)

# Plot 2: Yearly Power Plot
with col2:
    st.subheader(f"Daily Average Power in {year}")
    if not yearly_data.empty:
        base2 = alt.Chart(yearly_data).encode(x=alt.X("day:T", title="Date"), y=alt.Y("avg_abs_power:Q", title="Power (W)"))
        
        line2 = base2.mark_line().encode(tooltip=["day:T", "avg_abs_power:Q"])
        anomalies2 = base2.mark_circle(color="red", size=50).encode(
            tooltip=["day:T", "avg_abs_power:Q"]
        ).transform_filter(
            alt.datum.is_anomaly == True
        )
        
        chart2 = (line2 + anomalies2).properties(width=400, height=400, title=f"Daily Avg Absolute Power ({year})")
        st.altair_chart(chart2, use_container_width=True)
    else:
        st.warning(f"No data available for the year {year}.")

# FLOW ANALYSIS SECTION
st.subheader("Flow Analysis")
# Year selector - directly aligned left without columns
flow_year = st.selectbox("Select Year for Flow Analysis:", 
                         sorted(flow_df["day"].dt.year.unique(), reverse=True))

# Filter Data for Selected Year for Flow
yearly_flow_data = flow_df[flow_df["day"].dt.year == flow_year]

# Create two columns for Flow Analysis
col3, col4 = st.columns(2)

# Plot 3: Daily Average Flow Over Time
with col3:
    st.subheader("Daily Average Flow Over Time")
    base_flow = alt.Chart(flow_df).encode(x=alt.X("day:T", title="Date"), y=alt.Y("avg_abs_flow:Q", title="Flow (m³/s)"))

    line_flow = base_flow.mark_line().encode(tooltip=["day:T", "avg_abs_flow:Q"])
    anomalies_flow = base_flow.mark_circle(color="red", size=50).encode(
        tooltip=["day:T", "avg_abs_flow:Q"]
    ).transform_filter(alt.datum.is_flow_anomaly == True)

    chart3 = (line_flow + anomalies_flow).properties(width=400, height=400, title="Daily Avg Flow")
    st.altair_chart(chart3, use_container_width=True)

# Plot 4: Yearly Flow Plot
with col4:
    st.subheader(f"Daily Average Flow in {flow_year}")
    if not yearly_flow_data.empty:
        base_flow2 = alt.Chart(yearly_flow_data).encode(x=alt.X("day:T", title="Date"), y=alt.Y("avg_abs_flow:Q", title="Flow (m³/s)"))
        
        line_flow2 = base_flow2.mark_line().encode(tooltip=["day:T", "avg_abs_flow:Q"])
        anomalies_flow2 = base_flow2.mark_circle(color="red", size=50).encode(
            tooltip=["day:T", "avg_abs_flow:Q"]
        ).transform_filter(
            alt.datum.is_flow_anomaly == True
        )
        
        chart4 = (line_flow2 + anomalies_flow2).properties(width=400, height=400, title=f"Daily Avg Flow ({flow_year})")
        st.altair_chart(chart4, use_container_width=True)
    else:
        st.warning(f"No data available for the year {flow_year}.")

# WEEKLY ANALYSIS SECTION
st.subheader("Weekly Analysis")
# Group weeks by year for uniqueness
recent_df["week_label"] = recent_df["year"].astype(str) + " - Week " + recent_df["week"].astype(str)
week_options = recent_df["week_label"].drop_duplicates().sort_values(ascending=False).tolist()

# Always include weeks 31 and 32 as options
selected_weeks = ["2020 - Week 31", "2020 - Week 32"]

# Week selector - directly aligned left without columns
# Default to Week 32 initially
selected_week_label = st.selectbox("Select Week (Power & Flow - 30 min Avg):", 
                                  selected_weeks,
                                  index=1 if "2020 - Week 32" in selected_weeks else 0)

# Filter data for selected week
selected_year, selected_week = selected_week_label.split(" - Week ")
selected_year = int(selected_year)
selected_week = int(selected_week)

# Get the selected week data without showing warnings
selected_week_data = recent_df[
    (recent_df["year"] == selected_year) &
    (recent_df["week"] == selected_week)
]


# Create two columns for the third row (weekly analysis)
col5, col6 = st.columns(2)

# Weekly Power Chart
with col5:
    st.subheader(f"Power Over Time")
    if not selected_week_data.empty:
        power_chart = alt.Chart(selected_week_data).mark_line().encode(
            x=alt.X("start_time:T", title="Time", axis=alt.Axis(
                format="%a %d %b %Y", # Format as "Mon 01 Jan 2020"
                labelAngle=-45,
                title="Date"
            )),
            y=alt.Y("avg_abs_power:Q", title="Power (W)"),
            tooltip=["start_time:T", "avg_abs_power:Q"]
        ).properties(
            width=400,
            height=400, title=f"Power in week {selected_week}"
        )
        st.altair_chart(power_chart, use_container_width=True)

# Weekly Flow Chart
with col6:
    st.subheader(f"Flow Over Time")
    if not selected_week_data.empty:
        flow_chart = alt.Chart(selected_week_data).mark_line().encode(
            x=alt.X("start_time:T", title="Time", axis=alt.Axis(
                format="%a %d %b %Y", # Format as "Mon 01 Jan 2020"
                labelAngle=-45,
                title="Date"
            )),
            y=alt.Y("avg_abs_flow:Q", title="Flow (m³/s)"),
            tooltip=["start_time:T", "avg_abs_flow:Q"]
        ).properties(
            width=400,
            height=400, title=f"Flow in week {selected_week}"
        )
        st.altair_chart(flow_chart, use_container_width=True)