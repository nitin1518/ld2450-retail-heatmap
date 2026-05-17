import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-device-token",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function getServiceRoleKey(): string {
  const direct = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SB_SERVICE_ROLE_KEY");
  if (direct) return direct;

  const secretKeys = Deno.env.get("SUPABASE_SECRET_KEYS");
  if (secretKeys) {
    const parsed = JSON.parse(secretKeys);
    return parsed.service_role ?? parsed.serviceRole ?? parsed.secret ?? "";
  }

  return "";
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST required" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const expectedToken = Deno.env.get("LD2450_DEVICE_TOKEN");
  const actualToken = req.headers.get("x-device-token");

  if (!expectedToken || actualToken !== expectedToken) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = getServiceRoleKey();

  if (!supabaseUrl || !serviceRoleKey) {
    return new Response(JSON.stringify({ error: "missing Supabase server config" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let body: Record<string, unknown>;

  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const sensorId = String(body.sensorId ?? "unknown");
  const snapshot = body.snapshot as Record<string, any> | undefined;

  if (!snapshot || typeof snapshot !== "object") {
    return new Response(JSON.stringify({ error: "snapshot object required" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const zones = snapshot.zones ?? {};
  const cells = Array.isArray(zones.cells) ? zones.cells : [];
  const zoneNow = cells.map((row: any[]) => row.map((cell) => Number(cell?.now ?? 0)));
  const zoneHeat = cells.map((row: any[]) => row.map((cell) => Number(cell?.heat ?? 0)));
  const hottest = snapshot.hottest ?? {};

  const row = {
    sensor_id: sensorId,
    device_uptime_ms: Number(body.deviceUptimeMs ?? 0),
    firmware: String(body.firmware ?? ""),
    people_now: Number(snapshot.peopleNow ?? 0),
    frames_count: Number(snapshot.frames ?? 0),
    bad_frames_count: Number(snapshot.badFrames ?? 0),
    dropped_bytes: Number(snapshot.droppedBytes ?? 0),
    rx_bytes: Number(snapshot.rxBytes ?? 0),
    last_frame_age_ms: Number(snapshot.lastFrameAgeMs ?? 0),
    hottest_zone: String(hottest.zone ?? "none"),
    hottest_row: Number(hottest.row ?? -1),
    hottest_col: Number(hottest.col ?? -1),
    hottest_heat: Number(hottest.heat ?? 0),
    zone_now: zoneNow,
    zone_heat: zoneHeat,
    zone_x_names: zones.xNames ?? [],
    zone_y_names: zones.yNames ?? [],
    zone_x_edges: zones.xEdges ?? [],
    zone_y_edges: zones.yEdges ?? [],
    targets: snapshot.targets ?? [],
    network: snapshot.network ?? {},
    raw_payload: body,
  };

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });

  const { error } = await supabase.from("sensor_snapshots").insert(row);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 201,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
