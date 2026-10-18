/* Spaceships claim service -- one Cloudflare Worker, one KV namespace.
 *
 *   GET  /claims            every claim: { "<ship>": { name, claimedAt } }
 *   GET  /claims/<ship>     one claim, or 404
 *   POST /claim             { ship, code, name?, wallet? } -> records the
 *                           claim (a valid code on an already-claimed ship
 *                           updates the name, so typos are fixable); with
 *                           a wallet, also sends the ship's NFT there
 *                           from the vault (see solana.js), once
 *   POST /admin/unclaim     { ship }, Authorization: Bearer <ADMIN_TOKEN>
 *
 * The only secret-bearing step is code verification: codes are derived
 * from CLAIM_SECRET (see claimcode.js), never stored, so the KV holds
 * nothing an attacker could use to forge one.  The vault key that sends
 * NFTs is the other secret; the chain, not KV, is the truth about who
 * holds an NFT, so a lost KV write can never send a ship twice.
 */
import { verifyCode, normalise, timingSafeEqualStrings } from "./claimcode.js";
import deployment from "./deployment.json" with { type: "json" };

const KEY_PREFIX = "claim:";
const SHIP_ID = /^[a-z0-9][a-z0-9_-]{0,31}$/;
const NAME_MAX = 40;
const BODY_MAX = 4096;
const LIST_MAX_AGE_S = 15;
// A Solana address: 32 bytes in base58, 32 to 44 characters.
const BASE58 = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

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
        wallet: meta.wallet || null,
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

  const wallet = cleanWallet(body.value.wallet);
  if (wallet === null) {
    return json({ error: "That doesn't look like a Solana wallet address." }, 400);
  }

  const key = KEY_PREFIX + ship;
  const existing = await env.CLAIMS.get(key, "json");
  const now = new Date().toISOString();
  let record = existing
    ? { ...existing, name, updatedAt: now }
    : { ship, name, claimedAt: now };

  if (wallet) {
    const sent = await sendNft(ship, wallet, record, env);
    if (sent.error) {
      // Still keep the claim itself (and the name) if it's new.
      if (!existing) await save(env, key, record);
      return json({ error: sent.error, claim: publicView(sent.record || record) }, sent.status);
    }
    record = sent.record;
  }

  await save(env, key, record);
  console.log(JSON.stringify({
    message: wallet ? "nft sent" : existing ? "claim updated" : "claimed", ship,
  }));
  return json({ ok: true, updated: Boolean(existing), claim: publicView(record) });
}

/** Transfer the ship's NFT to `wallet`, at most once.  Resolves
 *  { record } on success or { error, status, record? }. */
async function sendNft(ship, wallet, record, env) {
  if (record.wallet) {
    return { error: "This ship's NFT is already in a wallet.", status: 409, record };
  }
  const asset = (deployment.assets || {})[ship];
  if (!asset) return { error: "The NFTs aren't minted yet. Check back soon.", status: 503 };
  const chain = await loadChain(env);
  if (!chain) return { error: "NFT sending isn't switched on yet.", status: 503 };

  let tx;
  try {
    tx = await chain.send(asset, wallet);
  } catch (err) {
    console.error(JSON.stringify({
      message: "nft send failed", ship,
      error: err instanceof Error ? err.message : String(err),
    }));
    // A transfer that failed because the vault no longer holds the asset
    // means it already went out (a racing claim, or KV lost the write).
    let owner = null;
    try { owner = await chain.ownerOf(asset); } catch { /* RPC down */ }
    if (owner && owner !== chain.vault) {
      const fixed = { ...record, wallet: owner, asset, cluster: deployment.cluster };
      await save(env, KEY_PREFIX + ship, fixed);
      return { error: "This ship's NFT is already in a wallet.", status: 409, record: fixed };
    }
    return { error: "Couldn't send the NFT just now. Try again in a minute.", status: 502 };
  }
  return {
    record: {
      ...record, wallet, asset, tx,
      cluster: deployment.cluster, sentAt: new Date().toISOString(),
    },
  };
}

async function save(env, key, record) {
  await env.CLAIMS.put(key, JSON.stringify(record), {
    metadata: { name: record.name, claimedAt: record.claimedAt, wallet: record.wallet || null },
  });
}

/* Tests hand in a fake as env.CHAIN; production builds the real one
 * (and only pays to load the Solana libraries when a wallet is given). */
async function loadChain(env) {
  if (env.CHAIN) return env.CHAIN;
  const { makeChain } = await import("./solana.js");
  return makeChain(env, deployment);
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
    wallet: record.wallet || null,
    asset: record.asset || null,
    tx: record.tx || null,
    cluster: record.cluster || null,
  };
}

/** Trim, collapse whitespace, drop control characters; null if too long. */
function cleanName(raw) {
  if (raw === undefined || raw === null) return "";
  const name = String(raw).replace(/[\p{Cc}\p{Cf}]/gu, "").replace(/\s+/g, " ").trim();
  return name.length > NAME_MAX ? null : name;
}

/** "" when absent, the address when it looks like one, null otherwise. */
function cleanWallet(raw) {
  if (raw === undefined || raw === null || raw === "") return "";
  const wallet = String(raw).trim();
  return BASE58.test(wallet) ? wallet : null;
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
