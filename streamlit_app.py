from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh


st.set_page_config(
    page_title="LD2450 Retail Intelligence",
    layout="wide",
)

LIVE_FEED_TIMEOUT_S = 30


CSS = """
<style>
  :root {
    --page: #f5f7fa;
    --ink: #111827;
    --muted: #667085;
    --line: #d9e0e8;
    --panel: #ffffff;
    --panel-soft: #f8fafc;
    --green: #0f9f6e;
    --amber: #b7791f;
    --red: #c2410c;
    --blue: #2563eb;
  }

  .stApp {
    background: var(--page);
    color: var(--ink);
  }

  [data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--line);
  }

  h1, h2, h3 {
    letter-spacing: 0;
  }

  .page-title {
    padding: 4px 0 10px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 14px;
  }

  .page-title h1 {
    margin: 0;
    font-size: 34px;
    line-height: 1.1;
    color: var(--ink);
  }

  .page-title p {
    margin: 8px 0 0;
    color: var(--muted);
    font-size: 15px;
  }

  .metric-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px 16px 14px;
    min-height: 118px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  .metric-card .label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
  }

  .metric-card .value {
    margin-top: 10px;
    color: var(--ink);
    font-size: clamp(22px, 2vw, 30px);
    font-weight: 760;
    line-height: 1.06;
    overflow-wrap: normal;
    word-break: normal;
    hyphens: none;
  }

  .metric-card .note {
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.35;
  }

  .status-ok {
    color: var(--green);
    font-weight: 700;
  }

  .status-warn {
    color: var(--amber);
    font-weight: 700;
  }

  .section-note {
    color: var(--muted);
    font-size: 13px;
    margin-top: -8px;
    margin-bottom: 12px;
  }

  .heatmap-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 14px 16px;
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  .heatmap-banner .title {
    color: var(--ink);
    font-size: 18px;
    font-weight: 760;
    line-height: 1.2;
  }

  .heatmap-banner .subtitle {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.35;
    margin-top: 4px;
  }

  .heatmap-legend {
    min-width: 240px;
  }

  .heatmap-legend .label-row {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 6px;
  }

  .heatmap-gradient {
    height: 12px;
    border-radius: 999px;
    border: 1px solid rgba(17, 24, 39, .08);
    background: linear-gradient(90deg, #eef4f7 0%, #9ad7ca 32%, #14956f 58%, #f0b84a 78%, #e86e32 100%);
  }

  .callout-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 15px 16px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    margin-bottom: 12px;
  }

  .callout-card .label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 750;
    letter-spacing: .06em;
    text-transform: uppercase;
  }

  .callout-card .value {
    color: var(--ink);
    font-size: 24px;
    line-height: 1.1;
    font-weight: 780;
    margin-top: 8px;
  }

  .callout-card .note {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.35;
    margin-top: 8px;
  }

  div[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  div[data-testid="stMetricLabel"] {
    color: var(--muted);
    font-weight: 700;
  }

  div[data-testid="stMetricValue"] {
    color: var(--ink);
  }

  .block-container {
    padding-top: 28px;
    padding-bottom: 44px;
  }
</style>
"""


def secret(name: str, default: str = "") -> str:
    return st.secrets.get(name, default)


SUPABASE_URL = secret("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = secret("SUPABASE_SERVICE_ROLE_KEY")
DASHBOARD_PASSWORD = secret("DASHBOARD_PASSWORD")
SNAPSHOT_COLUMNS = ",".join(
    [
        "captured_at",
        "sensor_id",
        "firmware",
        "people_now",
        "targets",
        "zone_now",
        "zone_heat",
        "zone_x_names",
        "zone_y_names",
        "zone_x_edges",
        "zone_y_edges",
        "frames_count",
        "bad_frames_count",
        "dropped_bytes",
        "rx_bytes",
        "last_frame_age_ms",
        "hottest_zone",
        "hottest_heat",
        "network",
    ]
)


def require_password() -> None:
    if not DASHBOARD_PASSWORD:
        return

    if st.session_state.get("authenticated"):
        return

    st.title("LD2450 Retail Intelligence")
    entered = st.text_input("Password", type="password")

    if entered == DASHBOARD_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()

    if entered:
        st.error("Incorrect password")

    st.stop()


def supabase_headers(prefer_count: bool = False) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer_count:
        headers["Prefer"] = "count=exact"
    return headers


def request_rows(params: dict[str, str], offset: int, page_size: int) -> list[dict[str, Any]]:
    page_params = dict(params)
    page_params["limit"] = str(page_size)
    page_params["offset"] = str(offset)

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/sensor_snapshots",
        headers=supabase_headers(),
        params=page_params,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=10)
def fetch_snapshots(hours: int, sensor_id: str | None, row_cap: int) -> pd.DataFrame:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return pd.DataFrame()

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "select": SNAPSHOT_COLUMNS,
        "captured_at": f"gte.{since.isoformat()}",
        "order": "captured_at.desc",
    }

    if sensor_id and sensor_id != "All":
        params["sensor_id"] = f"eq.{sensor_id}"

    rows: list[dict[str, Any]] = []
    page_size = 1000

    for offset in range(0, row_cap, page_size):
        page = request_rows(params, offset, min(page_size, row_cap - offset))
        rows.extend(page)
        if len(page) < page_size:
            break

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    return df.sort_values("captured_at").reset_index(drop=True)


@st.cache_data(ttl=30)
def fetch_sensor_ids() -> list[str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return []

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/sensor_snapshots",
        headers=supabase_headers(),
        params={"select": "sensor_id", "order": "captured_at.desc", "limit": "3000"},
        timeout=20,
    )
    response.raise_for_status()
    return sorted({row["sensor_id"] for row in response.json() if row.get("sensor_id")})


def empty_matrix(rows: int, cols: int) -> list[list[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def matrix_add(a: list[list[float]], b: list[list[Any]], multiplier: float = 1.0) -> list[list[float]]:
    for row_idx, row in enumerate(b or []):
        for col_idx, value in enumerate(row or []):
            if row_idx < len(a) and col_idx < len(a[row_idx]):
                a[row_idx][col_idx] += float(value or 0) * multiplier
    return a


def zone_config(df: pd.DataFrame) -> tuple[list[str], list[str], list[int], list[int]]:
    if df.empty:
        return ["LEFT", "CENTER", "RIGHT"], ["NEAR", "MID", "FAR"], [-2500, -800, 800, 2500], [250, 1500, 3500, 6000]

    latest = df.iloc[-1]
    x_names = list(latest.get("zone_x_names") or ["LEFT", "CENTER", "RIGHT"])
    y_names = list(latest.get("zone_y_names") or ["NEAR", "MID", "FAR"])
    x_edges = list(latest.get("zone_x_edges") or [-2500, -800, 800, 2500])
    y_edges = list(latest.get("zone_y_edges") or [250, 1500, 3500, 6000])
    return x_names, y_names, x_edges, y_edges


def add_durations(df: pd.DataFrame, max_gap_s: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    result = df.sort_values("captured_at").reset_index(drop=True).copy()
    next_delta = (result["captured_at"].shift(-1) - result["captured_at"]).dt.total_seconds()
    positive = next_delta[next_delta > 0]
    median_s = float(positive.median()) if not positive.empty else 10.0
    median_s = max(1.0, min(median_s, float(max_gap_s)))
    result["duration_s"] = next_delta.fillna(median_s).clip(lower=0, upper=max_gap_s)
    return result


def any_present(targets: Any) -> bool:
    return any(bool(target.get("present")) for target in targets or [])


def target_observations(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, record in df.iterrows():
        for target in record.get("targets") or []:
            if not target.get("present"):
                continue

            rows.append(
                {
                    "captured_at": record["captured_at"],
                    "duration_s": float(record.get("duration_s") or 0),
                    "sensor_id": record.get("sensor_id"),
                    "target_slot": target.get("id"),
                    "counted": bool(target.get("counted")),
                    "zone": target.get("zone"),
                    "zone_row": target.get("zoneRow"),
                    "zone_col": target.get("zoneCol"),
                    "x_mm": target.get("xMm"),
                    "y_mm": target.get("yMm"),
                    "distance_mm": target.get("distanceMm"),
                    "angle_deg": target.get("angleDeg"),
                    "side": target.get("side"),
                    "motion": target.get("motion"),
                    "speed_cms": target.get("speedCms"),
                    "resolution_mm": target.get("resolutionMm"),
                }
            )

    return pd.DataFrame(rows)


def estimated_entries(series: pd.Series) -> int:
    if series.empty:
        return 0

    counts = series.fillna(0).astype(int).clip(lower=0)
    previous = counts.shift(1).fillna(0)
    entries = (counts - previous).clip(lower=0).sum()
    return int(entries)


def occupied_sessions(df: pd.DataFrame, session_gap_s: int) -> pd.DataFrame:
    sessions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    previous_time: pd.Timestamp | None = None

    for _, record in df.iterrows():
        now = record["captured_at"]
        occupied = int(record.get("people_now") or 0) > 0
        gap_s = None if previous_time is None else (now - previous_time).total_seconds()
        split = gap_s is not None and gap_s > session_gap_s

        if occupied and (active is None or split):
            active = {
                "start": now,
                "end": now,
                "peak_people": int(record.get("people_now") or 0),
                "person_seconds": 0.0,
                "dwell_s": 0.0,
            }
        elif not occupied and active is not None:
            sessions.append(active)
            active = None

        if occupied and active is not None:
            active["end"] = now
            active["peak_people"] = max(active["peak_people"], int(record.get("people_now") or 0))
            duration_s = float(record.get("duration_s") or 0)
            active["dwell_s"] += duration_s
            active["person_seconds"] += duration_s * int(record.get("people_now") or 0)

        previous_time = now

    if active is not None:
        sessions.append(active)

    result = pd.DataFrame(sessions)
    if result.empty:
        return result

    return result


def zone_summary(df: pd.DataFrame, x_names: list[str], y_names: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    zone_seconds = empty_matrix(len(y_names), len(x_names))
    zone_occupied_seconds = empty_matrix(len(y_names), len(x_names))
    zone_heat = empty_matrix(len(y_names), len(x_names))

    for _, record in df.iterrows():
        duration_s = float(record.get("duration_s") or 0)
        now_matrix = record.get("zone_now") or []
        heat_matrix = record.get("zone_heat") or []

        matrix_add(zone_seconds, now_matrix, duration_s)
        matrix_add(zone_heat, heat_matrix, 1.0)

        occupied_matrix = [[1 if float(cell or 0) > 0 else 0 for cell in row] for row in now_matrix]
        matrix_add(zone_occupied_seconds, occupied_matrix, duration_s)

    total_zone_seconds = sum(sum(row) for row in zone_seconds)

    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            zone = f"{row_name}-{col_name}"
            dwell_s = zone_seconds[row_idx][col_idx]
            occupied_s = zone_occupied_seconds[row_idx][col_idx]
            heat = zone_heat[row_idx][col_idx]
            rows.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "zone": zone,
                    "dwell_minutes": dwell_s / 60.0,
                    "occupied_minutes": occupied_s / 60.0,
                    "activity_heat": heat,
                    "dwell_share": (dwell_s / total_zone_seconds) if total_zone_seconds else 0.0,
                }
            )

    return pd.DataFrame(rows).sort_values("dwell_minutes", ascending=False)


def zone_visit_counts(df: pd.DataFrame, x_names: list[str], y_names: list[str]) -> dict[str, int]:
    visits: dict[str, int] = {}

    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            zone = f"{row_name}-{col_name}"
            values = []
            for _, record in df.iterrows():
                matrix = record.get("zone_now") or []
                if row_idx < len(matrix) and col_idx < len(matrix[row_idx]):
                    values.append(int(matrix[row_idx][col_idx] or 0))
                else:
                    values.append(0)

            visits[zone] = estimated_entries(pd.Series(values))

    return visits


def summarize_period(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "snapshots": 0,
            "people_now": 0,
            "peak_people": 0,
            "avg_people": 0.0,
            "person_minutes": 0.0,
            "estimated_visits": 0,
            "avg_dwell_s": 0.0,
            "engaged_minutes": 0.0,
            "engagement_rate": 0.0,
            "passerby_snapshots": 0,
        }

    durations = df.get("duration_s", pd.Series([0] * len(df))).astype(float)
    people = df["people_now"].fillna(0).astype(int).clip(lower=0)
    person_seconds = float((people * durations).sum())
    estimated_visits = max(estimated_entries(people), int((people > 0).sum() > 0))
    target_present = df["targets"].map(any_present) if "targets" in df else pd.Series([False] * len(df))
    engaged = people > 0
    sessions = occupied_sessions(df, session_gap_s=90)
    dwell_s = person_seconds / estimated_visits if estimated_visits else 0.0

    return {
        "snapshots": float(len(df)),
        "people_now": float(people.iloc[-1]) if not people.empty else 0.0,
        "peak_people": float(people.max()) if not people.empty else 0.0,
        "avg_people": float(person_seconds / max(durations.sum(), 1.0)),
        "person_minutes": person_seconds / 60.0,
        "estimated_visits": float(max(estimated_visits, len(sessions))),
        "avg_dwell_s": dwell_s,
        "engaged_minutes": float(durations[engaged].sum() / 60.0),
        "engagement_rate": float(engaged.sum() / max(target_present.sum(), 1)),
        "passerby_snapshots": float((target_present & ~engaged).sum()),
    }


def format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    return f"{minutes / 60:.1f}h"


def format_delta(current: float, previous: float, suffix: str = "") -> str | None:
    if previous <= 0:
        return None
    change = ((current - previous) / previous) * 100
    return f"{change:+.1f}%{suffix}"


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="callout-card">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_label(value: Any) -> str:
    return str(value or "").replace("_", " ").replace("-", " ")


def format_minutes(value: float) -> str:
    if value <= 0:
        return "0m"
    if value < 1:
        return "<1m"
    if value < 60:
        return f"{value:.1f}m"
    return f"{value / 60:.1f}h"


def coerce_matrix(matrix: Any, rows: int, cols: int) -> list[list[float]]:
    coerced = empty_matrix(rows, cols)
    for row_idx, row in enumerate(matrix or []):
        if row_idx >= rows:
            break
        for col_idx, value in enumerate(row or []):
            if col_idx >= cols:
                break
            coerced[row_idx][col_idx] = float(value or 0)
    return coerced


def current_zone_labels(current_matrix: list[list[float]], x_names: list[str], y_names: list[str]) -> list[str]:
    labels: list[str] = []
    for row_idx, row in enumerate(current_matrix):
        for col_idx, value in enumerate(row):
            count = int(value or 0)
            if count <= 0 or row_idx >= len(y_names) or col_idx >= len(x_names):
                continue
            zone = clean_label(f"{y_names[row_idx]} {x_names[col_idx]}").upper()
            labels.append(f"{zone} ({count})")
    return labels


def current_target_points(latest: pd.Series, is_live: bool, x_edges: list[int], y_edges: list[int]) -> pd.DataFrame:
    if not is_live:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for target in latest.get("targets") or []:
        if not target.get("present") or not target.get("counted"):
            continue

        row_idx = target.get("zoneRow")
        col_idx = target.get("zoneCol")
        if row_idx is None or col_idx is None:
            continue
        row_idx = int(row_idx)
        col_idx = int(col_idx)
        if row_idx < 0 or col_idx < 0 or row_idx + 1 >= len(y_edges) or col_idx + 1 >= len(x_edges):
            continue

        x_mm = float(target.get("xMm") or 0)
        y_mm = float(target.get("yMm") or 0)
        x_span = max(float(x_edges[col_idx + 1] - x_edges[col_idx]), 1.0)
        y_span = max(float(y_edges[row_idx + 1] - y_edges[row_idx]), 1.0)
        x_ratio = min(max((x_mm - x_edges[col_idx]) / x_span, 0.08), 0.92)
        y_ratio = min(max((y_mm - y_edges[row_idx]) / y_span, 0.12), 0.88)

        rows.append(
            {
                "x": col_idx + x_ratio,
                "y": row_idx + y_ratio,
                "id": target.get("id"),
                "zone": target.get("zone"),
                "distance_mm": target.get("distanceMm"),
                "motion": target.get("motion"),
            }
        )

    return pd.DataFrame(rows)


def render_heatmap_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="heatmap-banner">
          <div>
            <div class="title">{title}</div>
            <div class="subtitle">{subtitle}</div>
          </div>
          <div class="heatmap-legend">
            <div class="label-row"><span>Low dwell</span><span>High dwell</span></div>
            <div class="heatmap-gradient"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_retail_floor_heatmap(
    dwell_matrix: list[list[float]],
    current_matrix: list[list[float]],
    current_targets: pd.DataFrame,
    x_names: list[str],
    y_names: list[str],
    title: str,
    is_live: bool,
) -> None:
    rows = len(y_names)
    cols = len(x_names)
    dwell = coerce_matrix(dwell_matrix, rows, cols)
    current = coerce_matrix(current_matrix if is_live else [], rows, cols)
    max_value = max([value for row in dwell for value in row] + [0.0])

    display_text: list[list[str]] = []
    customdata: list[list[list[Any]]] = []
    for row_idx in reversed(range(rows)):
        text_row: list[str] = []
        custom_row: list[list[Any]] = []
        for col_idx in range(cols):
            dwell_value = dwell[row_idx][col_idx]
            current_count = int(current[row_idx][col_idx])
            zone_label = clean_label(f"{y_names[row_idx]} {x_names[col_idx]}").upper()
            current_label = f"<br><b>NOW {current_count}</b>" if current_count else ""
            dwell_label = format_minutes(dwell_value) if dwell_value else ""
            text_row.append(f"<b>{dwell_label}</b>{current_label}")
            custom_row.append([zone_label, dwell_value, current_count])
        display_text.append(text_row)
        customdata.append(custom_row)

    z = list(reversed(dwell))
    y_display = [clean_label(name).upper() for name in reversed(y_names)]
    x_display = [clean_label(name).upper() for name in x_names]
    x_values = [col_idx + 0.5 for col_idx in range(cols)]
    y_values = [row_idx + 0.5 for row_idx in reversed(range(rows))]
    colorscale = [
        [0.0, "#eef4f7"],
        [0.18, "#cfece6"],
        [0.42, "#78c7b2"],
        [0.62, "#14956f"],
        [0.80, "#f0b84a"],
        [1.0, "#e86e32"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_values,
            y=y_values,
            text=display_text,
            customdata=customdata,
            texttemplate="%{text}",
            colorscale=colorscale,
            zmin=0,
            zmax=max(max_value, 1.0),
            xgap=9,
            ygap=9,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Dwell: %{customdata[1]:.2f} person-min<br>"
                "People now: %{customdata[2]}<extra></extra>"
            ),
            colorbar=dict(
                title="person-min",
                thickness=14,
                len=0.82,
                outlinewidth=0,
            ),
        )
    )

    if is_live and not current_targets.empty:
        plotted = current_targets.copy()
        fig.add_trace(
            go.Scatter(
                x=plotted["x"],
                y=plotted["y"],
                mode="markers+text",
                marker=dict(
                    size=30,
                    color="#111827",
                    symbol="circle",
                    line=dict(color="#ffffff", width=3),
                ),
                text=plotted["id"].map(lambda value: f"{int(value)}" if pd.notna(value) else ""),
                textfont=dict(color="#ffffff", size=13),
                customdata=plotted[["zone", "distance_mm", "motion"]],
                hovertemplate=(
                    "<b>Target %{text}</b><br>"
                    "%{customdata[0]}<br>"
                    "%{customdata[1]} mm | %{customdata[2]}<extra></extra>"
                ),
                name="Current target",
            )
        )

    sensor_x = cols / 2
    fig.add_shape(
        type="path",
        path=f"M {sensor_x - 0.18},-0.24 L {sensor_x + 0.18},-0.24 L {sensor_x},0.08 Z",
        fillcolor="#111827",
        line=dict(color="#111827", width=1),
    )
    fig.add_annotation(
        x=sensor_x,
        y=-0.36,
        text="RADAR",
        showarrow=False,
        font=dict(size=11, color="#475467"),
    )

    fig.update_layout(
        title=title,
        height=560,
        margin=dict(l=10, r=10, t=58, b=20),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#111827",
        showlegend=False,
    )
    fig.update_traces(textfont=dict(size=16, color="#111827"), selector=dict(type="heatmap"))
    fig.update_xaxes(
        side="top",
        ticks="",
        showgrid=False,
        zeroline=False,
        title="",
        range=[0, cols],
        tickmode="array",
        tickvals=x_values,
        ticktext=x_display,
    )
    fig.update_yaxes(
        ticks="",
        showgrid=False,
        zeroline=False,
        title="Distance from radar",
        range=[-0.46, rows],
        tickmode="array",
        tickvals=[row_idx + 0.5 for row_idx in range(rows)],
        ticktext=[clean_label(name).upper() for name in y_names],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_heatmap(matrix: list[list[float]], x_names: list[str], y_names: list[str], title: str, unit: str) -> None:
    display = list(reversed(matrix))
    y_display = list(reversed(y_names))
    text = [[f"{value:.1f}" if value else "0" for value in row] for row in display]

    fig = go.Figure(
        data=go.Heatmap(
            z=display,
            x=x_names,
            y=y_display,
            text=text,
            texttemplate="%{text}",
            colorscale=[
                [0.0, "#f1f5f9"],
                [0.25, "#99d4c4"],
                [0.55, "#2f9e7e"],
                [0.78, "#f2b84b"],
                [1.0, "#c2410c"],
            ],
            hovertemplate="Zone %{y}-%{x}<br>%{z:.2f} " + unit + "<extra></extra>",
            colorbar=dict(title=unit),
        )
    )
    fig.update_layout(
        title=title,
        height=430,
        margin=dict(l=10, r=10, t=52, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#111827",
        xaxis=dict(side="top"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_floor_map(targets: pd.DataFrame, x_edges: list[int], y_edges: list[int], x_names: list[str], y_names: list[str]) -> None:
    fig = go.Figure()

    for row_idx, row_name in enumerate(y_names):
        if row_idx + 1 >= len(y_edges):
            continue
        for col_idx, col_name in enumerate(x_names):
            if col_idx + 1 >= len(x_edges):
                continue
            fig.add_shape(
                type="rect",
                x0=x_edges[col_idx],
                x1=x_edges[col_idx + 1],
                y0=y_edges[row_idx],
                y1=y_edges[row_idx + 1],
                line=dict(color="#cbd5e1", width=1),
                fillcolor="rgba(248,250,252,.55)",
            )
            fig.add_annotation(
                x=(x_edges[col_idx] + x_edges[col_idx + 1]) / 2,
                y=(y_edges[row_idx] + y_edges[row_idx + 1]) / 2,
                text=f"{row_name}-{col_name}",
                showarrow=False,
                font=dict(size=10, color="#64748b"),
            )

    if not targets.empty:
        recent = targets.tail(500).copy()
        recent["display_time"] = recent["captured_at"].dt.strftime("%H:%M:%S")
        fig.add_trace(
            go.Scatter(
                x=recent["x_mm"],
                y=recent["y_mm"],
                mode="markers",
                marker=dict(
                    size=recent["counted"].map({True: 11, False: 7}),
                    color=recent["counted"].map({True: "#0f9f6e", False: "#c2410c"}),
                    opacity=0.72,
                    line=dict(width=1, color="#ffffff"),
                ),
                text=recent["zone"],
                customdata=recent[["display_time", "distance_mm", "motion", "speed_cms"]],
                hovertemplate=(
                    "%{text}<br>X %{x} mm | Y %{y} mm<br>"
                    "%{customdata[0]} | %{customdata[1]} mm<br>"
                    "%{customdata[2]} | %{customdata[3]} cm/s<extra></extra>"
                ),
                name="Target observations",
            )
        )

    fig.add_shape(type="line", x0=0, x1=0, y0=min(y_edges), y1=max(y_edges), line=dict(color="#94a3b8", width=1, dash="dot"))
    fig.update_layout(
        title="Target Position Cloud",
        height=520,
        margin=dict(l=10, r=10, t=52, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#111827",
        xaxis_title="Left / right position, mm",
        yaxis_title="Distance from sensor, mm",
        showlegend=False,
    )
    fig.update_yaxes(range=[max(y_edges), min(y_edges)], autorange=False)
    st.plotly_chart(fig, use_container_width=True)


def explode_hourly_zone_dwell(df: pd.DataFrame, x_names: list[str], y_names: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame(rows)

    temp = df.copy()
    temp["hour"] = temp["captured_at"].dt.floor("h")

    for _, record in temp.iterrows():
        duration_s = float(record.get("duration_s") or 0)
        for row_idx, row in enumerate(record.get("zone_now") or []):
            for col_idx, people in enumerate(row or []):
                if row_idx < len(y_names) and col_idx < len(x_names):
                    rows.append(
                        {
                            "hour": record["hour"],
                            "zone": f"{y_names[row_idx]}-{x_names[col_idx]}",
                            "person_minutes": float(people or 0) * duration_s / 60.0,
                        }
                    )

    hourly = pd.DataFrame(rows)
    if hourly.empty:
        return hourly

    return hourly.groupby(["hour", "zone"], as_index=False)["person_minutes"].sum()


def latest_targets_table(latest: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in latest.get("targets") or []:
        if not target.get("present"):
            continue
        rows.append(
            {
                "Target": target.get("id"),
                "Counted": target.get("counted"),
                "Zone": target.get("zone"),
                "Distance mm": target.get("distanceMm"),
                "Angle deg": target.get("angleDeg"),
                "Side": target.get("side"),
                "Motion": target.get("motion"),
                "Speed cm/s": target.get("speedCms"),
                "Resolution mm": target.get("resolutionMm"),
                "X mm": target.get("xMm"),
                "Y mm": target.get("yMm"),
            }
        )
    return pd.DataFrame(rows)


require_password()
st.markdown(CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-title">
      <h1>LD2450 Retail Intelligence</h1>
      <p>Occupancy, dwell, zone engagement, and campaign-lift analytics from ESP32 + HLK-LD2450 snapshots.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st_autorefresh(interval=60_000, key="ld2450_dashboard_autorefresh")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    st.warning(
        "Supabase secrets are not configured yet. Add SUPABASE_URL and "
        "SUPABASE_SERVICE_ROLE_KEY in .streamlit/secrets.toml locally, "
        "or in Streamlit Cloud app secrets after deployment."
    )
    st.stop()

with st.sidebar:
    st.header("Controls")
    try:
        sensor_ids = ["All"] + fetch_sensor_ids()
    except requests.RequestException as exc:
        st.error(f"Could not read sensors from Supabase: {exc}")
        st.stop()

    sensor_id = st.selectbox("Sensor", sensor_ids)
    hours = st.select_slider("Analysis window", options=[1, 3, 6, 12, 24, 48, 72, 168], value=24)
    session_gap_s = st.slider("Session merge gap", min_value=20, max_value=180, value=90, step=10)
    max_gap_s = st.slider("Max sample gap", min_value=15, max_value=180, value=45, step=5)
    row_cap = st.select_slider("Row budget", options=[1000, 3000, 5000, 10000], value=1000)
    st.caption("Auto-refreshes every 60 seconds. Increase row budget only when you need a longer history.")
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()

try:
    all_df = fetch_snapshots(hours=hours * 2, sensor_id=sensor_id, row_cap=row_cap)
except requests.RequestException as exc:
    st.error(f"Could not read snapshots from Supabase: {exc}")
    st.stop()

if all_df.empty:
    st.info("No snapshots found yet. Check the ESP32 cloud settings and Supabase Edge Function logs.")
    st.stop()

all_df = add_durations(all_df, max_gap_s=max_gap_s)
cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
previous_cutoff = cutoff - timedelta(hours=hours)
df = all_df[all_df["captured_at"] >= cutoff].copy().reset_index(drop=True)
previous_df = all_df[(all_df["captured_at"] >= previous_cutoff) & (all_df["captured_at"] < cutoff)].copy().reset_index(drop=True)

if df.empty:
    st.info("No snapshots found in the selected analysis window.")
    st.stop()

x_names, y_names, x_edges, y_edges = zone_config(df)
summary = summarize_period(df)
previous_summary = summarize_period(previous_df)
latest = df.iloc[-1]
targets = target_observations(df)
zone_table = zone_summary(df, x_names, y_names)
visits_by_zone = zone_visit_counts(df, x_names, y_names)
zone_table["estimated_visits"] = zone_table["zone"].map(visits_by_zone).fillna(0).astype(int)
zone_table["avg_dwell_s"] = zone_table.apply(
    lambda row: (row["dwell_minutes"] * 60 / row["estimated_visits"]) if row["estimated_visits"] else 0,
    axis=1,
)

zone_dwell_matrix = empty_matrix(len(y_names), len(x_names))
zone_occupied_matrix = empty_matrix(len(y_names), len(x_names))
for _, record in df.iterrows():
    duration_s = float(record.get("duration_s") or 0)
    matrix_add(zone_dwell_matrix, record.get("zone_now") or [], duration_s / 60.0)
    occupied = [[1 if float(cell or 0) > 0 else 0 for cell in row] for row in (record.get("zone_now") or [])]
    matrix_add(zone_occupied_matrix, occupied, duration_s / 60.0)

sessions = occupied_sessions(df, session_gap_s=session_gap_s)
latest_age_s = (datetime.now(timezone.utc) - latest["captured_at"].to_pydatetime()).total_seconds()
is_live = latest_age_s <= LIVE_FEED_TIMEOUT_S
last_people_now = int(summary["people_now"])
health_text = "Online" if is_live else "Offline"
health_class = "status-ok" if is_live else "status-warn"

if not is_live:
    st.warning(
        "Live radar feed is stale. "
        f"The last snapshot arrived {format_seconds(latest_age_s)} ago and reported "
        f"{last_people_now} {'person' if last_people_now == 1 else 'people'}. "
        "Treat live occupancy as unknown until the ESP32 starts uploading again."
    )

latest_zone_now = coerce_matrix(latest.get("zone_now") or [], len(y_names), len(x_names))
current_heatmap_matrix = latest_zone_now if is_live else empty_matrix(len(y_names), len(x_names))
current_targets = current_target_points(latest, is_live, x_edges, y_edges)
active_zone_labels = current_zone_labels(current_heatmap_matrix, x_names, y_names)
active_zone_text = ", ".join(active_zone_labels[:3]) if active_zone_labels else ("Clear" if is_live else "Offline")
top_zone = zone_table.iloc[0]["zone"] if not zone_table.empty else "none"
top_zone_label = clean_label(top_zone).upper()

view_options = ["Heatmap", "Executive View", "Zones", "Dwell", "Campaign Impact", "Targets", "Data Health"]
active_view = st.radio("View", view_options, horizontal=True, label_visibility="collapsed")

if active_view == "Heatmap":
    render_heatmap_banner(
        "Retail Floor Heatmap",
        f"{hours}h dwell depth with live occupancy overlay. Darker cells held attention longer.",
    )
    render_retail_floor_heatmap(
        zone_dwell_matrix,
        current_heatmap_matrix,
        current_targets,
        x_names,
        y_names,
        "Dwell Depth by Zone",
        is_live,
    )

    metric_cols = st.columns(5)
    with metric_cols[0]:
        people_now_label = str(last_people_now) if is_live else "--"
        people_now_note = (
            f"<span class='{health_class}'>{health_text}</span> | {latest_age_s:.0f}s ago"
            if is_live
            else f"<span class='{health_class}'>{health_text}</span> | last was {last_people_now}"
        )
        metric_card("People Now", people_now_label, people_now_note)
    with metric_cols[1]:
        metric_card("Estimated Visits", f"{int(summary['estimated_visits'])}", f"{int(summary['peak_people'])} peak occupancy")
    with metric_cols[2]:
        metric_card("Avg Dwell", format_seconds(summary["avg_dwell_s"]), f"{summary['person_minutes']:.1f} person-min total")
    with metric_cols[3]:
        metric_card("Engagement", f"{summary['engagement_rate'] * 100:.0f}%", f"{summary['engaged_minutes']:.1f} occupied minutes")
    with metric_cols[4]:
        metric_card("Top Zone", top_zone_label, f"{zone_table.iloc[0]['dwell_minutes']:.1f} dwell min" if not zone_table.empty else "No dwell yet")

    insight_cols = st.columns(4)
    with insight_cols[0]:
        callout_card("Current Position", active_zone_text, "Live zone count" if is_live else "Waiting for fresh ESP32 uploads")
    with insight_cols[1]:
        if not zone_table.empty:
            top = zone_table.iloc[0]
            callout_card(
                "Deepest Zone",
                clean_label(top["zone"]).upper(),
                f"{format_minutes(float(top['dwell_minutes']))} dwell in selected window",
            )
    with insight_cols[2]:
        if not zone_table.empty:
            top = zone_table.iloc[0]
            callout_card(
                "Attention Share",
                f"{float(top['dwell_share']) * 100:.0f}%",
                "Share of all measured dwell time",
            )
    with insight_cols[3]:
        callout_card("Freshness", health_text, f"Last upload {format_seconds(latest_age_s)} ago")

    st.subheader("Zone Ranking")
    ranking = zone_table.head(8).copy()
    if not ranking.empty:
        ranking["Zone"] = ranking["zone"].map(lambda value: clean_label(value).upper())
        ranking["Dwell"] = ranking["dwell_minutes"].map(format_minutes)
        ranking["Attention share"] = (ranking["dwell_share"] * 100).round(1)
        st.dataframe(
            ranking[["Zone", "Dwell", "occupied_minutes", "estimated_visits", "Attention share"]].rename(
                columns={
                    "occupied_minutes": "Occupied min",
                    "estimated_visits": "Visits",
                }
            ).round(2),
            use_container_width=True,
            hide_index=True,
        )

elif active_view == "Executive View":
    left, right = st.columns([1.25, 1])
    with left:
        timeline = df[["captured_at", "people_now"]].copy()
        fig = px.area(timeline, x="captured_at", y="people_now", title=f"Occupancy Timeline, Last {hours}h")
        fig.update_traces(line_color="#0f9f6e", fillcolor="rgba(15,159,110,.18)")
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=52, b=10),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font_color="#111827",
            xaxis_title="Time",
            yaxis_title="People",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        ranked = zone_table.head(8).copy()
        fig = px.bar(
            ranked.sort_values("dwell_minutes"),
            x="dwell_minutes",
            y="zone",
            orientation="h",
            title="Top Engagement Zones",
            color="dwell_share",
            color_continuous_scale=["#99d4c4", "#0f9f6e", "#f2b84b"],
        )
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=52, b=10),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font_color="#111827",
            xaxis_title="Person-minutes",
            yaxis_title="",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Retail Readout")
    readout_cols = st.columns(4)
    readout_cols[0].metric(
        "Avg People Present",
        f"{summary['avg_people']:.2f}",
        format_delta(summary["avg_people"], previous_summary["avg_people"]),
    )
    readout_cols[1].metric(
        "Person-Minutes",
        f"{summary['person_minutes']:.1f}",
        format_delta(summary["person_minutes"], previous_summary["person_minutes"]),
    )
    readout_cols[2].metric(
        "Passerby Snapshots",
        f"{int(summary['passerby_snapshots'])}",
        format_delta(summary["passerby_snapshots"], previous_summary["passerby_snapshots"]),
    )
    readout_cols[3].metric(
        "Samples",
        f"{int(summary['snapshots'])}",
        f"{len(previous_df)} previous",
    )

elif active_view == "Zones":
    left, right = st.columns(2)
    with left:
        render_retail_floor_heatmap(
            zone_dwell_matrix,
            current_heatmap_matrix,
            current_targets,
            x_names,
            y_names,
            "Zone Dwell Heatmap",
            is_live,
        )
    with right:
        render_heatmap(zone_occupied_matrix, x_names, y_names, "Zone Occupied-Time Heatmap", "min")

    st.subheader("Zone Performance")
    display_zone_table = zone_table.copy()
    display_zone_table["dwell_share"] = (display_zone_table["dwell_share"] * 100).round(1)
    display_zone_table["avg_dwell"] = display_zone_table["avg_dwell_s"].map(format_seconds)
    display_zone_table = display_zone_table[
        ["zone", "dwell_minutes", "occupied_minutes", "estimated_visits", "avg_dwell", "dwell_share", "activity_heat"]
    ].rename(
        columns={
            "zone": "Zone",
            "dwell_minutes": "Dwell person-min",
            "occupied_minutes": "Occupied min",
            "estimated_visits": "Estimated visits",
            "avg_dwell": "Avg dwell",
            "dwell_share": "Dwell share %",
            "activity_heat": "Activity heat",
        }
    )
    st.dataframe(display_zone_table.round(2), use_container_width=True, hide_index=True)
    st.download_button(
        "Download zone performance CSV",
        data=display_zone_table.to_csv(index=False).encode("utf-8"),
        file_name="ld2450_zone_performance.csv",
        mime="text/csv",
    )

elif active_view == "Dwell":
    left, right = st.columns([1, 1])
    with left:
        hourly = explode_hourly_zone_dwell(df, x_names, y_names)
        if not hourly.empty:
            fig = px.area(hourly, x="hour", y="person_minutes", color="zone", title="Dwell Trend by Zone")
            fig.update_layout(
                height=430,
                margin=dict(l=10, r=10, t=52, b=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
                xaxis_title="Time",
                yaxis_title="Person-minutes",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for dwell trend yet.")

    with right:
        if not sessions.empty:
            sessions_display = sessions.copy()
            sessions_display["dwell_min"] = sessions_display["dwell_s"] / 60
            fig = px.histogram(sessions_display, x="dwell_min", nbins=20, title="Estimated Session Dwell Distribution")
            fig.update_traces(marker_color="#2563eb")
            fig.update_layout(
                height=430,
                margin=dict(l=10, r=10, t=52, b=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
                xaxis_title="Dwell minutes",
                yaxis_title="Sessions",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No occupied sessions in this window.")

    st.subheader("Recent Sessions")
    if sessions.empty:
        st.write("No occupied sessions.")
    else:
        recent_sessions = sessions.tail(20).copy()
        recent_sessions["dwell"] = recent_sessions["dwell_s"].map(format_seconds)
        recent_sessions["person_minutes"] = recent_sessions["person_seconds"] / 60
        st.dataframe(
            recent_sessions[["start", "end", "peak_people", "dwell", "person_minutes"]].sort_values("start", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

elif active_view == "Campaign Impact":
    st.markdown('<div class="section-note">Current window compared with the immediately preceding window of the same length.</div>', unsafe_allow_html=True)
    comp_cols = st.columns(4)
    comp_cols[0].metric(
        "Visits",
        f"{int(summary['estimated_visits'])}",
        format_delta(summary["estimated_visits"], previous_summary["estimated_visits"]),
    )
    comp_cols[1].metric(
        "Dwell Person-Min",
        f"{summary['person_minutes']:.1f}",
        format_delta(summary["person_minutes"], previous_summary["person_minutes"]),
    )
    comp_cols[2].metric(
        "Avg Dwell",
        format_seconds(summary["avg_dwell_s"]),
        format_delta(summary["avg_dwell_s"], previous_summary["avg_dwell_s"]),
    )
    comp_cols[3].metric(
        "Engagement Rate",
        f"{summary['engagement_rate'] * 100:.0f}%",
        format_delta(summary["engagement_rate"], previous_summary["engagement_rate"]),
    )

    previous_x, previous_y, _, _ = zone_config(previous_df) if not previous_df.empty else (x_names, y_names, x_edges, y_edges)
    previous_zone_table = zone_summary(previous_df, previous_x, previous_y) if not previous_df.empty else pd.DataFrame()
    if not previous_zone_table.empty:
        comparison = zone_table[["zone", "dwell_minutes", "estimated_visits"]].merge(
            previous_zone_table[["zone", "dwell_minutes"]].rename(columns={"dwell_minutes": "previous_dwell_minutes"}),
            on="zone",
            how="left",
        )
        comparison["previous_dwell_minutes"] = comparison["previous_dwell_minutes"].fillna(0)
        comparison["dwell_lift_pct"] = comparison.apply(
            lambda row: ((row["dwell_minutes"] - row["previous_dwell_minutes"]) / row["previous_dwell_minutes"] * 100)
            if row["previous_dwell_minutes"] > 0
            else None,
            axis=1,
        )
        st.subheader("Zone Lift")
        st.dataframe(
            comparison.sort_values("dwell_minutes", ascending=False).rename(
                columns={
                    "zone": "Zone",
                    "dwell_minutes": "Current dwell min",
                    "estimated_visits": "Current visits",
                    "previous_dwell_minutes": "Previous dwell min",
                    "dwell_lift_pct": "Dwell lift %",
                }
            ).round(2),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Previous-period comparison will appear once there is enough history.")

elif active_view == "Targets":
    render_floor_map(targets, x_edges, y_edges, x_names, y_names)

    left, right = st.columns(2)
    with left:
        if not targets.empty:
            motion = targets.groupby("motion", dropna=False).size().reset_index(name="observations")
            fig = px.pie(motion, names="motion", values="observations", title="Motion Mix")
            fig.update_layout(height=360, paper_bgcolor="#ffffff", font_color="#111827")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No target observations in this window.")

    with right:
        latest_targets = latest_targets_table(latest)
        st.subheader("Latest Targets")
        if latest_targets.empty:
            st.write("No current targets.")
        else:
            st.dataframe(latest_targets, use_container_width=True, hide_index=True)

elif active_view == "Data Health":
    latest_network = latest.get("network") or {}
    latest_raw = latest.get("raw_payload") or {}
    latest_snapshot = latest_raw.get("snapshot") or {}
    latest_cloud = latest_snapshot.get("cloud") or {}
    health_cols = st.columns(4)
    health_cols[0].metric("Last Upload Age", format_seconds(latest_age_s))
    health_cols[1].metric("Frame Count", int(latest.get("frames_count") or 0))
    health_cols[2].metric("Bad Frames", int(latest.get("bad_frames_count") or 0))
    health_cols[3].metric("Cloud Status", latest_cloud.get("lastStatusCode", "unknown"))

    details = {
        "sensor_id": latest.get("sensor_id"),
        "captured_at": str(latest.get("captured_at")),
        "network_mode": latest_network.get("mode"),
        "ip": latest_network.get("ip"),
        "ssid": latest_network.get("ssid"),
        "rssi_dbm": latest_network.get("rssiDbm"),
        "cloud_ok_count": latest_cloud.get("okCount"),
        "cloud_fail_count": latest_cloud.get("failCount"),
        "last_cloud_message": latest_cloud.get("message"),
        "rows_loaded": len(all_df),
        "analysis_rows": len(df),
    }
    st.subheader("Device Diagnostics")
    st.json(details)

    st.subheader("Snapshot Log")
    st.dataframe(
        df[
            [
                "captured_at",
                "sensor_id",
                "people_now",
                "hottest_zone",
                "hottest_heat",
                "frames_count",
                "bad_frames_count",
                "last_frame_age_ms",
            ]
        ].sort_values("captured_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
