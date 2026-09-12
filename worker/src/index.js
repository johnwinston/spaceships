/* Spaceships claim service -- one Cloudflare Worker, one KV namespace.
 *
 *   GET  /claims            every claim: { "<ship>": { name, claimedAt } }
 *   GET  /claims/<ship>     one claim, or 404
 *   POST /claim             { ship, code, name? } -> records the claim
 *                           (a valid code on an already-claimed ship
 *                           updates the name, so typos are fixable)
 *   POST /admin/unclaim     { ship }, Authorization: Bearer <ADMIN_TOKEN>
 *
 * The only secret-bearing step is code verification: codes are derived
 * from CLAIM_SECRET (see claimcode.js), never stored, so the KV holds
 * nothing an attacker could use to forge one.
 */
import { verifyCode, normalise, timingSafeEqualStrings } from "./claimcode.js";

const KEY_PREFIX = "claim:";
const SHIP_ID = /^[a-z0-9][a-z0-9_-]{0,31}$/;
const NAME_MAX = 40;
const BODY_MAX = 4096;
const LIST_MAX_AGE_S = 15;

export default {
  async fetch(request, env, ctx) {
    const cors = corsHeaders(request.headers.get("Origin"), env);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    try {
      const res = await route(request, env);
      for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
      return res;
    } catch (err) {
      console.error(JSON.stringify({
        message: "unhandled error",
        error: err instanceof Error ? err.message : String(err),
        path: new URL(request.url).pathname,
      }));
      return json({ error: "internal error" }, 500, cors);
    }
  },
};

async function route(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = request.method;

  if (method === "GET" && path === "/") {
    return json({ service: "spaceships-claims", ok: true });
  }
  if (method === "GET" && path === "/claims") return listClaims(env);
  if (method === "GET" && path.startsWith("/claims/")) {
    return getClaim(path.slice("/claims/".length), env);
  }
  if (method === "POST" && path === "/claim") return claim(request, env);
  if (method === "POST" && path === "/admin/unclaim") return unclaim(request, env);
  return json({ error: "not found" }, 404);
}

/* ---- handlers ------------------------------------------------------- */

async function listClaims(env) {
  const claims = {};
  let cursor;
  do {
    const page = await env.CLAIMS.list({ prefix: KEY_PREFIX, cursor });
    for (const key of page.keys) {
      const meta = key.metadata || {};
      claims[key.name.slice(KEY_PREFIX.length)] = {
        name: meta.name || "",
        claimedAt: meta.claimedAt || null,
      };
    }
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return json({ claims }, 200, { "Cache-Control": "public, max-age=" + LIST_MAX_AGE_S });
}

async function getClaim(ship, env) {
  if (!SHIP_ID.test(ship)) return json({ error: "bad ship id" }, 400);
  const record = await env.CLAIMS.get(KEY_PREFIX + ship, "json");
  if (!record) return json({ error: "unclaimed", ship }, 404);
  return json({ claim: publicView(record) });
}

async function claim(request, env) {
  const limited = await rateLimited(request, env);
  if (limited) return limited;
  const body = await readJson(request);
  if (body.error) return json({ error: body.error }, body.status);

  const ship = String(body.value.ship || "").toLowerCase();
  if (!SHIP_ID.test(ship)) return json({ error: "bad ship id" }, 400);
  if (normalise(body.value.code) === null) {
    return json({ error: "A claim code is eight letters and digits, like ABCD-2345." }, 400);
  }
  const name = cleanName(body.value.name);
  if (name === null) return json({ error: "name is too long" }, 400);
  if (!env.CLAIM_SECRET) return json({ error: "claims are not open yet" }, 503);

  const ok = await verifyCode(ship, body.value.code, env.CLAIM_SECRET);
  if (!ok) {
    console.log(JSON.stringify({ message: "claim rejected", ship }));
    return json({ error: "That code doesn't match this ship." }, 403);
  }

  const key = KEY_PREFIX + ship;
  const existing = await env.CLAIMS.get(key, "json");
  const now = new Date().toISOString();
  const record = existing
    ? { ...existing, name, updatedAt: now }
    : { ship, name, claimedAt: now };
  await env.CLAIMS.put(key, JSON.stringify(record), {
    metadata: { name: record.name, claimedAt: record.claimedAt },
  });
  console.log(JSON.stringify({ message: existing ? "claim updated" : "claimed", ship }));
  return json({ ok: true, updated: Boolean(existing), claim: publicView(record) });
}

async function unclaim(request, env) {
  const limited = await rateLimited(request, env);
  if (limited) return limited;
  if (!env.ADMIN_TOKEN) return json({ error: "admin is not configured" }, 503);
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!(await timingSafeEqualStrings(token, env.ADMIN_TOKEN))) {
    return json({ error: "unauthorized" }, 401);
  }
  const body = await readJson(request);
  if (body.error) return json({ error: body.error }, body.status);
  const ship = String(body.value.ship || "").toLowerCase();
  if (!SHIP_ID.test(ship)) return json({ error: "bad ship id" }, 400);
  await env.CLAIMS.delete(KEY_PREFIX + ship);
  console.log(JSON.stringify({ message: "unclaimed", ship }));
  return json({ ok: true, ship });
}

/* ---- helpers -------------------------------------------------------- */

function publicView(record) {
  return {
    ship: record.ship,
    name: record.name || "",
    claimedAt: record.claimedAt || null,
    updatedAt: record.updatedAt || null,
  };
}

/** Trim, collapse whitespace, drop control characters; null if too long. */
function cleanName(raw) {
  if (raw === undefined || raw === null) return "";
  const name = String(raw).replace(/[\p{Cc}\p{Cf}]/gu, "").replace(/\s+/g, " ").trim();
  return name.length > NAME_MAX ? null : name;
}

async function readJson(request) {
  const declared = Number(request.headers.get("Content-Length") || 0);
  if (declared > BODY_MAX) return { error: "body too large", status: 413 };
  let text;
  try {
    text = await request.text();
  } catch {
    return { error: "unreadable body", status: 400 };
  }
  if (text.length > BODY_MAX) return { error: "body too large", status: 413 };
  try {
    const value = JSON.parse(text || "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { error: "expected a JSON object", status: 400 };
    }
    return { value };
  } catch {
    return { error: "invalid JSON", status: 400 };
  }
}

/** 429 when the caller's IP is over the write limit, else null. */
async function rateLimited(request, env) {
  if (!env.CLAIM_LIMITER) {
    console.log(JSON.stringify({ message: "rate limiter binding missing; skipping" }));
    return null;
  }
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const { success } = await env.CLAIM_LIMITER.limit({ key: ip });
  if (success) return null;
  return json({ error: "Too many attempts. Wait a minute and try again." }, 429,
              { "Retry-After": "60" });
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || "")
    .split(",").map((s) => s.trim()).filter(Boolean);
  if (!origin || !allowed.includes(origin)) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...extra },
  });
}
