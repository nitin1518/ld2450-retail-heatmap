from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
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

  .dashboard-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(240px, .78fr) minmax(240px, .78fr);
    gap: 12px;
    align-items: stretch;
    margin: 2px 0 14px;
  }

  .hero-primary,
  .hero-side {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  .hero-primary {
    position: relative;
    overflow: hidden;
    padding: 18px 20px;
    border-left: 5px solid var(--green);
  }

  .hero-primary:after {
    content: "";
    position: absolute;
    inset: 0 0 0 auto;
    width: 38%;
    background: linear-gradient(90deg, rgba(255,255,255,0), rgba(154,215,202,.26));
    pointer-events: none;
  }

  .hero-eyebrow {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
  }

  .hero-title {
    margin-top: 8px;
    color: var(--ink);
    font-size: clamp(28px, 3vw, 42px);
    line-height: 1.02;
    font-weight: 840;
    max-width: 760px;
  }

  .hero-subtitle {
    margin-top: 10px;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.45;
    max-width: 720px;
  }

  .hero-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }

  .hero-pill {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    border: 1px solid rgba(17, 24, 39, .08);
    border-radius: 999px;
    background: #f8fafc;
    color: #344054;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 750;
  }

  .hero-side {
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 168px;
  }

  .hero-side .value {
    color: var(--ink);
    font-size: 28px;
    line-height: 1.05;
    font-weight: 820;
    margin-top: 10px;
  }

  .hero-side .note {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.4;
    margin-top: 10px;
  }

  .hero-side.action {
    border-left: 4px solid var(--amber);
  }

  .hero-side.service {
    border-left: 4px solid var(--blue);
  }

  .section-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
    margin: 18px 0 10px;
  }

  .section-heading .title {
    color: var(--ink);
    font-size: 20px;
    line-height: 1.15;
    font-weight: 820;
  }

  .section-heading .subtitle {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.4;
    margin-top: 4px;
  }

  div[data-testid="stPlotlyChart"] {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 8px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  div[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
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

  .owner-floor-wrap {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    margin-bottom: 16px;
  }

  .owner-floor-title {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 12px;
  }

  .owner-floor-title .title {
    color: var(--ink);
    font-size: 18px;
    font-weight: 780;
  }

  .owner-floor-title .subtitle {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.35;
    margin-top: 4px;
  }

  .owner-floor-grid {
    display: grid;
    gap: 12px;
  }

  .owner-zone-card {
    position: relative;
    min-height: 148px;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 13px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }

  .owner-zone-card:before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 5px;
    background: #cbd5e1;
  }

  .owner-zone-card.live {
    background: #ecfdf5;
    border-color: rgba(15, 159, 110, .38);
  }

  .owner-zone-card.live:before {
    background: var(--green);
  }

  .owner-zone-card.hot {
    background: #fff7ed;
    border-color: rgba(232, 110, 50, .38);
  }

  .owner-zone-card.hot:before {
    background: #e86e32;
  }

  .owner-zone-card.move {
    background: #eff6ff;
    border-color: rgba(37, 99, 235, .28);
  }

  .owner-zone-card.move:before {
    background: var(--blue);
  }

  .owner-zone-card.risk {
    background: #fef2f2;
    border-color: rgba(194, 65, 12, .34);
  }

  .owner-zone-card.risk:before {
    background: var(--red);
  }

  .owner-zone-card.pass {
    background: #fffbeb;
    border-color: rgba(183, 121, 31, .32);
  }

  .owner-zone-card.pass:before {
    background: var(--amber);
  }

  .owner-zone-card.quiet {
    background: #f8fafc;
    color: #475467;
  }

  .owner-zone-name {
    color: var(--ink);
    font-size: 12px;
    font-weight: 780;
    text-transform: uppercase;
    letter-spacing: .05em;
  }

  .owner-zone-topline {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: flex-start;
  }

  .owner-zone-badge {
    border-radius: 999px;
    background: rgba(255,255,255,.76);
    border: 1px solid rgba(17, 24, 39, .08);
    color: #344054;
    font-size: 10px;
    font-weight: 800;
    padding: 4px 7px;
    white-space: nowrap;
  }

  .owner-zone-status {
    margin-top: 8px;
    color: var(--ink);
    font-size: 21px;
    line-height: 1.08;
    font-weight: 800;
  }

  .owner-zone-note {
    margin-top: 6px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.3;
  }

  .owner-zone-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .owner-zone-metrics span {
    border: 1px solid rgba(17, 24, 39, .08);
    border-radius: 999px;
    background: rgba(255,255,255,.72);
    padding: 4px 7px;
    color: #344054;
    font-size: 11px;
    font-weight: 700;
  }

  .owner-attention-track {
    height: 7px;
    border-radius: 999px;
    background: rgba(15, 23, 42, .08);
    overflow: hidden;
    margin-top: 10px;
  }

  .owner-attention-fill {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #9ad7ca, #14956f, #f0b84a);
  }

  .owner-map-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
  }

  .owner-map-legend span {
    border: 1px solid rgba(17, 24, 39, .08);
    border-radius: 999px;
    background: #f8fafc;
    color: #344054;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 750;
  }

  .owner-brief-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    margin-bottom: 16px;
  }

  .owner-brief-panel h3 {
    margin: 0 0 10px;
    font-size: 18px;
  }

  .owner-brief-panel ul {
    margin: 0;
    padding-left: 18px;
    color: #344054;
    font-size: 14px;
    line-height: 1.55;
  }

  .owner-brief-panel li + li {
    margin-top: 7px;
  }

  .owner-action {
    border-left: 4px solid var(--green);
    padding-left: 14px;
  }

  .owner-action strong {
    color: var(--ink);
  }

  .owner-action-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .owner-action-grid .callout-card {
    margin-bottom: 0;
    min-height: 132px;
  }

  .owner-rank-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .owner-rank-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
  }

  .owner-rank-card .rank {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
  }

  .owner-rank-card .zone {
    color: var(--ink);
    font-size: 18px;
    line-height: 1.15;
    font-weight: 820;
    margin-top: 8px;
  }

  .owner-rank-card .signal {
    color: #344054;
    font-size: 13px;
    line-height: 1.35;
    margin-top: 8px;
  }

  .owner-rank-card .mini-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
  }

  .owner-rank-card .mini-metrics span {
    background: #f8fafc;
    border: 1px solid rgba(17, 24, 39, .08);
    border-radius: 999px;
    color: #344054;
    font-size: 11px;
    font-weight: 750;
    padding: 4px 7px;
  }

  @media (max-width: 980px) {
    .dashboard-hero,
    .owner-action-grid,
    .owner-rank-grid {
      grid-template-columns: 1fr;
    }

    .heatmap-banner,
    .owner-floor-title,
    .section-heading {
      align-items: flex-start;
      flex-direction: column;
    }
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
SETTINGS_TABLE = "dashboard_settings"
ZONE_LABELS_KEY = "zone_labels"
APP_DIR = Path(__file__).parent
ROOM_IMAGE_PATH = APP_DIR / "assets" / "home_environment.jpg"
ROOM_IMAGE_WIDTH = 1800
ROOM_IMAGE_HEIGHT = 1368
ROOM_WIDTH_MM = 4200
ROOM_DEPTH_MM = 4500
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


@st.cache_data(ttl=30)
def fetch_dashboard_setting(setting_key: str) -> dict[str, Any]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {}

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{SETTINGS_TABLE}",
            headers=supabase_headers(),
            params={"select": "value", "setting_key": f"eq.{setting_key}", "limit": "1"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        return {}

    rows = response.json()
    if not rows:
        return {}

    value = rows[0].get("value") or {}
    return value if isinstance(value, dict) else {}


def save_dashboard_setting(setting_key: str, value: dict[str, Any]) -> tuple[bool, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return False, "Supabase is not configured."

    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = {"setting_key": setting_key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}

    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/{SETTINGS_TABLE}",
            headers=headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, str(exc)

    fetch_dashboard_setting.clear()
    return True, "Saved."


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


def crowd_concentration(
    df: pd.DataFrame,
    x_names: list[str],
    y_names: list[str],
) -> tuple[dict[str, list[list[float]]], list[list[float]], pd.DataFrame]:
    rows = len(y_names)
    cols = len(x_names)
    buckets = {
        "Solo": empty_matrix(rows, cols),
        "Pairs": empty_matrix(rows, cols),
        "Groups": empty_matrix(rows, cols),
    }
    crowd_pressure = empty_matrix(rows, cols)
    peak_people = empty_matrix(rows, cols)

    for _, record in df.iterrows():
        duration_min = float(record.get("duration_s") or 0) / 60.0
        matrix = record.get("zone_now") or []

        for row_idx, row in enumerate(matrix):
            if row_idx >= rows:
                continue
            for col_idx, value in enumerate(row or []):
                if col_idx >= cols:
                    continue

                count = int(value or 0)
                peak_people[row_idx][col_idx] = max(peak_people[row_idx][col_idx], float(count))

                if count == 1:
                    buckets["Solo"][row_idx][col_idx] += duration_min
                elif count == 2:
                    buckets["Pairs"][row_idx][col_idx] += duration_min
                    crowd_pressure[row_idx][col_idx] += duration_min
                elif count >= 3:
                    buckets["Groups"][row_idx][col_idx] += duration_min
                    crowd_pressure[row_idx][col_idx] += duration_min * (count - 1)

    table_rows: list[dict[str, Any]] = []
    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            solo = buckets["Solo"][row_idx][col_idx]
            pairs = buckets["Pairs"][row_idx][col_idx]
            groups = buckets["Groups"][row_idx][col_idx]
            values = {"Solo": solo, "Pairs": pairs, "Groups": groups}
            dominant = max(values, key=values.get) if max(values.values()) > 0 else "None"
            table_rows.append(
                {
                    "zone": f"{row_name}-{col_name}",
                    "solo_minutes": solo,
                    "pair_minutes": pairs,
                    "group_minutes": groups,
                    "crowd_pressure": crowd_pressure[row_idx][col_idx],
                    "peak_people": int(peak_people[row_idx][col_idx]),
                    "dominant_pattern": dominant,
                }
            )

    concentration_table = pd.DataFrame(table_rows).sort_values(
        ["crowd_pressure", "group_minutes", "pair_minutes", "solo_minutes"],
        ascending=False,
    )
    return buckets, crowd_pressure, concentration_table


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


def render_section_heading(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-heading">
          <div>
            <div class="title">{escape(title)}</div>
            <div class="subtitle">{escape(subtitle)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_owner_hero(
    attention_zone: str,
    attention_note: str,
    people_value: str,
    people_note: str,
    service_value: str,
    service_note: str,
    action_title: str,
    action_note: str,
) -> None:
    st.markdown(
        f"""
        <div class="dashboard-hero">
          <div class="hero-primary">
            <div class="hero-eyebrow">Owner brief</div>
            <div class="hero-title">{escape(attention_zone)} is the main place to watch</div>
            <div class="hero-subtitle">{escape(attention_note)}</div>
            <div class="hero-pills">
              <span class="hero-pill">Live: {escape(people_value)}</span>
              <span class="hero-pill">{escape(people_note)}</span>
            </div>
          </div>
          <div class="hero-side action">
            <div>
              <div class="hero-eyebrow">Next action</div>
              <div class="value">{escape(action_title)}</div>
              <div class="note">{escape(action_note)}</div>
            </div>
          </div>
          <div class="hero-side service">
            <div>
              <div class="hero-eyebrow">Service watch</div>
              <div class="value">{escape(service_value)}</div>
              <div class="note">{escape(service_note)}</div>
            </div>
          </div>
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


def current_zone_labels(
    current_matrix: list[list[float]],
    x_names: list[str],
    y_names: list[str],
    zone_aliases: dict[str, str] | None = None,
) -> list[str]:
    labels: list[str] = []
    for row_idx, row in enumerate(current_matrix):
        for col_idx, value in enumerate(row):
            count = int(value or 0)
            if count <= 0 or row_idx >= len(y_names) or col_idx >= len(x_names):
                continue
            zone = clean_label(f"{y_names[row_idx]} {x_names[col_idx]}").upper()
            labels.append(f"{zone_display_name(zone, zone_aliases)} ({count})")
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


def enrich_targets(targets: pd.DataFrame) -> pd.DataFrame:
    if targets.empty:
        return targets.copy()

    result = targets.copy()
    result["distance_mm"] = pd.to_numeric(result["distance_mm"], errors="coerce").fillna(0)
    result["speed_cms"] = pd.to_numeric(result["speed_cms"], errors="coerce").fillna(0)
    result["duration_s"] = pd.to_numeric(result["duration_s"], errors="coerce").fillna(0)
    result["counted"] = result["counted"].fillna(False).astype(bool)
    result["motion"] = result["motion"].fillna("UNKNOWN")
    result["zone_label"] = result["zone"].fillna("OUT_OF_ZONE").map(lambda value: clean_label(value).upper())
    result["target_label"] = result["target_slot"].fillna(0).astype(int).map(lambda value: f"Slot {value}")
    result["distance_band"] = pd.cut(
        result["distance_mm"],
        bins=[0, 1000, 2200, 3800, 6000, float("inf")],
        labels=["Front 0-1m", "Near 1-2.2m", "Mid 2.2-3.8m", "Far 3.8-6m", "Out of range"],
        include_lowest=True,
    ).astype(str)

    def behavior(row: pd.Series) -> str:
        if not bool(row["counted"]):
            return "Passerby / out of zone"
        if row["motion"] == "APPROACHING":
            return "Approaching"
        if row["motion"] == "MOVING_AWAY":
            return "Leaving"
        if row["motion"] == "STATIONARY":
            return "Engaged stationary"
        return clean_label(row["motion"]).title()

    result["behavior"] = result.apply(behavior, axis=1)
    return result


def top_value(series: pd.Series, fallback: str = "None") -> str:
    values = series.dropna()
    if values.empty:
        return fallback
    counts = values.value_counts()
    if counts.empty:
        return fallback
    return str(counts.index[0])


def apply_selection_filter(frame: pd.DataFrame, column: str, selected: list[str], options: list[str]) -> pd.DataFrame:
    if frame.empty or not options:
        return frame
    if not selected:
        return frame.iloc[0:0].copy()
    return frame[frame[column].isin(selected)].copy()


def all_zone_labels(x_names: list[str], y_names: list[str]) -> list[str]:
    return [clean_label(f"{row_name} {col_name}").upper() for row_name in y_names for col_name in x_names]


def default_zone_name(zone_label: str) -> str:
    return clean_label(zone_label).title()


def zone_display_name(zone_label: str, zone_aliases: dict[str, str] | None = None) -> str:
    canonical = clean_label(zone_label).upper()
    alias = (zone_aliases or {}).get(canonical, "").strip()
    return alias or default_zone_name(canonical)


def display_zone_list(zone_labels: list[str], zone_aliases: dict[str, str] | None = None) -> str:
    if not zone_labels:
        return ""
    return ", ".join(zone_display_name(zone, zone_aliases) for zone in zone_labels)


def bedroom_zone_preset(zone_options: list[str]) -> dict[str, str]:
    preset = {
        "FRONT FAR LEFT": "Left Sofa Front",
        "FRONT LEFT": "Left Sofa Front",
        "FRONT CENTER": "Walkway Front",
        "FRONT RIGHT": "Right Sofa Front",
        "FRONT FAR RIGHT": "Right Sofa Front",
        "NEAR FAR LEFT": "Left Sofa",
        "NEAR LEFT": "Left Sofa",
        "NEAR CENTER": "Bed Foot",
        "NEAR RIGHT": "Right Sofa",
        "NEAR FAR RIGHT": "Right Sofa",
        "MID FAR LEFT": "Wardrobe",
        "MID LEFT": "Wardrobe / Left Aisle",
        "MID CENTER": "Bed",
        "MID RIGHT": "Right Aisle",
        "MID FAR RIGHT": "Curtains",
        "FAR FAR LEFT": "Wardrobe Back",
        "FAR LEFT": "Back Wall Left",
        "FAR CENTER": "Bed Head",
        "FAR RIGHT": "Back Wall Right",
        "FAR FAR RIGHT": "Curtains Back",
    }
    return {zone: preset[zone] for zone in zone_options if zone in preset}


def default_counter_zones(targets: pd.DataFrame, zone_options: list[str]) -> list[str]:
    if targets.empty or not zone_options:
        return zone_options[:1]

    stationary = targets[
        targets["counted"]
        & (targets["motion"] == "STATIONARY")
        & targets["zone_label"].isin(zone_options)
    ].copy()
    if not stationary.empty:
        top_stationary = (
            stationary.groupby("zone_label")["duration_s"].sum().sort_values(ascending=False).head(1).index.tolist()
        )
        if top_stationary:
            return top_stationary

    preferred = ["NEAR CENTER", "NEAR RIGHT", "NEAR LEFT", "MID CENTER"]
    for zone in preferred:
        if zone in zone_options:
            return [zone]
    return zone_options[:1]


def zone_value_matrix(values: dict[str, float], x_names: list[str], y_names: list[str]) -> list[list[float]]:
    matrix = empty_matrix(len(y_names), len(x_names))
    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            label = clean_label(f"{row_name} {col_name}").upper()
            matrix[row_idx][col_idx] = float(values.get(label, 0.0))
    return matrix


def boolean_segments(frame: pd.DataFrame, flag_col: str) -> pd.DataFrame:
    if frame.empty or flag_col not in frame:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    start_time = None
    end_time = None
    duration_s = 0.0
    peak_floor = 0
    peak_counter = 0

    for _, record in frame.sort_values("captured_at").iterrows():
        active = bool(record.get(flag_col))
        if active and start_time is None:
            start_time = record["captured_at"]
            duration_s = 0.0
            peak_floor = 0
            peak_counter = 0

        if active:
            duration = float(record.get("duration_s") or 0)
            duration_s += duration
            end_time = record["captured_at"] + timedelta(seconds=duration)
            peak_floor = max(peak_floor, int(record.get("floor_moving_people") or 0))
            peak_counter = max(peak_counter, int(record.get("counter_stationary_people") or 0))
            continue

        if start_time is not None:
            rows.append(
                {
                    "start": start_time,
                    "end": end_time or record["captured_at"],
                    "duration_s": duration_s,
                    "peak_floor_moving": peak_floor,
                    "peak_counter_stationary": peak_counter,
                }
            )
            start_time = None

    if start_time is not None:
        rows.append(
            {
                "start": start_time,
                "end": end_time or start_time,
                "duration_s": duration_s,
                "peak_floor_moving": peak_floor,
                "peak_counter_stationary": peak_counter,
            }
        )

    return pd.DataFrame(rows)


def longest_true_duration(frame: pd.DataFrame, flag_col: str) -> float:
    if frame.empty or flag_col not in frame:
        return 0.0

    current = 0.0
    longest = 0.0
    for _, record in frame.sort_values("captured_at").iterrows():
        if bool(record.get(flag_col)):
            current += float(record.get("duration_s") or 0)
            longest = max(longest, current)
        else:
            current = 0.0
    return longest


def service_coverage_analysis(
    targets: pd.DataFrame,
    counter_zones: list[str],
    floor_zones: list[str],
    stationary_speed_cms: int,
    moving_speed_cms: int,
) -> dict[str, Any]:
    empty = {
        "frames": pd.DataFrame(),
        "risk_floor": pd.DataFrame(),
        "counter_stationary": pd.DataFrame(),
        "risk_segments": pd.DataFrame(),
    }
    if targets.empty or not counter_zones or not floor_zones:
        return empty

    work = targets[targets["counted"]].copy()
    if work.empty:
        return empty

    abs_speed = pd.to_numeric(work["speed_cms"], errors="coerce").fillna(0).abs()
    work["stationary_like"] = (work["motion"] == "STATIONARY") | (abs_speed <= stationary_speed_cms)
    work["moving_like"] = work["motion"].isin(["APPROACHING", "MOVING_AWAY"]) | (abs_speed >= moving_speed_cms)
    work["counter_stationary"] = work["zone_label"].isin(counter_zones) & work["stationary_like"]
    work["counter_present"] = work["zone_label"].isin(counter_zones)
    work["floor_moving"] = work["zone_label"].isin(floor_zones) & work["moving_like"]
    work["floor_present"] = work["zone_label"].isin(floor_zones)

    frames = (
        work.groupby("captured_at", as_index=False)
        .agg(
            duration_s=("duration_s", "max"),
            counter_stationary_people=("counter_stationary", "sum"),
            counter_present_people=("counter_present", "sum"),
            floor_moving_people=("floor_moving", "sum"),
            floor_present_people=("floor_present", "sum"),
        )
        .sort_values("captured_at")
    )
    frames["counter_stationary"] = frames["counter_stationary_people"] > 0
    frames["floor_moving"] = frames["floor_moving_people"] > 0
    frames["service_risk"] = frames["counter_stationary"] & frames["floor_moving"]

    risk_times = set(frames.loc[frames["service_risk"], "captured_at"])
    risk_floor = work[work["floor_moving"] & work["captured_at"].isin(risk_times)].copy()
    counter_stationary = work[work["counter_stationary"]].copy()

    return {
        "frames": frames,
        "risk_floor": risk_floor,
        "counter_stationary": counter_stationary,
        "risk_segments": boolean_segments(frames, "service_risk"),
    }


def owner_location_summary(
    zone_table: pd.DataFrame,
    targets: pd.DataFrame,
    risk_floor: pd.DataFrame,
    current_matrix: list[list[float]],
    concentration_table: pd.DataFrame,
    x_names: list[str],
    y_names: list[str],
    zone_aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    current = coerce_matrix(current_matrix, len(y_names), len(x_names))
    zone_lookup = {
        clean_label(row["zone"]).upper(): row
        for _, row in zone_table.iterrows()
    }

    moving_minutes: dict[str, float] = {}
    stationary_minutes: dict[str, float] = {}
    if not targets.empty:
        counted = targets[targets["counted"]].copy()
        if not counted.empty:
            moving = counted[counted["behavior"].isin(["Approaching", "Leaving"])]
            stationary = counted[counted["behavior"] == "Engaged stationary"]
            moving_minutes = moving.groupby("zone_label")["duration_s"].sum().div(60).to_dict()
            stationary_minutes = stationary.groupby("zone_label")["duration_s"].sum().div(60).to_dict()

    risk_minutes = (
        risk_floor.groupby("zone_label")["duration_s"].sum().div(60).to_dict()
        if not risk_floor.empty
        else {}
    )
    crowd_lookup = (
        {
            clean_label(row["zone"]).upper(): float(row["crowd_pressure"] or 0)
            for _, row in concentration_table.iterrows()
        }
        if not concentration_table.empty
        else {}
    )

    rows: list[dict[str, Any]] = []
    for row_idx, row_name in enumerate(y_names):
        for col_idx, col_name in enumerate(x_names):
            zone_label = clean_label(f"{row_name} {col_name}").upper()
            zone_row = zone_lookup.get(zone_label)
            dwell = float(zone_row["dwell_minutes"]) if zone_row is not None else 0.0
            visits = int(zone_row["estimated_visits"]) if zone_row is not None and "estimated_visits" in zone_row else 0
            occupied = float(zone_row["occupied_minutes"]) if zone_row is not None else 0.0
            rows.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "zone_label": zone_label,
                    "display_zone": zone_display_name(zone_label, zone_aliases),
                    "dwell_minutes": dwell,
                    "occupied_minutes": occupied,
                    "estimated_visits": visits,
                    "now": int(current[row_idx][col_idx]),
                    "moving_minutes": float(moving_minutes.get(zone_label, 0.0)),
                    "stationary_minutes": float(stationary_minutes.get(zone_label, 0.0)),
                    "risk_minutes": float(risk_minutes.get(zone_label, 0.0)),
                    "crowd_pressure": float(crowd_lookup.get(zone_label, 0.0)),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    for source, normalized in [
        ("dwell_minutes", "dwell_score"),
        ("estimated_visits", "visit_score"),
        ("moving_minutes", "move_score"),
        ("crowd_pressure", "crowd_score"),
    ]:
        max_value = float(result[source].max() or 0)
        result[normalized] = result[source] / max_value if max_value else 0.0

    result["attention_score"] = (
        result["dwell_score"] * 55
        + result["visit_score"] * 20
        + result["move_score"] * 15
        + result["crowd_score"] * 10
    )

    top_attention = result.sort_values(["attention_score", "dwell_minutes"], ascending=False).iloc[0]["zone_label"]
    top_movement = result.sort_values(["moving_minutes", "estimated_visits"], ascending=False).iloc[0]["zone_label"]
    active_risk = float(result["risk_minutes"].max() or 0)
    nonzero_dwell = result.loc[result["dwell_minutes"] > 0, "dwell_minutes"]
    low_dwell_cutoff = float(nonzero_dwell.quantile(0.35)) if not nonzero_dwell.empty else 0.0

    statuses: list[str] = []
    classes: list[str] = []
    notes: list[str] = []
    for _, row in result.iterrows():
        if row["risk_minutes"] > 0 and row["risk_minutes"] >= max(1.0, active_risk * 0.45):
            statuses.append("Service watch")
            classes.append("risk")
            notes.append("Customers moved here while counter was held")
        elif row["now"] > 0:
            statuses.append("Live now")
            classes.append("live")
            notes.append("Person detected in this zone")
        elif row["zone_label"] == top_attention and row["attention_score"] > 0:
            statuses.append("Main attention")
            classes.append("hot")
            notes.append("Strongest pull in this window")
        elif row["zone_label"] == top_movement and row["moving_minutes"] > 0:
            statuses.append("Movement lane")
            classes.append("move")
            notes.append("Frequent customer motion")
        elif row["estimated_visits"] > 0 and row["dwell_minutes"] <= low_dwell_cutoff:
            statuses.append("Pass-through")
            classes.append("pass")
            notes.append("People pass but do not stay")
        elif row["dwell_minutes"] > 0:
            statuses.append("Some interest")
            classes.append("move")
            notes.append("Measured attention, but not the top zone")
        else:
            statuses.append("Quiet")
            classes.append("quiet")
            notes.append("Little activity in this window")

    result["owner_status"] = statuses
    result["status_class"] = classes
    result["owner_note"] = notes
    return result


def owner_zone_lookup(frame: pd.DataFrame) -> dict[str, pd.Series]:
    if frame.empty:
        return {}
    return {str(row["zone_label"]): row for _, row in frame.iterrows()}


def render_owner_floor_map(owner_zones: pd.DataFrame, x_names: list[str], y_names: list[str]) -> None:
    if owner_zones.empty:
        st.info("No location data available for the selected window.")
        return

    lookup = owner_zone_lookup(owner_zones)
    max_score = max(float(owner_zones["attention_score"].max() or 0), 1.0)
    cards: list[str] = []
    for row_idx in reversed(range(len(y_names))):
        for col_idx, col_name in enumerate(x_names):
            zone_label = clean_label(f"{y_names[row_idx]} {col_name}").upper()
            row = lookup.get(zone_label)
            if row is None:
                continue
            score_width = min(max(float(row["attention_score"]) / max_score * 100, 4), 100)
            metrics = [
                f"Now {int(row['now'])}",
                f"Dwell {format_minutes(float(row['dwell_minutes']))}",
                f"Move {format_minutes(float(row['moving_minutes']))}",
            ]
            if float(row["risk_minutes"]) > 0:
                metrics.append(f"Risk {format_minutes(float(row['risk_minutes']))}")

            display_zone = str(row.get("display_zone") or zone_label)
            cards.append(
                f'<div class="owner-zone-card {escape(str(row["status_class"]))}">'
                f'<div><div class="owner-zone-topline">'
                f'<div class="owner-zone-name">{escape(display_zone)}</div>'
                f'<div class="owner-zone-badge">{score_width:.0f}% pull</div></div>'
                f'<div class="owner-zone-status">{escape(str(row["owner_status"]))}</div>'
                f'<div class="owner-zone-note">{escape(str(row["owner_note"]))}</div></div>'
                f'<div><div class="owner-zone-metrics">'
                f'{"".join(f"<span>{escape(metric)}</span>" for metric in metrics)}'
                f'</div><div class="owner-attention-track">'
                f'<span class="owner-attention-fill" style="width:{score_width:.0f}%"></span>'
                f'</div></div></div>'
            )

    st.markdown(
        (
            '<div class="owner-floor-wrap">'
            '<div class="owner-floor-title"><div>'
            '<div class="title">Simple Store Location Map</div>'
            '<div class="subtitle">Each block is a radar zone. Stronger bars mean more dwell, visits, movement, or group pressure.</div>'
            '</div><div class="owner-map-legend">'
            '<span>Live now</span><span>Main attention</span><span>Movement</span><span>Service watch</span>'
            '</div></div>'
            f'<div class="owner-floor-grid" style="grid-template-columns: repeat({max(len(x_names), 1)}, minmax(130px, 1fr));">'
            f'{"".join(cards)}'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )


def render_owner_brief(story_lines: list[str], actions: list[tuple[str, str]], panel_title: str = "Today's Store Story") -> None:
    story_html = "".join(f"<li>{escape(line)}</li>" for line in story_lines)
    action_html = "".join(
        '<div class="callout-card owner-action">'
        '<div class="label">Suggested action</div>'
        f'<div class="value">{escape(action_title)}</div>'
        f'<div class="note">{escape(note)}</div>'
        '</div>'
        for action_title, note in actions
    )
    st.markdown(
        f'<div class="owner-brief-panel"><h3>{escape(panel_title)}</h3><ul>{story_html}</ul></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="owner-action-grid">{action_html}</div>', unsafe_allow_html=True)


def render_owner_rank_cards(owner_zones: pd.DataFrame, limit: int = 6) -> None:
    if owner_zones.empty:
        st.info("No ranked locations are available yet.")
        return

    cards: list[str] = []
    for position, (_, row) in enumerate(
        owner_zones.sort_values(["attention_score", "dwell_minutes"], ascending=False).head(limit).iterrows(),
        start=1,
    ):
        metrics = [
            f"Dwell {format_minutes(float(row['dwell_minutes']))}",
            f"Move {format_minutes(float(row['moving_minutes']))}",
            f"Now {int(row['now'])}",
        ]
        if float(row["crowd_pressure"]) > 0:
            metrics.append(f"Group {format_minutes(float(row['crowd_pressure']))}")
        cards.append(
            '<div class="owner-rank-card">'
            f'<div class="rank">Rank {position}</div>'
            f'<div class="zone">{escape(str(row["display_zone"]))}</div>'
            f'<div class="signal">{escape(str(row["owner_status"]))}: {escape(str(row["owner_note"]))}</div>'
            f'<div class="mini-metrics">{"".join(f"<span>{escape(metric)}</span>" for metric in metrics)}</div>'
            '</div>'
        )

    st.markdown(f'<div class="owner-rank-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def previous_zone_dwell(previous_zone_table: pd.DataFrame, zone_label: str) -> float:
    if previous_zone_table.empty:
        return 0.0
    lookup = {
        clean_label(row["zone"]).upper(): float(row["dwell_minutes"] or 0)
        for _, row in previous_zone_table.iterrows()
    }
    return float(lookup.get(zone_label, 0.0))


@st.cache_data
def image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def radar_to_photo_xy(x_mm: float, y_mm: float) -> tuple[float, float]:
    y_clamped = min(max(float(y_mm), 0.0), float(ROOM_DEPTH_MM))
    depth_ratio = y_clamped / float(ROOM_DEPTH_MM)
    image_y = 1305.0 - depth_ratio * 575.0
    half_width = 805.0 - depth_ratio * 425.0
    image_x = ROOM_IMAGE_WIDTH / 2 + (float(x_mm) / (ROOM_WIDTH_MM / 2)) * half_width
    return image_x, image_y


def room_landmarks() -> list[dict[str, Any]]:
    return [
        {"name": "Wardrobe", "x0": 0, "y0": 470, "x1": 470, "y1": 1085, "color": "#4b2e1f"},
        {"name": "Left sofa", "x0": 0, "y0": 870, "x1": 790, "y1": 1360, "color": "#d99118"},
        {"name": "Bed", "x0": 710, "y0": 770, "x1": 1190, "y1": 1190, "color": "#e7d4c9"},
        {"name": "Right sofa", "x0": 1190, "y0": 850, "x1": 1800, "y1": 1340, "color": "#d6b69a"},
        {"name": "Walkway", "x0": 730, "y0": 1110, "x1": 1220, "y1": 1360, "color": "#d9e0e8"},
        {"name": "Back wall", "x0": 590, "y0": 445, "x1": 1515, "y1": 770, "color": "#d8cdc0"},
    ]


def render_room_photo_overlay(
    targets: pd.DataFrame,
    current_targets: pd.DataFrame,
    zone_aliases: dict[str, str] | None = None,
    trail_limit: int = 250,
    highlight_time: pd.Timestamp | None = None,
) -> None:
    uri = image_data_uri(str(ROOM_IMAGE_PATH))
    if not uri:
        st.info("Room photo asset is missing from the deployed app.")
        return

    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=uri,
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=ROOM_IMAGE_WIDTH,
            sizey=ROOM_IMAGE_HEIGHT,
            sizing="stretch",
            layer="below",
        )
    )

    for landmark in room_landmarks():
        fig.add_shape(
            type="rect",
            x0=landmark["x0"],
            y0=landmark["y0"],
            x1=landmark["x1"],
            y1=landmark["y1"],
            line=dict(color=landmark["color"], width=2),
            fillcolor=landmark["color"],
            opacity=0.18,
        )
        fig.add_annotation(
            x=(landmark["x0"] + landmark["x1"]) / 2,
            y=(landmark["y0"] + landmark["y1"]) / 2,
            text=landmark["name"],
            showarrow=False,
            font=dict(size=13, color="#111827"),
            bgcolor="rgba(255,255,255,.72)",
            bordercolor="rgba(17,24,39,.15)",
            borderwidth=1,
        )

    fig.add_trace(
        go.Scatter(
            x=[ROOM_IMAGE_WIDTH / 2],
            y=[1308],
            mode="markers+text",
            marker=dict(size=13, color="#111827", symbol="diamond"),
            text=["Radar eye"],
            textposition="top center",
            name="Radar",
            hovertemplate="Radar/camera eye position<extra></extra>",
        )
    )

    counted = targets[targets["counted"]].copy() if not targets.empty else pd.DataFrame()
    if not counted.empty:
        recent = counted.tail(trail_limit).copy()
        recent["x_mm"] = pd.to_numeric(recent["x_mm"], errors="coerce")
        recent["y_mm"] = pd.to_numeric(recent["y_mm"], errors="coerce")
        recent = recent.dropna(subset=["x_mm", "y_mm"])
        if not recent.empty:
            projected = recent.apply(lambda row: radar_to_photo_xy(row["x_mm"], row["y_mm"]), axis=1)
            recent["photo_x"] = [point[0] for point in projected]
            recent["photo_y"] = [point[1] for point in projected]
            recent["display_time"] = recent["captured_at"].dt.strftime("%H:%M:%S")
            color_map = {
                "Approaching": "#0f9f6e",
                "Engaged stationary": "#2563eb",
                "Leaving": "#e86e32",
                "Passerby / out of zone": "#94a3b8",
            }
            for behavior, group in recent.groupby("behavior", dropna=False):
                fig.add_trace(
                    go.Scatter(
                        x=group["photo_x"],
                        y=group["photo_y"],
                        mode="markers",
                        marker=dict(
                            size=9,
                            color=color_map.get(str(behavior), "#475467"),
                            opacity=0.76,
                            line=dict(width=1, color="#ffffff"),
                        ),
                        customdata=list(
                            zip(
                                group["display_time"].astype(str),
                                group["zone_label"].map(lambda zone: zone_display_name(zone, zone_aliases)),
                                group["distance_mm"].astype(str),
                                group["speed_cms"].astype(str),
                            )
                        ),
                        hovertemplate=(
                            "%{customdata[0]}<br>%{customdata[1]}<br>"
                            "%{customdata[2]} mm | %{customdata[3]} cm/s<extra></extra>"
                        ),
                        name=str(behavior),
                    )
                )

            if highlight_time is not None:
                current = recent[recent["captured_at"] == highlight_time].copy()
                if not current.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=current["photo_x"],
                            y=current["photo_y"],
                            mode="markers",
                            marker=dict(
                                size=19,
                                color="rgba(255,255,255,.05)",
                                line=dict(width=4, color="#111827"),
                                symbol="circle",
                            ),
                            customdata=list(
                                zip(
                                    current["zone_label"].map(lambda zone: zone_display_name(zone, zone_aliases)),
                                    current["distance_mm"].astype(str),
                                    current["motion"].astype(str),
                                )
                            ),
                            hovertemplate="Replay point<br>%{customdata[0]}<br>%{customdata[1]} mm | %{customdata[2]}<extra></extra>",
                            name="Replay moment",
                        )
                    )

    fig.update_layout(
        height=680,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis=dict(range=[0, ROOM_IMAGE_WIDTH], visible=False),
        yaxis=dict(range=[ROOM_IMAGE_HEIGHT, 0], visible=False, scaleanchor="x", scaleratio=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    st.plotly_chart(fig, width="stretch")


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
    unit: str = "person-min",
    metric_label: str = "Dwell",
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
                f"{metric_label}: " + "%{customdata[1]:.2f} " + unit + "<br>"
                "People now: %{customdata[2]}<extra></extra>"
            ),
            colorbar=dict(
                title=unit,
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
    st.plotly_chart(fig, width="stretch")


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
    st.plotly_chart(fig, width="stretch")


def render_floor_map(
    targets: pd.DataFrame,
    x_edges: list[int],
    y_edges: list[int],
    x_names: list[str],
    y_names: list[str],
    color_by: str = "behavior",
) -> None:
    fig = go.Figure()
    palette = [
        "#0f9f6e",
        "#2563eb",
        "#e86e32",
        "#7c3aed",
        "#b7791f",
        "#c2410c",
        "#0891b2",
        "#475467",
    ]
    fixed_colors = {
        "Approaching": "#0f9f6e",
        "Engaged stationary": "#2563eb",
        "Leaving": "#e86e32",
        "Passerby / out of zone": "#94a3b8",
        "STATIONARY": "#2563eb",
        "APPROACHING": "#0f9f6e",
        "MOVING_AWAY": "#e86e32",
    }

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
        if color_by not in recent.columns:
            color_by = "motion" if "motion" in recent.columns else "counted"
        recent[color_by] = recent[color_by].fillna("Unknown").astype(str)

        for idx, (label, group) in enumerate(recent.groupby(color_by, dropna=False)):
            color = fixed_colors.get(str(label), palette[idx % len(palette)])
            hover_color_values = group[color_by].fillna("Unknown").astype(str)
            customdata = list(
                zip(
                    group["display_time"].astype(str),
                    group["distance_mm"].astype(str),
                    group["motion"].astype(str),
                    group["speed_cms"].astype(str),
                    hover_color_values,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=group["x_mm"],
                    y=group["y_mm"],
                    mode="markers",
                    marker=dict(
                        size=group["counted"].map({True: 12, False: 7}),
                        color=color,
                        opacity=0.76,
                        line=dict(width=1, color="#ffffff"),
                    ),
                    text=group["zone"],
                    customdata=customdata,
                    hovertemplate=(
                        "%{text}<br>X %{x} mm | Y %{y} mm<br>"
                        "%{customdata[0]} | %{customdata[1]} mm<br>"
                        "%{customdata[2]} | %{customdata[3]} cm/s<br>"
                        f"{clean_label(color_by).title()}: " + "%{customdata[4]}<extra></extra>"
                    ),
                    name=str(label),
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
        legend_title=clean_label(color_by).title(),
        showlegend=True,
    )
    fig.update_yaxes(range=[max(y_edges), min(y_edges)], autorange=False)
    st.plotly_chart(fig, width="stretch")


def activity_color(value: float, max_value: float) -> str:
    if max_value <= 0 or value <= 0:
        return "#e8eef3"
    ratio = min(max(value / max_value, 0.0), 1.0)
    if ratio < 0.25:
        return "#9ad7ca"
    if ratio < 0.55:
        return "#14956f"
    if ratio < 0.78:
        return "#f0b84a"
    return "#e86e32"


def add_zone_prism(
    fig: go.Figure,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    height: float,
    color: str,
    name: str,
    value_label: str,
) -> None:
    xs = [x0, x1, x1, x0, x0, x1, x1, x0]
    ys = [y0, y0, y1, y1, y0, y0, y1, y1]
    zs = [0, 0, 0, 0, height, height, height, height]
    fig.add_trace(
        go.Mesh3d(
            x=xs,
            y=ys,
            z=zs,
            i=[0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3],
            j=[1, 2, 6, 7, 4, 5, 5, 6, 6, 7, 7, 4],
            k=[2, 3, 5, 6, 5, 1, 6, 2, 7, 3, 4, 0],
            color=color,
            opacity=0.58,
            flatshading=True,
            hovertemplate=f"{name}<br>{value_label}<extra></extra>",
            name=name,
            showscale=False,
            showlegend=False,
        )
    )


def render_activity_3d_map(
    dwell_matrix: list[list[float]],
    movement_matrix: list[list[float]],
    current_matrix: list[list[float]],
    targets: pd.DataFrame,
    x_edges: list[int],
    y_edges: list[int],
    x_names: list[str],
    y_names: list[str],
    zone_aliases: dict[str, str] | None = None,
    metric_mode: str = "Dwell",
    target_limit: int = 350,
) -> None:
    rows = len(y_names)
    cols = len(x_names)
    dwell = coerce_matrix(dwell_matrix, rows, cols)
    movement = coerce_matrix(movement_matrix, rows, cols)
    current = coerce_matrix(current_matrix, rows, cols)
    metric_matrix = movement if metric_mode == "Movement" else dwell
    max_metric = max([value for row in metric_matrix for value in row] + [0.0])

    fig = go.Figure()
    label_x: list[float] = []
    label_y: list[float] = []
    label_z: list[float] = []
    label_text: list[str] = []

    for row_idx, row_name in enumerate(y_names):
        if row_idx + 1 >= len(y_edges):
            continue
        for col_idx, col_name in enumerate(x_names):
            if col_idx + 1 >= len(x_edges):
                continue

            x0 = float(x_edges[col_idx])
            x1 = float(x_edges[col_idx + 1])
            y0 = float(y_edges[row_idx])
            y1 = float(y_edges[row_idx + 1])
            value = float(metric_matrix[row_idx][col_idx])
            height = 20.0 + (360.0 * value / max_metric if max_metric > 0 else 0.0)
            zone_label = clean_label(f"{row_name} {col_name}").upper()
            display_zone = zone_display_name(zone_label, zone_aliases)
            live_count = int(current[row_idx][col_idx])
            value_label = f"{metric_mode}: {format_minutes(value)}"
            if live_count:
                value_label += f"<br>Live now: {live_count}"

            add_zone_prism(
                fig,
                x0,
                x1,
                y0,
                y1,
                height,
                activity_color(value, max_metric),
                display_zone,
                value_label,
            )
            label_x.append((x0 + x1) / 2)
            label_y.append((y0 + y1) / 2)
            label_z.append(height + 42)
            label_text.append(f"{display_zone}<br>{format_minutes(value)}")

    fig.add_trace(
        go.Scatter3d(
            x=label_x,
            y=label_y,
            z=label_z,
            mode="text",
            text=label_text,
            textfont=dict(color="#111827", size=10),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter3d(
            x=[0],
            y=[0],
            z=[0],
            mode="markers+text",
            marker=dict(size=7, color="#111827", symbol="diamond"),
            text=["RADAR"],
            textposition="bottom center",
            name="Radar",
            hovertemplate="Radar position<extra></extra>",
        )
    )

    counted_targets = targets[targets["counted"]].copy() if not targets.empty else pd.DataFrame()
    if not counted_targets.empty:
        recent = counted_targets.tail(target_limit).copy()
        recent["x_mm"] = pd.to_numeric(recent["x_mm"], errors="coerce")
        recent["y_mm"] = pd.to_numeric(recent["y_mm"], errors="coerce")
        recent = recent.dropna(subset=["x_mm", "y_mm"])
        recent["display_time"] = recent["captured_at"].dt.strftime("%H:%M:%S")
        count = max(len(recent) - 1, 1)
        recent["time_layer"] = [80.0 + (idx / count) * 240.0 for idx in range(len(recent))]

        color_map = {
            "Approaching": "#0f9f6e",
            "Engaged stationary": "#2563eb",
            "Leaving": "#e86e32",
            "Passerby / out of zone": "#94a3b8",
        }
        for behavior, group in recent.groupby("behavior", dropna=False):
            fig.add_trace(
                go.Scatter3d(
                    x=group["x_mm"],
                    y=group["y_mm"],
                    z=group["time_layer"],
                    mode="markers",
                    marker=dict(
                        size=5,
                        color=color_map.get(str(behavior), "#475467"),
                        opacity=0.72,
                        line=dict(width=1, color="#ffffff"),
                    ),
                    customdata=list(
                        zip(
                            group["display_time"].astype(str),
                            group["zone_label"].map(lambda zone: zone_display_name(zone, zone_aliases)),
                            group["distance_mm"].astype(str),
                            group["speed_cms"].astype(str),
                        )
                    ),
                    hovertemplate=(
                        "%{customdata[0]}<br>%{customdata[1]}<br>"
                        "X %{x} mm | Y %{y} mm<br>"
                        "%{customdata[2]} mm | %{customdata[3]} cm/s<extra></extra>"
                    ),
                    name=str(behavior),
                )
            )

    axis_common = dict(showbackground=False, gridcolor="#d9e0e8", zerolinecolor="#94a3b8", showspikes=False)
    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=28, b=0),
        paper_bgcolor="#ffffff",
        scene=dict(
            xaxis=dict(title="Left / right, mm", **axis_common),
            yaxis=dict(title="Distance from radar, mm", **axis_common),
            zaxis=dict(title=f"{metric_mode} layer", range=[0, 520], **axis_common),
            camera=dict(eye=dict(x=1.35, y=-1.75, z=1.25)),
            aspectmode="manual",
            aspectratio=dict(x=1.35, y=1.55, z=0.62),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    st.plotly_chart(fig, width="stretch")


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
target_view = enrich_targets(targets)
previous_targets = target_observations(previous_df)
previous_target_view = enrich_targets(previous_targets)
zone_table = zone_summary(df, x_names, y_names)
previous_zone_table = zone_summary(previous_df, x_names, y_names) if not previous_df.empty else pd.DataFrame()
visits_by_zone = zone_visit_counts(df, x_names, y_names)
zone_table["estimated_visits"] = zone_table["zone"].map(visits_by_zone).fillna(0).astype(int)
zone_table["avg_dwell_s"] = zone_table.apply(
    lambda row: (row["dwell_minutes"] * 60 / row["estimated_visits"]) if row["estimated_visits"] else 0,
    axis=1,
)
if not previous_zone_table.empty:
    previous_visits_by_zone = zone_visit_counts(previous_df, x_names, y_names)
    previous_zone_table["estimated_visits"] = previous_zone_table["zone"].map(previous_visits_by_zone).fillna(0).astype(int)
    previous_zone_table["avg_dwell_s"] = previous_zone_table.apply(
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

zone_movement_values = (
    target_view[target_view["behavior"].isin(["Approaching", "Leaving"])]
    .groupby("zone_label")["duration_s"]
    .sum()
    .div(60)
    .to_dict()
    if not target_view.empty
    else {}
)
zone_movement_matrix = zone_value_matrix(zone_movement_values, x_names, y_names)

concentration_buckets, crowd_pressure_matrix, concentration_table = crowd_concentration(df, x_names, y_names)
_, _, previous_concentration_table = (
    crowd_concentration(previous_df, x_names, y_names)
    if not previous_df.empty
    else ({}, empty_matrix(len(y_names), len(x_names)), pd.DataFrame())
)
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
zone_options = all_zone_labels(x_names, y_names)
stored_zone_aliases = fetch_dashboard_setting(ZONE_LABELS_KEY)
session_zone_aliases = st.session_state.get("zone_aliases", {})
zone_aliases = {
    clean_label(key).upper(): str(value).strip()
    for key, value in {**stored_zone_aliases, **session_zone_aliases}.items()
    if clean_label(key).upper() in zone_options and str(value).strip()
}
active_zone_labels = current_zone_labels(current_heatmap_matrix, x_names, y_names, zone_aliases)
active_zone_text = ", ".join(active_zone_labels[:3]) if active_zone_labels else ("Clear" if is_live else "Offline")
top_zone = zone_table.iloc[0]["zone"] if not zone_table.empty else "none"
top_zone_label = zone_display_name(clean_label(top_zone).upper(), zone_aliases)

view_options = [
    "Owner Brief",
    "Heatmap",
    "Time Replay",
    "Crowd Concentration",
    "Service Coverage",
    "Targets",
    "Executive View",
    "Zones",
    "Dwell",
    "Campaign Compare",
    "Room Layout",
    "3D Activity Map",
    "Setup",
    "Data Health",
]
active_view = st.radio("View", view_options, horizontal=True, label_visibility="collapsed")

if active_view == "Owner Brief":
    owner_counter_zones = default_counter_zones(target_view, zone_options)
    owner_floor_zones = [zone for zone in zone_options if zone not in owner_counter_zones]
    owner_service = service_coverage_analysis(
        target_view,
        owner_counter_zones,
        owner_floor_zones,
        stationary_speed_cms=3,
        moving_speed_cms=6,
    )
    owner_service_frames = owner_service["frames"]
    owner_risk_floor = owner_service["risk_floor"]
    owner_risk_segments = owner_service["risk_segments"]
    owner_zones = owner_location_summary(
        zone_table,
        target_view,
        owner_risk_floor,
        current_heatmap_matrix,
        concentration_table,
        x_names,
        y_names,
        zone_aliases,
    )

    top_owner_zone = owner_zones.sort_values(["attention_score", "dwell_minutes"], ascending=False).iloc[0]
    movement_zone = owner_zones.sort_values(["moving_minutes", "estimated_visits"], ascending=False).iloc[0]
    risk_zone = owner_zones.sort_values(["risk_minutes", "moving_minutes"], ascending=False).iloc[0]
    pass_candidates = owner_zones[
        (owner_zones["estimated_visits"] > 0)
        & (owner_zones["dwell_minutes"] <= owner_zones["dwell_minutes"].replace(0, pd.NA).dropna().median())
    ].copy()
    quiet_zone = (
        pass_candidates.sort_values(["estimated_visits", "moving_minutes"], ascending=False).iloc[0]
        if not pass_candidates.empty
        else owner_zones.sort_values(["attention_score", "dwell_minutes"], ascending=True).iloc[0]
    )

    risk_minutes = (
        float(owner_service_frames.loc[owner_service_frames["service_risk"], "duration_s"].sum()) / 60.0
        if not owner_service_frames.empty
        else 0.0
    )
    floor_motion_minutes = (
        float(owner_service_frames.loc[owner_service_frames["floor_moving"], "duration_s"].sum()) / 60.0
        if not owner_service_frames.empty
        else 0.0
    )
    trend_previous = previous_zone_dwell(previous_zone_table, str(top_owner_zone["zone_label"]))
    trend_current = float(top_owner_zone["dwell_minutes"])
    trend_text = "No previous comparison yet"
    if trend_previous > 0:
        trend_change = ((trend_current - trend_previous) / trend_previous) * 100
        direction = "up" if trend_change >= 0 else "down"
        trend_text = f"{direction} {abs(trend_change):.0f}% vs previous {hours}h window"
    top_owner_name = str(top_owner_zone["display_zone"])
    movement_zone_name = str(movement_zone["display_zone"])
    risk_zone_name = str(risk_zone["display_zone"])
    quiet_zone_name = str(quiet_zone["display_zone"])

    story_lines = [
        f"The strongest attention zone is {top_owner_name} with {format_minutes(float(top_owner_zone['dwell_minutes']))} of measured dwell.",
        f"The busiest movement zone is {movement_zone_name} with {format_minutes(float(movement_zone['moving_minutes']))} of motion.",
        f"The quiet or pass-through area to inspect is {quiet_zone_name}; people are not staying there long.",
    ]
    if risk_minutes > 0:
        risk_share = risk_minutes / floor_motion_minutes if floor_motion_minutes else 0.0
        story_lines.append(
            f"Possible service miss: counter stayed stationary while floor movement was active for {format_minutes(risk_minutes)} ({risk_share * 100:.0f}% of movement time)."
        )
    else:
        story_lines.append("No counter-stationary service-risk overlap was detected in this window.")
    if float(top_owner_zone["crowd_pressure"]) > 0:
        story_lines.append(f"Group attention appeared around {top_owner_name}; that area may be drawing shared interest.")

    actions: list[tuple[str, str]] = []
    if risk_minutes >= 3:
        actions.append(
            (
                "Check service coverage",
                f"Review counter behavior when {risk_zone_name} is active; the system saw {format_minutes(risk_minutes)} of overlap.",
            )
        )
    actions.append(
        (
            "Protect the attention winner",
            f"Keep {top_owner_name} tidy and stocked; it is currently doing the most work for the store.",
        )
    )
    actions.append(
        (
            "Improve the quiet zone",
            f"Try a clearer price sign, product move, or staff prompt near {quiet_zone_name} and compare tomorrow.",
        )
    )

    hero_action_title, hero_action_note = actions[0]
    people_value = f"{last_people_now} now" if is_live else "Offline"
    people_note = active_zone_text if is_live else f"Last snapshot had {last_people_now}"
    service_value = format_minutes(risk_minutes) if risk_minutes > 0 else "Clear"
    service_note = (
        f"{len(owner_risk_segments)} overlap windows detected"
        if not owner_risk_segments.empty
        else "No counter-stationary service risk in this window"
    )
    render_owner_hero(
        top_owner_name,
        f"{format_minutes(float(top_owner_zone['dwell_minutes']))} of dwell in the selected {hours}h window; {trend_text}.",
        people_value,
        people_note,
        service_value,
        service_note,
        hero_action_title,
        hero_action_note,
    )

    render_section_heading("Floor Snapshot", "The cards below translate radar activity into plain store-location signals.")
    brief_cols = st.columns(4)
    with brief_cols[0]:
        callout_card("Right Now", str(last_people_now) if is_live else "--", active_zone_text if is_live else "Live feed is stale")
    with brief_cols[1]:
        callout_card("Main Attention", top_owner_name, f"{format_minutes(float(top_owner_zone['dwell_minutes']))} dwell, {trend_text}")
    with brief_cols[2]:
        callout_card(
            "Movement Hotspot",
            movement_zone_name if float(movement_zone["moving_minutes"]) > 0 else "None",
            f"{format_minutes(float(movement_zone['moving_minutes']))} customer motion",
        )
    with brief_cols[3]:
        callout_card("Service Watch", service_value, service_note)

    render_owner_floor_map(owner_zones, x_names, y_names)

    left, right = st.columns([1.05, 1])
    with left:
        render_owner_brief(story_lines, actions)
    with right:
        render_section_heading("Top Locations", "Ranked by dwell, visits, movement, and group pressure.")
        render_owner_rank_cards(owner_zones)

elif active_view == "Room Layout":
    render_heatmap_banner(
        "Room Layout Overlay",
        "Uses the supplied camera-eye photo and room dimensions to make radar detections easier to understand.",
    )

    layout_cols = st.columns(4)
    with layout_cols[0]:
        callout_card("Room Width", f"{ROOM_WIDTH_MM / 1000:.1f}m", "Back-wall reference from photo")
    with layout_cols[1]:
        callout_card("Room Depth", f"{ROOM_DEPTH_MM / 1000:.1f}m", "Radar-facing depth estimate")
    with layout_cols[2]:
        callout_card("Bed", "1.44m x 1.94m", "Measured bed footprint")
    with layout_cols[3]:
        callout_card("Seating", "2.83m / 1.73m", "Left and right sofa lengths")

    trail_limit = st.slider("Photo overlay trail points", min_value=50, max_value=1000, value=300, step=50)
    render_room_photo_overlay(target_view, current_targets, zone_aliases=zone_aliases, trail_limit=trail_limit)

    st.subheader("Photo Calibration Notes")
    note_cols = st.columns(3)
    with note_cols[0]:
        callout_card("Best Used For", "Context", "Shows where radar detections sit relative to bed, sofas, wardrobe, and walkway")
    with note_cols[1]:
        callout_card("Accuracy", "Approximate", "A single photo has perspective distortion; target overlay is calibrated from the visible dimensions")
    with note_cols[2]:
        callout_card("Next Improvement", "Mount point", "If you mark exact radar position and height, the projection can be tuned tighter")

elif active_view == "Time Replay":
    render_heatmap_banner(
        "Historic Location Replay",
        "Scrub or auto-play through the loaded history to see how people and room zones changed over time.",
    )

    replay_len = len(df)
    if "replay_index" not in st.session_state:
        st.session_state["replay_index"] = 0
    st.session_state["replay_index"] = int(min(max(st.session_state["replay_index"], 0), max(replay_len - 1, 0)))

    control_cols = st.columns([1, 1, 1, 1, 1])
    with control_cols[0]:
        autoplay = st.checkbox("Auto play", value=False, key="replay_autoplay")
    with control_cols[1]:
        loop_replay = st.checkbox("Loop", value=True, key="replay_loop")
    with control_cols[2]:
        playback_speed_ms = st.select_slider("Speed", options=[250, 500, 1000, 1500, 2500, 5000], value=1000, format_func=lambda value: f"{value} ms")
    with control_cols[3]:
        step_size = st.select_slider("Frame step", options=[1, 2, 5, 10, 20], value=1)
    with control_cols[4]:
        trail_minutes = st.slider("Trail minutes", min_value=1, max_value=max(5, min(hours * 60, 120)), value=min(10, max(1, hours * 60)), step=1)

    jump_cols = st.columns([1, 1, 4])
    with jump_cols[0]:
        if st.button("Start replay"):
            st.session_state["replay_index"] = 0
            st.rerun()
    with jump_cols[1]:
        if st.button("Latest"):
            st.session_state["replay_index"] = replay_len - 1
            st.rerun()

    if autoplay and replay_len > 1:
        tick = st_autorefresh(interval=int(playback_speed_ms), key="replay_autoplay_tick")
        last_tick = st.session_state.get("replay_last_tick")
        if tick != last_tick:
            next_index = st.session_state["replay_index"] + int(step_size)
            if next_index >= replay_len:
                next_index = 0 if loop_replay else replay_len - 1
            st.session_state["replay_index"] = next_index
            st.session_state["replay_last_tick"] = tick

    replay_start_time = df.iloc[0]["captured_at"]
    replay_end_time = df.iloc[-1]["captured_at"]
    total_replay_seconds = int(max(0, (replay_end_time - replay_start_time).total_seconds()))
    current_replay_time = df.iloc[int(st.session_state["replay_index"])]["captured_at"]
    current_offset_seconds = int(max(0, (current_replay_time - replay_start_time).total_seconds()))
    offset_step_seconds = max(1, min(60, max(total_replay_seconds, 1) // 240 or 1))
    replay_offset_seconds = st.slider(
        "Time from start",
        min_value=0,
        max_value=max(total_replay_seconds, 0),
        value=min(current_offset_seconds, max(total_replay_seconds, 0)),
        step=offset_step_seconds,
        format="%d sec",
        help="Scrub through the selected analysis window by elapsed time.",
    )
    st.caption(f"Selected offset: {format_seconds(float(replay_offset_seconds))} from the first loaded snapshot")
    requested_replay_time = replay_start_time + timedelta(seconds=int(replay_offset_seconds))
    replay_index = int((df["captured_at"] - requested_replay_time).abs().to_numpy().argmin())
    if replay_index != int(st.session_state["replay_index"]):
        st.session_state["replay_index"] = replay_index
        st.rerun()

    replay_index = int(st.session_state["replay_index"])
    replay_record = df.iloc[replay_index]
    replay_time = replay_record["captured_at"]
    replay_age = replay_time - df.iloc[0]["captured_at"]
    replay_until = df[df["captured_at"] <= replay_time].copy()
    replay_zone_now = coerce_matrix(replay_record.get("zone_now") or [], len(y_names), len(x_names))
    replay_current_targets = current_target_points(replay_record, True, x_edges, y_edges)
    trail_start = replay_time - timedelta(minutes=int(trail_minutes))
    if target_view.empty or "captured_at" not in target_view.columns:
        replay_trail = pd.DataFrame()
    else:
        replay_trail = target_view[
            (target_view["captured_at"] >= trail_start)
            & (target_view["captured_at"] <= replay_time)
        ].copy()
    if replay_trail.empty or "captured_at" not in replay_trail.columns:
        replay_current_observations = pd.DataFrame()
    else:
        replay_current_observations = replay_trail[replay_trail["captured_at"] == replay_time].copy()

    active_replay_zones = current_zone_labels(replay_zone_now, x_names, y_names, zone_aliases)
    replay_people = int(replay_record.get("people_now") or 0)
    replay_target_count = int(replay_current_observations["counted"].sum()) if not replay_current_observations.empty else 0
    replay_motion = (
        top_value(replay_current_observations["behavior"], "No target")
        if not replay_current_observations.empty
        else "No target"
    )

    replay_cols = st.columns(5)
    with replay_cols[0]:
        callout_card("Replay Time", replay_time.strftime("%b %d, %H:%M:%S"), f"+{format_seconds(replay_age.total_seconds())} from start")
    with replay_cols[1]:
        callout_card("People Then", str(replay_people), "Snapshot occupancy")
    with replay_cols[2]:
        callout_card("Active Zone", ", ".join(active_replay_zones[:2]) if active_replay_zones else "Clear", "At selected moment")
    with replay_cols[3]:
        callout_card("Current Points", str(replay_target_count), "Targets at selected moment")
    with replay_cols[4]:
        callout_card("Motion State", replay_motion, "Dominant behavior then")

    view_mode = st.radio("Replay view", ["Room photo", "Radar floor", "Both"], horizontal=True)

    timeline = df[["captured_at", "people_now"]].copy()
    fig = px.area(timeline, x="captured_at", y="people_now", title="Occupancy Timeline With Replay Cursor")
    fig.update_traces(line_color="#0f9f6e", fillcolor="rgba(15,159,110,.18)")
    fig.add_vline(x=replay_time, line_color="#c2410c", line_width=2)
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=52, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#111827",
        xaxis_title="Time",
        yaxis_title="People",
    )
    st.plotly_chart(fig, width="stretch")

    if view_mode in ["Room photo", "Both"]:
        render_room_photo_overlay(
            replay_trail,
            replay_current_targets,
            zone_aliases=zone_aliases,
            trail_limit=1000,
            highlight_time=replay_time,
        )

    if view_mode in ["Radar floor", "Both"]:
        render_retail_floor_heatmap(
            replay_zone_now,
            replay_zone_now,
            replay_current_targets,
            x_names,
            y_names,
            "Radar Zones at Replay Moment",
            True,
            unit="people",
            metric_label="People",
        )
        render_floor_map(replay_trail, x_edges, y_edges, x_names, y_names, color_by="behavior")

    st.subheader("Replay Data Points")
    if replay_current_observations.empty:
        st.write("No counted target observations at this replay moment.")
    else:
        display_replay = replay_current_observations.copy()
        display_replay["Store location"] = display_replay["zone_label"].map(lambda zone: zone_display_name(zone, zone_aliases))
        replay_columns = [
            "captured_at",
            "target_slot",
            "Store location",
            "behavior",
            "motion",
            "x_mm",
            "y_mm",
            "distance_mm",
            "speed_cms",
        ]
        st.dataframe(
            display_replay[[column for column in replay_columns if column in display_replay.columns]].rename(
                columns={
                    "captured_at": "Time",
                    "target_slot": "Target",
                    "behavior": "Behavior",
                    "motion": "Motion",
                    "x_mm": "X mm",
                    "y_mm": "Y mm",
                    "distance_mm": "Distance mm",
                    "speed_cms": "Speed cm/s",
                }
            ),
            width="stretch",
            hide_index=True,
        )

elif active_view == "3D Activity Map":
    render_heatmap_banner(
        "3D Activity Map",
        "A pseudo-3D radar view: X/Y are real floor position, height shows activity intensity rather than physical height.",
    )

    map_cols = st.columns([1, 1, 1, 1])
    with map_cols[0]:
        metric_mode = st.selectbox("Height shows", ["Dwell", "Movement"], index=0)
    with map_cols[1]:
        target_limit = st.slider("Target trail points", min_value=50, max_value=1000, value=350, step=50)
    with map_cols[2]:
        total_dwell = sum(sum(row) for row in zone_dwell_matrix)
        callout_card("Dwell Layer", format_minutes(float(total_dwell)), "Total zone attention")
    with map_cols[3]:
        total_movement = sum(sum(row) for row in zone_movement_matrix)
        callout_card("Motion Layer", format_minutes(float(total_movement)), "Approach + leaving movement")

    selected_matrix = zone_movement_matrix if metric_mode == "Movement" else zone_dwell_matrix
    selected_values = [
        {
            "zone": zone_display_name(clean_label(f"{row_name} {col_name}").upper(), zone_aliases),
            "value": float(selected_matrix[row_idx][col_idx]),
        }
        for row_idx, row_name in enumerate(y_names)
        for col_idx, col_name in enumerate(x_names)
    ]
    top_3d_zone = max(selected_values, key=lambda item: item["value"]) if selected_values else {"zone": "None", "value": 0.0}

    insight_cols = st.columns(3)
    with insight_cols[0]:
        callout_card("Tallest Zone", str(top_3d_zone["zone"]), f"{format_minutes(float(top_3d_zone['value']))} {metric_mode.lower()}")
    with insight_cols[1]:
        callout_card("Live Targets", str(last_people_now) if is_live else "--", active_zone_text if is_live else "Feed is stale")
    with insight_cols[2]:
        callout_card("3D Meaning", "Activity height", "LD2450 does not measure physical height or shelves")

    render_activity_3d_map(
        zone_dwell_matrix,
        zone_movement_matrix,
        current_heatmap_matrix,
        target_view,
        x_edges,
        y_edges,
        x_names,
        y_names,
        zone_aliases=zone_aliases,
        metric_mode=metric_mode,
        target_limit=target_limit,
    )

    st.info(
        "This is not a LiDAR-style room scan. The radar provides person targets on an X/Y floor plane, so the vertical axis is an activity layer. "
        "For real 3D shelves, walls, or body height, you would need a depth camera, LiDAR, or a point-cloud mmWave sensor."
    )

elif active_view == "Heatmap":
    render_heatmap_banner(
        "Retail Floor Heatmap",
        f"{hours}h dwell depth with live occupancy overlay. Darker cells held attention longer.",
    )

    render_section_heading("Read First", "A compact summary before the detailed zone heatmap.")
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

    render_section_heading("Visual Heatmap", "Depth shows where attention accumulated; target markers show live position when online.")
    render_retail_floor_heatmap(
        zone_dwell_matrix,
        current_heatmap_matrix,
        current_targets,
        x_names,
        y_names,
        "Dwell Depth by Zone",
        is_live,
    )

    render_section_heading("Zone Ranking", "The most useful locations to inspect first.")
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
            width="stretch",
            hide_index=True,
        )

elif active_view == "Crowd Concentration":
    render_heatmap_banner(
        "Crowd Concentration",
        "Separates solo browsing from pair and group gathering. Useful for spotting where products pull shared attention.",
    )

    top_crowd = concentration_table.iloc[0] if not concentration_table.empty else None
    top_crowd_pressure = float(top_crowd["crowd_pressure"]) if top_crowd is not None else 0.0
    total_pair_group = float(concentration_table["pair_minutes"].sum() + concentration_table["group_minutes"].sum()) if not concentration_table.empty else 0.0
    total_solo = float(concentration_table["solo_minutes"].sum()) if not concentration_table.empty else 0.0
    group_zone = concentration_table.sort_values("group_minutes", ascending=False).iloc[0] if not concentration_table.empty else None

    crowd_cols = st.columns(4)
    with crowd_cols[0]:
        callout_card(
            "Gathering Zone",
            clean_label(top_crowd["zone"]).upper() if top_crowd_pressure > 0 else "NONE",
            f"{format_minutes(top_crowd_pressure)} pressure" if top_crowd_pressure > 0 else "No 2+ person gathering yet",
        )
    with crowd_cols[1]:
        callout_card("Solo Time", format_minutes(total_solo), "One-person browsing minutes")
    with crowd_cols[2]:
        callout_card("Pair/Group Time", format_minutes(total_pair_group), "Minutes with 2+ people in the same zone")
    with crowd_cols[3]:
        callout_card(
            "Group Hotspot",
            clean_label(group_zone["zone"]).upper() if group_zone is not None and float(group_zone["group_minutes"]) > 0 else "NONE",
            "3+ people together" if group_zone is not None and float(group_zone["group_minutes"]) > 0 else "No 3+ person gathering yet",
        )

    render_section_heading("Where Groups Form", "This layer is useful for spotting shared attention, bottlenecks, and product draw.")
    render_retail_floor_heatmap(
        crowd_pressure_matrix,
        current_heatmap_matrix,
        current_targets,
        x_names,
        y_names,
        "Crowd Pressure: 2+ People in the Same Zone",
        is_live,
        unit="pressure-min",
        metric_label="Crowd pressure",
    )

    render_section_heading("Solo, Pair, Group", "Compare whether a zone is mainly browsed alone or attracts multiple people.")
    solo_col, pair_col, group_col = st.columns(3)
    with solo_col:
        render_heatmap(concentration_buckets["Solo"], x_names, y_names, "Solo Presence", "min")
    with pair_col:
        render_heatmap(concentration_buckets["Pairs"], x_names, y_names, "Pairs", "min")
    with group_col:
        render_heatmap(concentration_buckets["Groups"], x_names, y_names, "Groups 3+", "min")

    render_section_heading("Crowd Pattern Ranking", "Zones sorted by concentration behavior.")
    display_concentration = concentration_table.copy()
    display_concentration["Zone"] = display_concentration["zone"].map(lambda value: clean_label(value).upper())
    display_concentration = display_concentration[
        ["Zone", "solo_minutes", "pair_minutes", "group_minutes", "crowd_pressure", "peak_people", "dominant_pattern"]
    ].rename(
        columns={
            "solo_minutes": "Solo min",
            "pair_minutes": "Pair min",
            "group_minutes": "3+ group min",
            "crowd_pressure": "Crowd pressure",
            "peak_people": "Peak people",
            "dominant_pattern": "Dominant pattern",
        }
    )
    st.dataframe(display_concentration.round(2), width="stretch", hide_index=True)

elif active_view == "Service Coverage":
    render_heatmap_banner(
        "Service Coverage",
        "Compares stationary counter presence with moving floor activity. Use it as an operations signal, not identity detection.",
    )

    default_counter = default_counter_zones(target_view, zone_options)
    config_cols = st.columns([1.25, 1.6, 0.9, 0.9])
    with config_cols[0]:
        counter_zones = st.multiselect("Counter / staff zone", zone_options, default=default_counter)
    with config_cols[1]:
        default_floor_zones = [zone for zone in zone_options if zone not in counter_zones]
        floor_zones = st.multiselect("Customer floor zones", zone_options, default=default_floor_zones)
    with config_cols[2]:
        stationary_speed_cms = st.slider("Stationary tolerance", min_value=0, max_value=20, value=3, step=1)
    with config_cols[3]:
        moving_speed_cms = st.slider("Movement threshold", min_value=1, max_value=60, value=6, step=1)

    service = service_coverage_analysis(
        target_view,
        counter_zones,
        floor_zones,
        stationary_speed_cms=stationary_speed_cms,
        moving_speed_cms=moving_speed_cms,
    )
    service_frames = service["frames"]
    risk_floor = service["risk_floor"]
    counter_stationary = service["counter_stationary"]
    risk_segments = service["risk_segments"]

    if service_frames.empty:
        st.info("Choose at least one counter zone and one customer floor zone to calculate service coverage.")
    else:
        counter_stationary_minutes = float(service_frames.loc[service_frames["counter_stationary"], "duration_s"].sum()) / 60.0
        floor_motion_minutes = float(service_frames.loc[service_frames["floor_moving"], "duration_s"].sum()) / 60.0
        risk_minutes = float(service_frames.loc[service_frames["service_risk"], "duration_s"].sum()) / 60.0
        risk_floor_person_minutes = float(risk_floor["duration_s"].sum()) / 60.0 if not risk_floor.empty else 0.0
        longest_counter_s = longest_true_duration(service_frames, "counter_stationary")
        longest_risk_s = longest_true_duration(service_frames, "service_risk")
        risk_share = risk_minutes / floor_motion_minutes if floor_motion_minutes else 0.0
        latest_service = service_frames.iloc[-1]

        if is_live and bool(latest_service.get("service_risk")):
            current_signal = "Risk now"
            current_note = "Counter stationary while floor movement is active"
        elif is_live and bool(latest_service.get("counter_stationary")):
            current_signal = "Counter held"
            current_note = "Counter is stationary; floor movement not active"
        elif is_live and bool(latest_service.get("floor_moving")):
            current_signal = "Floor active"
            current_note = "Movement without counter-stationary overlap"
        elif is_live:
            current_signal = "Clear"
            current_note = "No selected-zone activity right now"
        else:
            current_signal = "Offline"
            current_note = "Waiting for fresh radar uploads"

        coverage_cols = st.columns(4)
        with coverage_cols[0]:
            callout_card("Current Signal", current_signal, current_note)
        with coverage_cols[1]:
            callout_card("Counter Stationary", format_minutes(counter_stationary_minutes), "Selected counter zone hold time")
        with coverage_cols[2]:
            callout_card("Floor Movement", format_minutes(floor_motion_minutes), "Any movement in selected floor zones")
        with coverage_cols[3]:
            callout_card("Service Risk", format_minutes(risk_minutes), f"{risk_share * 100:.0f}% of floor movement time")

        detail_cols = st.columns(4)
        with detail_cols[0]:
            callout_card("Longest Counter Hold", format_seconds(longest_counter_s), "Continuous stationary stretch")
        with detail_cols[1]:
            callout_card("Longest Risk Stretch", format_seconds(longest_risk_s), "Continuous overlap stretch")
        with detail_cols[2]:
            callout_card("Risk Windows", str(len(risk_segments)), "Counter stationary + floor motion")
        with detail_cols[3]:
            callout_card("Moving Customer Time", format_minutes(risk_floor_person_minutes), "Person-minutes during risk windows")

        risk_values = (
            risk_floor.groupby("zone_label")["duration_s"].sum().div(60).to_dict()
            if not risk_floor.empty
            else {}
        )
        risk_matrix = zone_value_matrix(risk_values, x_names, y_names)
        render_retail_floor_heatmap(
            risk_matrix,
            current_heatmap_matrix,
            current_targets,
            x_names,
            y_names,
            "Where Floor Motion Happened While Counter Was Stationary",
            is_live,
            unit="motion-min",
            metric_label="Overlap motion",
        )

        timeline = service_frames.copy()
        timeline["minute"] = timeline["captured_at"].dt.floor("min")
        timeline_parts = []
        for metric, flag_col in [
            ("Counter stationary", "counter_stationary"),
            ("Floor movement", "floor_moving"),
            ("Service risk overlap", "service_risk"),
        ]:
            part = timeline[["minute", "duration_s"]].copy()
            part["metric"] = metric
            part["minutes"] = part["duration_s"].where(timeline[flag_col], 0) / 60.0
            timeline_parts.append(part[["minute", "metric", "minutes"]])

        timeline_long = (
            pd.concat(timeline_parts, ignore_index=True)
            .groupby(["minute", "metric"], as_index=False)["minutes"]
            .sum()
        )

        timeline_fig = px.bar(
            timeline_long,
            x="minute",
            y="minutes",
            color="metric",
            barmode="group",
            title="Service Coverage Timeline",
            color_discrete_map={
                "Counter stationary": "#2563eb",
                "Floor movement": "#0f9f6e",
                "Service risk overlap": "#c2410c",
            },
        )
        timeline_fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=52, b=10),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font_color="#111827",
            xaxis_title="Time",
            yaxis_title="Minutes per time bucket",
            legend_title="Signal",
        )
        st.plotly_chart(timeline_fig, width="stretch")

        left, right = st.columns(2)
        with left:
            if not risk_floor.empty:
                risk_zone_table = (
                    risk_floor.groupby("zone_label", as_index=False)
                    .agg(
                        motion_minutes=("duration_s", lambda values: float(values.sum()) / 60.0),
                        observations=("captured_at", "count"),
                        avg_speed_cms=("speed_cms", "mean"),
                    )
                    .sort_values(["motion_minutes", "observations"], ascending=False)
                )
                fig = px.bar(
                    risk_zone_table,
                    x="motion_minutes",
                    y="zone_label",
                    orientation="h",
                    title="Floor Motion During Counter Hold",
                    color="motion_minutes",
                    color_continuous_scale=["#dbeafe", "#0f9f6e", "#c2410c"],
                )
                fig.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=52, b=10),
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font_color="#111827",
                    xaxis_title="Moving person-minutes",
                    yaxis_title="",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No floor movement overlapped with a stationary counter signal in this window.")

        with right:
            if not counter_stationary.empty:
                counter_zone_table = (
                    counter_stationary.groupby("zone_label", as_index=False)
                    .agg(
                        stationary_minutes=("duration_s", lambda values: float(values.sum()) / 60.0),
                        observations=("captured_at", "count"),
                    )
                    .sort_values(["stationary_minutes", "observations"], ascending=False)
                )
                fig = px.bar(
                    counter_zone_table,
                    x="stationary_minutes",
                    y="zone_label",
                    orientation="h",
                    title="Counter Stationary Concentration",
                    color="stationary_minutes",
                    color_continuous_scale=["#dbeafe", "#2563eb"],
                )
                fig.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=52, b=10),
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font_color="#111827",
                    xaxis_title="Stationary person-minutes",
                    yaxis_title="",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No stationary signal in the selected counter zone yet.")

        st.subheader("Service Risk Windows")
        if risk_segments.empty:
            st.write("No overlap windows found in the selected analysis window.")
        else:
            display_segments = risk_segments.sort_values("start", ascending=False).head(25).copy()
            display_segments["Start"] = display_segments["start"].dt.strftime("%b %d %H:%M:%S")
            display_segments["End"] = display_segments["end"].dt.strftime("%b %d %H:%M:%S")
            display_segments["Duration"] = display_segments["duration_s"].map(format_seconds)
            display_segments = display_segments.rename(
                columns={
                    "peak_floor_moving": "Peak floor moving",
                    "peak_counter_stationary": "Peak counter stationary",
                }
            )
            st.dataframe(
                display_segments[["Start", "End", "Duration", "Peak floor moving", "Peak counter stationary"]],
                width="stretch",
                hide_index=True,
            )

        st.info(
            "Interpretation: if the counter zone is stationary while selected floor zones show repeated movement, "
            "the dashboard flags a service opportunity. This does not identify staff or customers; it infers behavior from zone, speed, and dwell."
        )

elif active_view == "Executive View":
    render_heatmap_banner(
        "Executive View",
        "High-level traffic, attention, and sample health for quick reporting.",
    )
    render_section_heading("Retail Readout", f"Current {hours}h window compared with the previous matching window.")
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

    render_section_heading("Traffic And Attention", "Traffic over time on the left, strongest zones on the right.")
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
        st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig, width="stretch")

elif active_view == "Zones":
    render_heatmap_banner(
        "Zone Performance",
        "Detailed zone-by-zone readout for dwell, occupied time, visits, and activity heat.",
    )
    render_section_heading("Zone Maps", "Compare person-minutes with occupied-time to separate popularity from duration.")
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

    render_section_heading("Zone Table", "Operational export for all measured zones.")
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
    st.dataframe(display_zone_table.round(2), width="stretch", hide_index=True)
    st.download_button(
        "Download zone performance CSV",
        data=display_zone_table.to_csv(index=False).encode("utf-8"),
        file_name="ld2450_zone_performance.csv",
        mime="text/csv",
    )

elif active_view == "Dwell":
    render_heatmap_banner(
        "Dwell Analysis",
        "Time-based view of how long people stayed and how dwell is distributed.",
    )
    render_section_heading("Dwell Over Time", "Use this to see whether attention is growing, fading, or shifting across zones.")
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
            st.plotly_chart(fig, width="stretch")
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
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No occupied sessions in this window.")

    render_section_heading("Recent Sessions", "Latest occupied stretches merged using the sidebar session gap.")
    if sessions.empty:
        st.write("No occupied sessions.")
    else:
        recent_sessions = sessions.tail(20).copy()
        recent_sessions["dwell"] = recent_sessions["dwell_s"].map(format_seconds)
        recent_sessions["person_minutes"] = recent_sessions["person_seconds"] / 60
        st.dataframe(
            recent_sessions[["start", "end", "peak_people", "dwell", "person_minutes"]].sort_values("start", ascending=False),
            width="stretch",
            hide_index=True,
        )

elif active_view == "Campaign Compare":
    render_heatmap_banner(
        "Campaign Compare",
        f"Compares the current {hours}h window with the previous {hours}h window for one store location.",
    )

    campaign_zone = st.selectbox(
        "Campaign / display location",
        zone_options,
        format_func=lambda zone: zone_display_name(zone, zone_aliases),
    )
    campaign_name = zone_display_name(campaign_zone, zone_aliases)

    def zone_row(table: pd.DataFrame, zone_label: str) -> pd.Series | None:
        if table.empty:
            return None
        working = table.copy()
        working["zone_label"] = working["zone"].map(lambda value: clean_label(value).upper())
        match = working[working["zone_label"] == zone_label]
        return None if match.empty else match.iloc[0]

    def metric_from_row(row: pd.Series | None, column: str) -> float:
        if row is None or column not in row:
            return 0.0
        return float(row[column] or 0)

    def target_minutes(table: pd.DataFrame, zone_label: str, behaviors: list[str]) -> float:
        if table.empty:
            return 0.0
        filtered = table[(table["zone_label"] == zone_label) & table["behavior"].isin(behaviors)]
        return float(filtered["duration_s"].sum()) / 60.0 if not filtered.empty else 0.0

    def crowd_minutes(table: pd.DataFrame, zone_label: str) -> float:
        if table.empty:
            return 0.0
        working = table.copy()
        working["zone_label"] = working["zone"].map(lambda value: clean_label(value).upper())
        match = working[working["zone_label"] == zone_label]
        return float(match.iloc[0]["crowd_pressure"] or 0) if not match.empty else 0.0

    after_row = zone_row(zone_table, campaign_zone)
    before_row = zone_row(previous_zone_table, campaign_zone)
    after_dwell = metric_from_row(after_row, "dwell_minutes")
    before_dwell = metric_from_row(before_row, "dwell_minutes")
    after_visits = metric_from_row(after_row, "estimated_visits")
    before_visits = metric_from_row(before_row, "estimated_visits")
    after_avg_dwell = metric_from_row(after_row, "avg_dwell_s")
    before_avg_dwell = metric_from_row(before_row, "avg_dwell_s")
    after_motion = target_minutes(target_view, campaign_zone, ["Approaching", "Leaving"])
    before_motion = target_minutes(previous_target_view, campaign_zone, ["Approaching", "Leaving"])
    after_stationary = target_minutes(target_view, campaign_zone, ["Engaged stationary"])
    before_stationary = target_minutes(previous_target_view, campaign_zone, ["Engaged stationary"])
    after_crowd = crowd_minutes(concentration_table, campaign_zone)
    before_crowd = crowd_minutes(previous_concentration_table, campaign_zone)

    dwell_delta = format_delta(after_dwell, before_dwell)
    visit_delta = format_delta(after_visits, before_visits)
    motion_delta = format_delta(after_motion, before_motion)
    avg_delta = format_delta(after_avg_dwell, before_avg_dwell)

    if before_dwell <= 0 and after_dwell > 0:
        campaign_result = "New attention"
        campaign_note = "This location has measurable attention now; keep watching the next window."
    elif after_dwell > before_dwell * 1.15:
        campaign_result = "Lift"
        campaign_note = "The location is holding more attention than the previous period."
    elif after_dwell < before_dwell * 0.85 and before_dwell > 0:
        campaign_result = "Drop"
        campaign_note = "Attention fell. Refresh the sign, product facing, or staff prompt."
    elif after_motion > before_motion * 1.25 and after_avg_dwell <= before_avg_dwell:
        campaign_result = "Passing interest"
        campaign_note = "More people moved through, but they did not stay longer."
    else:
        campaign_result = "Stable"
        campaign_note = "No major change yet. Let the campaign run longer or adjust the offer."

    comp_cols = st.columns(5)
    with comp_cols[0]:
        callout_card("Campaign Result", campaign_result, campaign_note)
    comp_cols[1].metric("Dwell", format_minutes(after_dwell), dwell_delta)
    comp_cols[2].metric("Visits", f"{int(after_visits)}", visit_delta)
    comp_cols[3].metric("Avg Stay", format_seconds(after_avg_dwell), avg_delta)
    comp_cols[4].metric("Movement", format_minutes(after_motion), motion_delta)

    compare_data = pd.DataFrame(
        [
            {"Metric": "Dwell minutes", "Before": before_dwell, "After": after_dwell},
            {"Metric": "Estimated visits", "Before": before_visits, "After": after_visits},
            {"Metric": "Movement minutes", "Before": before_motion, "After": after_motion},
            {"Metric": "Stationary minutes", "Before": before_stationary, "After": after_stationary},
            {"Metric": "Group pressure", "Before": before_crowd, "After": after_crowd},
        ]
    )
    compare_long = compare_data.melt(id_vars="Metric", var_name="Window", value_name="Value")
    fig = px.bar(
        compare_long,
        x="Metric",
        y="Value",
        color="Window",
        barmode="group",
        title=f"Before vs After: {campaign_name}",
        color_discrete_map={"Before": "#94a3b8", "After": "#0f9f6e"},
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=52, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#111827",
        xaxis_title="",
        yaxis_title="Minutes / count",
        legend_title="Window",
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Campaign Brief")
    brief_lines = [
        f"{campaign_name} recorded {format_minutes(after_dwell)} of dwell in the current window versus {format_minutes(before_dwell)} before.",
        f"Movement was {format_minutes(after_motion)} now versus {format_minutes(before_motion)} before.",
        f"Average stay is {format_seconds(after_avg_dwell)} now versus {format_seconds(before_avg_dwell)} before.",
    ]
    if after_motion > before_motion and after_avg_dwell <= before_avg_dwell:
        brief_lines.append("People are noticing or passing the location, but the display is not holding them yet.")
    elif after_dwell > before_dwell:
        brief_lines.append("The location is doing more work than before; this is a positive campaign signal.")
    else:
        brief_lines.append("The location has not improved yet; adjust the product facing, price message, or staff prompt.")

    render_owner_brief(
        brief_lines,
        [
            (
                "Run one controlled change",
                f"Change only one thing at {campaign_name}, then compare this same view after the next {hours}h window.",
            ),
            (
                "Watch dwell, not only visits",
                "A good campaign should increase stay time or returns, not just people walking past.",
            ),
        ],
    )

    st.subheader("All Location Lift")
    if previous_zone_table.empty:
        st.info("Previous-period comparison will appear once there is enough history.")
    else:
        comparison = zone_table[["zone", "dwell_minutes", "estimated_visits"]].copy()
        comparison["zone_label"] = comparison["zone"].map(lambda value: clean_label(value).upper())
        previous_comp = previous_zone_table[["zone", "dwell_minutes", "estimated_visits"]].copy()
        previous_comp["zone_label"] = previous_comp["zone"].map(lambda value: clean_label(value).upper())
        comparison = comparison.merge(
            previous_comp[["zone_label", "dwell_minutes", "estimated_visits"]].rename(
                columns={
                    "dwell_minutes": "previous_dwell_minutes",
                    "estimated_visits": "previous_visits",
                }
            ),
            on="zone_label",
            how="left",
        )
        comparison["previous_dwell_minutes"] = comparison["previous_dwell_minutes"].fillna(0)
        comparison["previous_visits"] = comparison["previous_visits"].fillna(0)
        comparison["dwell_lift_pct"] = comparison.apply(
            lambda row: ((row["dwell_minutes"] - row["previous_dwell_minutes"]) / row["previous_dwell_minutes"] * 100)
            if row["previous_dwell_minutes"] > 0
            else None,
            axis=1,
        )
        comparison["Store location"] = comparison["zone_label"].map(lambda zone: zone_display_name(zone, zone_aliases))
        st.dataframe(
            comparison.sort_values("dwell_minutes", ascending=False)[
                ["Store location", "dwell_minutes", "previous_dwell_minutes", "estimated_visits", "previous_visits", "dwell_lift_pct"]
            ].rename(
                columns={
                    "dwell_minutes": "Current dwell min",
                    "previous_dwell_minutes": "Previous dwell min",
                    "estimated_visits": "Current visits",
                    "previous_visits": "Previous visits",
                    "dwell_lift_pct": "Dwell lift %",
                }
            ).round(2),
            width="stretch",
            hide_index=True,
        )

elif active_view == "Targets":
    latest_targets = latest_targets_table(latest)
    counted_latest = latest_targets[latest_targets["Counted"] == True] if not latest_targets.empty else pd.DataFrame()
    current_target_count = len(counted_latest)
    current_target_zones = (
        ", ".join(counted_latest["Zone"].dropna().map(lambda value: clean_label(value).upper()).unique()[:3])
        if not counted_latest.empty
        else ("Clear" if is_live else "Offline")
    )
    avg_current_distance = float(counted_latest["Distance mm"].mean()) if not counted_latest.empty else 0.0

    st.subheader("Target Lens")
    control_cols = st.columns([1.1, 1.1, 1, 1])
    with control_cols[0]:
        recent_target_limit = st.slider("Recent target trail", min_value=50, max_value=1000, value=300, step=50)
    recent_targets = target_view.tail(recent_target_limit).copy() if not target_view.empty else pd.DataFrame()

    with control_cols[1]:
        color_mode = st.selectbox(
            "Color by",
            ["Behavior", "Motion", "Zone", "Distance band", "Target slot"],
            index=0,
        )
    color_column = {
        "Behavior": "behavior",
        "Motion": "motion",
        "Zone": "zone_label",
        "Distance band": "distance_band",
        "Target slot": "target_label",
    }[color_mode]

    filtered_targets = recent_targets.copy()
    with control_cols[2]:
        counted_only = st.checkbox("Counted only", value=True)
    if counted_only and not filtered_targets.empty:
        filtered_targets = filtered_targets[filtered_targets["counted"]].copy()

    with control_cols[3]:
        behavior_options = sorted(filtered_targets["behavior"].dropna().unique().tolist()) if not filtered_targets.empty else []
        selected_behaviors = st.multiselect("Behavior", behavior_options, default=behavior_options)
    filtered_targets = apply_selection_filter(filtered_targets, "behavior", selected_behaviors, behavior_options)

    filter_cols = st.columns(3)
    with filter_cols[0]:
        motion_options = sorted(filtered_targets["motion"].dropna().unique().tolist()) if not filtered_targets.empty else []
        selected_motions = st.multiselect("Motion", motion_options, default=motion_options)
    filtered_targets = apply_selection_filter(filtered_targets, "motion", selected_motions, motion_options)

    with filter_cols[1]:
        zone_options = sorted(filtered_targets["zone_label"].dropna().unique().tolist()) if not filtered_targets.empty else []
        selected_zones = st.multiselect("Zone", zone_options, default=zone_options)
    filtered_targets = apply_selection_filter(filtered_targets, "zone_label", selected_zones, zone_options)

    with filter_cols[2]:
        band_options = sorted(filtered_targets["distance_band"].dropna().unique().tolist()) if not filtered_targets.empty else []
        selected_bands = st.multiselect("Distance band", band_options, default=band_options)
    filtered_targets = apply_selection_filter(filtered_targets, "distance_band", selected_bands, band_options)

    approach_count = int((filtered_targets["behavior"] == "Approaching").sum()) if not filtered_targets.empty else 0
    leaving_count = int((filtered_targets["behavior"] == "Leaving").sum()) if not filtered_targets.empty else 0
    stationary_minutes = (
        float(filtered_targets.loc[filtered_targets["behavior"] == "Engaged stationary", "duration_s"].sum()) / 60.0
        if not filtered_targets.empty
        else 0.0
    )
    dominant_behavior = top_value(filtered_targets["behavior"], "None") if not filtered_targets.empty else "None"

    target_cols = st.columns(4)
    with target_cols[0]:
        callout_card("Current Targets", str(current_target_count) if is_live else "--", "Counted targets right now")
    with target_cols[1]:
        callout_card("Current Zones", current_target_zones, "Where the latest target slots are located")
    with target_cols[2]:
        callout_card("Dominant Behavior", dominant_behavior, "From visible filtered observations")
    with target_cols[3]:
        callout_card("Stationary Time", format_minutes(stationary_minutes), "Engaged stationary time in filtered trail")

    insight_cols = st.columns(4)
    with insight_cols[0]:
        callout_card("Avg Distance", f"{avg_current_distance / 1000:.2f}m" if avg_current_distance else "--", "Current counted targets")
    with insight_cols[1]:
        callout_card("Approach / Leave", f"{approach_count} / {leaving_count}", "Directional observations in filtered trail")
    with insight_cols[2]:
        callout_card("Visible Trail", f"{len(filtered_targets)} obs", "After filters")
    with insight_cols[3]:
        callout_card("Color Mode", color_mode, "Applied to map and trail chart")

    render_floor_map(filtered_targets, x_edges, y_edges, x_names, y_names, color_by=color_column)

    left, right = st.columns(2)
    with left:
        if not filtered_targets.empty:
            fig = px.scatter(
                filtered_targets,
                x="captured_at",
                y="distance_mm",
                color=color_column,
                symbol="motion",
                hover_data=["zone_label", "x_mm", "y_mm", "speed_cms", "resolution_mm", "behavior"],
                title=f"Target Distance Trail Colored by {color_mode}",
                color_discrete_map={
                    "Approaching": "#0f9f6e",
                    "Engaged stationary": "#2563eb",
                    "Leaving": "#e86e32",
                    "Passerby / out of zone": "#94a3b8",
                    "STATIONARY": "#2563eb",
                    "APPROACHING": "#0f9f6e",
                    "MOVING_AWAY": "#e86e32",
                },
            )
            fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=52, b=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
                xaxis_title="Time",
                yaxis_title="Distance from radar, mm",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No target observations in this window.")

    with right:
        if not filtered_targets.empty:
            behavior_mix = filtered_targets.groupby("behavior", dropna=False).size().reset_index(name="observations")
            fig = px.bar(
                behavior_mix.sort_values("observations"),
                x="observations",
                y="behavior",
                orientation="h",
                title="Behavior Mix",
                color="behavior",
                color_discrete_map={
                    "Approaching": "#0f9f6e",
                    "Engaged stationary": "#2563eb",
                    "Leaving": "#e86e32",
                    "Passerby / out of zone": "#94a3b8",
                },
            )
            fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=52, b=10),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font_color="#111827",
                xaxis_title="Observations",
                yaxis_title="",
                showlegend=False,
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No target observations in this window.")

    if not filtered_targets.empty:
        band_counts = filtered_targets.groupby("distance_band", observed=False).size().reset_index(name="observations")
        fig = px.bar(
            band_counts,
            x="distance_band",
            y="observations",
            title="Target Observations by Distance Band",
            color="observations",
            color_continuous_scale=["#cfece6", "#14956f", "#f0b84a"],
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=52, b=10),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font_color="#111827",
            xaxis_title="",
            yaxis_title="Observations",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, width="stretch")

        zone_behavior = (
            filtered_targets.groupby(["zone_label", "behavior"], as_index=False)
            .agg(observations=("captured_at", "count"), minutes=("duration_s", lambda values: float(values.sum()) / 60.0))
            .sort_values(["observations", "minutes"], ascending=False)
        )
        st.subheader("Zone x Behavior Detail")
        st.dataframe(
            zone_behavior.rename(
                columns={
                    "zone_label": "Zone",
                    "behavior": "Behavior",
                    "observations": "Observations",
                    "minutes": "Minutes",
                }
            ).round(2),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Latest Targets")
    if latest_targets.empty:
        st.write("No current targets.")
    else:
        st.dataframe(latest_targets, width="stretch", hide_index=True)

    st.info(
        "LD2450 target fields are position, speed, distance, angle, and resolution. "
        "They are useful for movement and zone behavior, but not reliable for age, identity, height, or body-size classification."
    )

elif active_view == "Setup":
    render_heatmap_banner(
        "Zone Naming Setup",
        "Rename radar zones into store language. These names make Owner Brief and Campaign Compare easier to read.",
    )

    settings_ready = bool(stored_zone_aliases)
    if not settings_ready:
        st.info(
            "Zone names will work in this session immediately. To persist them across devices and redeploys, "
            "run the updated supabase_schema.sql once in Supabase SQL Editor."
        )

    preset_aliases = bedroom_zone_preset(zone_options)
    if preset_aliases:
        preset_col, note_col = st.columns([1, 2])
        with preset_col:
            apply_preset = st.button("Apply bedroom preset")
        with note_col:
            st.caption("Uses the supplied photo: bed, sofas, wardrobe, curtains, walkway, and back wall.")

        if apply_preset:
            merged_aliases = {**zone_aliases, **preset_aliases}
            st.session_state["zone_aliases"] = merged_aliases
            ok, message = save_dashboard_setting(ZONE_LABELS_KEY, merged_aliases)
            if ok:
                st.success("Bedroom zone names saved to Supabase.")
            else:
                st.warning("Bedroom names are active for this session, but could not be saved yet.")
                st.caption(message)
            st.rerun()

    st.subheader("Store Location Names")
    with st.form("zone_name_setup"):
        new_aliases: dict[str, str] = {}
        for row_idx, row_name in enumerate(y_names):
            cols = st.columns(len(x_names))
            for col_idx, col_name in enumerate(x_names):
                technical = clean_label(f"{row_name} {col_name}").upper()
                with cols[col_idx]:
                    friendly = st.text_input(
                        technical,
                        value=zone_aliases.get(technical, default_zone_name(technical)),
                        key=f"zone_alias_{row_idx}_{col_idx}",
                    ).strip()
                    if friendly:
                        new_aliases[technical] = friendly

        save_names = st.form_submit_button("Save zone names")

    if save_names:
        st.session_state["zone_aliases"] = new_aliases
        ok, message = save_dashboard_setting(ZONE_LABELS_KEY, new_aliases)
        if ok:
            st.success("Zone names saved to Supabase.")
        else:
            st.warning(
                "Zone names are active for this session, but could not be saved to Supabase yet. "
                "Run the updated supabase_schema.sql, then save again."
            )
            st.caption(message)
        st.rerun()

    st.subheader("Name Preview")
    preview_rows = [
        {"Technical zone": zone, "Store name": zone_display_name(zone, zone_aliases)}
        for zone in zone_options
    ]
    st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)

elif active_view == "Data Health":
    latest_network = latest.get("network") or {}
    health_cols = st.columns(4)
    health_cols[0].metric("Last Upload Age", format_seconds(latest_age_s))
    health_cols[1].metric("Frame Count", int(latest.get("frames_count") or 0))
    health_cols[2].metric("Bad Frames", int(latest.get("bad_frames_count") or 0))
    health_cols[3].metric("Firmware", latest.get("firmware") or "unknown")

    details = {
        "sensor_id": latest.get("sensor_id"),
        "captured_at": str(latest.get("captured_at")),
        "firmware": latest.get("firmware"),
        "network_mode": latest_network.get("mode"),
        "ip": latest_network.get("ip"),
        "ssid": latest_network.get("ssid"),
        "rssi_dbm": latest_network.get("rssiDbm"),
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
        width="stretch",
        hide_index=True,
    )
