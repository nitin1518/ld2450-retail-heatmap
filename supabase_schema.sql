create extension if not exists pgcrypto;

create table if not exists public.sensor_snapshots (
  id uuid primary key default gen_random_uuid(),
  sensor_id text not null,
  captured_at timestamptz not null default now(),
  device_uptime_ms bigint,
  firmware text,
  people_now smallint not null default 0,
  frames_count bigint not null default 0,
  bad_frames_count bigint not null default 0,
  dropped_bytes bigint not null default 0,
  rx_bytes bigint not null default 0,
  last_frame_age_ms bigint,
  hottest_zone text,
  hottest_row smallint,
  hottest_col smallint,
  hottest_heat integer not null default 0,
  zone_now jsonb not null,
  zone_heat jsonb not null,
  zone_x_names jsonb not null,
  zone_y_names jsonb not null,
  zone_x_edges jsonb not null,
  zone_y_edges jsonb not null,
  targets jsonb not null,
  network jsonb not null default '{}'::jsonb,
  raw_payload jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists sensor_snapshots_sensor_time_idx
  on public.sensor_snapshots (sensor_id, captured_at desc);

create index if not exists sensor_snapshots_time_idx
  on public.sensor_snapshots (captured_at desc);

create index if not exists sensor_snapshots_hottest_zone_idx
  on public.sensor_snapshots (hottest_zone, captured_at desc);

create table if not exists public.dashboard_settings (
  setting_key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.sensor_snapshots enable row level security;
alter table public.dashboard_settings enable row level security;

-- Edge Functions and the Streamlit dashboard should use a server-side service role key.
-- No public table policy is created here, so browser clients cannot read or write directly.
