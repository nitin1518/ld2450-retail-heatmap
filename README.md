# LD2450 Remote Retail Heatmap

This folder turns the ESP32 + LD2450 into a remote historical dashboard:

ESP32 -> Supabase Edge Function -> Supabase Postgres -> Streamlit dashboard

## Why this stack

- Supabase gives persistent Postgres storage on its free plan.
- Supabase Edge Functions give a small authenticated ingest endpoint, so the ESP32 does not need a database service-role key.
- Streamlit Community Cloud can host the dashboard for free from a GitHub repo.

## 1. Create Supabase tables

1. Create a free Supabase project.
2. Open Supabase SQL Editor.
3. Run `supabase_schema.sql`.

## 2. Deploy the ingest function

Install and log in to the Supabase CLI, then from this `cloud` folder:

```bash
supabase link --project-ref mfansktqlesaqiumgtsf
supabase secrets set LD2450_DEVICE_TOKEN="make-a-long-random-token"
supabase secrets set SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
supabase functions deploy ld2450-ingest --no-verify-jwt
```

The ESP32 ingest URL will be:

```text
https://mfansktqlesaqiumgtsf.functions.supabase.co/ld2450-ingest
```

## 3. Configure the ESP32 sketch

In `LD2450_PeopleCounter.ino`, change:

```cpp
#define CLOUD_UPLOAD_ENABLED 1
#define CLOUD_INGEST_URL "https://mfansktqlesaqiumgtsf.functions.supabase.co/ld2450-ingest"
#define CLOUD_DEVICE_ID "store-zone-1"
#define CLOUD_DEVICE_TOKEN "the-same-long-random-token"
```

Upload the sketch again. The ESP32 will send a snapshot every `CLOUD_UPLOAD_INTERVAL_MS`.

## 4. Run Streamlit locally

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and fill in your values:

```toml
SUPABASE_URL = "https://mfansktqlesaqiumgtsf.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
DASHBOARD_PASSWORD = "change-this-password"
```

Then:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 5. Deploy remote dashboard

1. Push this `cloud` folder to a GitHub repo.
2. Open Streamlit Community Cloud.
3. Deploy `streamlit_app.py`.
4. Add the same secrets in Streamlit app settings.
5. Open the Streamlit URL from anywhere.

## Notes

- Keep the Supabase service-role key only in Supabase Edge Function secrets and Streamlit secrets.
- Do not commit `.streamlit/secrets.toml`.
- If you deploy the Streamlit app publicly, keep `DASHBOARD_PASSWORD` set.
