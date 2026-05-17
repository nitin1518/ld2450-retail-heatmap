from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(
    page_title="LD2450 Retail Heatmap",
    layout="wide",
)


def secret(name: str, default: str = "") -> str:
    return st.secrets.get(name, default)


SUPABASE_URL = secret("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = secret("SUPABASE_SERVICE_ROLE_KEY")
DASHBOARD_PASSWORD = secret("DASHBOARD_PASSWORD")


def require_password() -> None:
    if not DASHBOARD_PASSWORD:
        return

    if st.session_state.get("authenticated"):
        return

    st.title("LD2450 Retail Heatmap")
    entered = st.text_input("Password", type="password")

    if entered == DASHBOARD_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()

    if entered:
        st.error("Incorrect password")

    st.stop()


def supabase_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


@st.cache_data(ttl=10)
def fetch_snapshots(hours: int, sensor_id: str | None) -> pd.DataFrame:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return pd.DataFrame()

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "select": "*",
        "captured_at": f"gte.{since.isoformat()}",
        "order": "captured_at.desc",
        "limit": "5000",
    }

    if sensor_id and sensor_id != "All":
        params["sensor_id"] = f"eq.{sensor_id}"

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/sensor_snapshots",
        headers=supabase_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    records = response.json()
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    return df.sort_values("captured_at")


@st.cache_data(ttl=30)
def fetch_sensor_ids() -> list[str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return []

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/sensor_snapshots",
        headers=supabase_headers(),
        params={"select": "sensor_id", "order": "captured_at.desc", "limit": "2000"},
        timeout=20,
    )
    response.raise_for_status()

    values = sorted({row["sensor_id"] for row in response.json() if row.get("sensor_id")})
    return values


def empty_matrix(rows: int = 3, cols: int = 3) -> list[list[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def matrix_add(a: list[list[float]], b: list[list[Any]]) -> list[list[float]]:
    for row_idx, row in enumerate(b or []):
        for col_idx, value in enumerate(row or []):
            if row_idx < len(a) and col_idx < len(a[row_idx]):
                a[row_idx][col_idx] += float(value or 0)
    return a


def aggregate_heat(df: pd.DataFrame) -> list[list[float]]:
    matrix = empty_matrix()

    for value in df.get("zone_heat", []):
        matrix_add(matrix, value)

    return matrix


def aggregate_now(df: pd.DataFrame) -> list[list[float]]:
    matrix = empty_matrix()

    for value in df.get("zone_now", []):
        matrix_add(matrix, value)

    return matrix


def zone_names(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    if df.empty:
        return ["LEFT", "CENTER", "RIGHT"], ["NEAR", "MID", "FAR"]

    latest = df.iloc[-1]
    x_names = latest.get("zone_x_names") or ["LEFT", "CENTER", "RIGHT"]
    y_names = latest.get("zone_y_names") or ["NEAR", "MID", "FAR"]
    return list(x_names), list(y_names)


def zone_dataframe(matrix: list[list[float]], x_names: list[str], y_names: list[str]) -> pd.DataFrame:
    rows = []
    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            rows.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "zone": f"{row_name}-{col_name}",
                    "heat": matrix[row_idx][col_idx],
                }
            )
    return pd.DataFrame(rows)


def render_heatmap(matrix: list[list[float]], x_names: list[str], y_names: list[str], title: str) -> None:
    display = list(reversed(matrix))
    y_display = list(reversed(y_names))

    fig = go.Figure(
        data=go.Heatmap(
            z=display,
            x=x_names,
            y=y_display,
            colorscale=[
                [0.0, "#17202b"],
                [0.35, "#287d8e"],
                [0.7, "#f6c350"],
                [1.0, "#ff5f57"],
            ],
            hovertemplate="Zone %{y}-%{x}<br>Heat %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        height=430,
        margin=dict(l=10, r=10, t=52, b=10),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font_color="#f2f6fb",
    )
    st.plotly_chart(fig, use_container_width=True)


def explode_hourly_zone_heat(df: pd.DataFrame, x_names: list[str], y_names: list[str]) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame(rows)

    temp = df.copy()
    temp["hour"] = temp["captured_at"].dt.floor("h")

    for _, record in temp.iterrows():
        for row_idx, row in enumerate(record.get("zone_heat") or []):
            for col_idx, heat in enumerate(row or []):
                rows.append(
                    {
                        "hour": record["hour"],
                        "zone": f"{y_names[row_idx]}-{x_names[col_idx]}",
                        "heat": float(heat or 0),
                    }
                )

    hourly = pd.DataFrame(rows)
    if hourly.empty:
        return hourly

    return hourly.groupby(["hour", "zone"], as_index=False)["heat"].sum()


def latest_targets_table(latest: pd.Series) -> pd.DataFrame:
    rows = []
    for target in latest.get("targets") or []:
        if not target.get("present"):
            continue
        rows.append(
            {
                "Target": target.get("id"),
                "Zone": target.get("zone"),
                "Distance mm": target.get("distanceMm"),
                "Angle deg": target.get("angleDeg"),
                "Side": target.get("side"),
                "Motion": target.get("motion"),
                "Speed cm/s": target.get("speedCms"),
                "X mm": target.get("xMm"),
                "Y mm": target.get("yMm"),
            }
        )
    return pd.DataFrame(rows)


require_password()

st.title("LD2450 Retail Heatmap")
st.caption("Historical occupancy and activity zones from ESP32 + HLK-LD2450 snapshots.")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    st.warning(
        "Supabase secrets are not configured yet. Add SUPABASE_URL and "
        "SUPABASE_SERVICE_ROLE_KEY in .streamlit/secrets.toml locally, "
        "or in Streamlit Cloud app secrets after deployment."
    )
    st.stop()

with st.sidebar:
    st.header("Filters")
    try:
        sensor_ids = ["All"] + fetch_sensor_ids()
    except requests.RequestException as exc:
        st.error(f"Could not read sensors from Supabase: {exc}")
        st.stop()

    sensor_id = st.selectbox("Sensor", sensor_ids)
    hours = st.slider("History window", min_value=1, max_value=168, value=24, step=1)
    st.caption("The dashboard refreshes from Supabase every few seconds.")
    if st.button("Refresh now"):
        st.cache_data.clear()

try:
    df = fetch_snapshots(hours=hours, sensor_id=sensor_id)
except requests.RequestException as exc:
    st.error(f"Could not read snapshots from Supabase: {exc}")
    st.stop()

if df.empty:
    st.info("No snapshots found yet. Check the ESP32 cloud settings and Supabase Edge Function logs.")
    st.stop()

latest = df.iloc[-1]
x_names, y_names = zone_names(df)
total_heat = aggregate_heat(df)
total_now = aggregate_now(df)
zone_totals = zone_dataframe(total_heat, x_names, y_names).sort_values("heat", ascending=False)

metric_cols = st.columns(4)
metric_cols[0].metric("People Now", int(latest["people_now"]))
metric_cols[1].metric("Snapshots", len(df))
metric_cols[2].metric("Most Active", zone_totals.iloc[0]["zone"])
metric_cols[3].metric("Heat Score", int(zone_totals.iloc[0]["heat"]))

left, right = st.columns([1.25, 1])

with left:
    render_heatmap(total_heat, x_names, y_names, f"Accumulated Activity Heat, Last {hours}h")

with right:
    render_heatmap(total_now, x_names, y_names, f"Presence Frequency, Last {hours}h")

st.subheader("How Heat Changed Over Time")
hourly = explode_hourly_zone_heat(df, x_names, y_names)
if not hourly.empty:
    fig = px.area(hourly, x="hour", y="heat", color="zone", line_group="zone")
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font_color="#f2f6fb",
        xaxis_title="Time",
        yaxis_title="Heat score",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data for time trend yet.")

table_cols = st.columns([1, 1])

with table_cols[0]:
    st.subheader("Hottest Zones")
    st.dataframe(zone_totals.reset_index(drop=True), use_container_width=True, hide_index=True)

with table_cols[1]:
    st.subheader("Latest Targets")
    targets = latest_targets_table(latest)
    if targets.empty:
        st.write("No current targets.")
    else:
        st.dataframe(targets, use_container_width=True, hide_index=True)

st.subheader("Snapshot Log")
st.dataframe(
    df[[
        "captured_at",
        "sensor_id",
        "people_now",
        "hottest_zone",
        "hottest_heat",
        "frames_count",
        "bad_frames_count",
    ]].sort_values("captured_at", ascending=False),
    use_container_width=True,
    hide_index=True,
)
