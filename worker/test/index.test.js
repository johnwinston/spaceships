import { test } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const ORIGIN = "https://john-winston.com";
const BASE = "https://claims.test";

function fakeKV() {
  const store = new Map();
  return {
    async get(key, type) {
      const hit = store.get(key);
      if (!hit) return null;
      return type === "json" ? JSON.parse(hit.value) : hit.value;
    },
    async put(key, value, opts) {
      store.set(key, { value, metadata: (opts && opts.metadata) || null });
    },
    async delete(key) { store.delete(key); },
    async list({ prefix = "" } = {}) {
      const keys = [...store]
        .filter(([k]) => k.startsWith(prefix))
        .map(([name, v]) => ({ name, metadata: v.metadata }));
      return { keys, list_complete: true, cursor: undefined };
    },
  };
}

function makeEnv(overrides = {}) {
  return {
    CLAIMS: fakeKV(),
    CLAIM_SECRET: "test-secret",
    ADMIN_TOKEN: "admin-token",
    ALLOWED_ORIGINS: ORIGIN + ",http://localhost:8765",
    CLAIM_LIMITER: { limit: async () => ({ success: true }) },
    ...overrides,
  };
}

const ctx = { waitUntil() {}, passThroughOnException() {} };

async function call(env, method, path, body, headers = {}) {
  const init = { method, headers: { Origin: ORIGIN, ...headers } };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  const res = await worker.fetch(new Request(BASE + path, init), env, ctx);
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  return { status: res.status, headers: res.headers, data };
}

test("health check and CORS for an allowed origin", async () => {
  const r = await call(makeEnv(), "GET", "/");
  assert.equal(r.status, 200);
  assert.equal(r.data.service, "spaceships-claims");
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGIN);
  assert.equal(r.headers.get("Vary"), "Origin");
});

test("no CORS headers for an unknown origin", async () => {
  const r = await call(makeEnv(), "GET", "/", undefined, { Origin: "https://evil.example" });
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), null);
});

test("preflight succeeds", async () => {
  const r = await call(makeEnv(), "OPTIONS", "/claim");
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("Access-Control-Allow-Methods"), "GET, POST, OPTIONS");
});

test("claiming with the right code records the claim", async () => {
  const env = makeEnv();
  const r = await call(env, "POST", "/claim", { ship: "p4-01", code: "gqe2 q3k7", name: "  Ana   Lu  " });
  assert.equal(r.status, 200);
  assert.equal(r.data.ok, true);
  assert.equal(r.data.updated, false);
  assert.equal(r.data.claim.name, "Ana Lu");
  assert.ok(r.data.claim.claimedAt);

  const one = await call(env, "GET", "/claims/p4-01");
  assert.equal(one.status, 200);
  assert.equal(one.data.claim.name, "Ana Lu");

  const all = await call(env, "GET", "/claims");
  assert.equal(all.status, 200);
  assert.deepEqual(Object.keys(all.data.claims), ["p4-01"]);
  assert.equal(all.data.claims["p4-01"].name, "Ana Lu");
  assert.match(all.headers.get("Cache-Control"), /max-age/);
});

test("the wrong code is rejected and nothing is stored", async () => {
  const env = makeEnv();
  const r = await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K8" });
  assert.equal(r.status, 403);
  assert.equal((await call(env, "GET", "/claims/p4-01")).status, 404);
});

test("a valid code on a claimed ship updates the name", async () => {
  const env = makeEnv();
  await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7", name: "Ana" });
  const r = await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7", name: "Ana L." });
  assert.equal(r.status, 200);
  assert.equal(r.data.updated, true);
  assert.equal(r.data.claim.name, "Ana L.");
  assert.ok(r.data.claim.updatedAt);
});

test("malformed input is rejected before any crypto", async () => {
  const env = makeEnv();
  assert.equal((await call(env, "POST", "/claim", { ship: "P4-01; drop", code: "GQE2-Q3K7" })).status, 400);
  assert.equal((await call(env, "POST", "/claim", { ship: "p4-01", code: "nope" })).status, 400);
  assert.equal((await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7", name: "x".repeat(41) })).status, 400);
  assert.equal((await call(env, "POST", "/claim", [1, 2])).status, 400);
  const bad = await worker.fetch(new Request(BASE + "/claim", { method: "POST", body: "{not json" }), env, ctx);
  assert.equal(bad.status, 400);
});

test("claims are closed without a secret", async () => {
  const r = await call(makeEnv({ CLAIM_SECRET: "" }), "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7" });
  assert.equal(r.status, 503);
});

test("rate limiter turns writes away with 429", async () => {
  const env = makeEnv({ CLAIM_LIMITER: { limit: async () => ({ success: false }) } });
  const r = await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7" });
  assert.equal(r.status, 429);
  assert.equal(r.headers.get("Retry-After"), "60");
});

test("unclaim needs the admin token", async () => {
  const env = makeEnv();
  await call(env, "POST", "/claim", { ship: "p4-01", code: "GQE2-Q3K7", name: "Ana" });
  assert.equal((await call(env, "POST", "/admin/unclaim", { ship: "p4-01" })).status, 401);
  assert.equal((await call(env, "POST", "/admin/unclaim", { ship: "p4-01" },
    { Authorization: "Bearer wrong" })).status, 401);
  const ok = await call(env, "POST", "/admin/unclaim", { ship: "p4-01" },
    { Authorization: "Bearer admin-token" });
  assert.equal(ok.status, 200);
  assert.equal((await call(env, "GET", "/claims/p4-01")).status, 404);
});

test("unknown routes 404 and handler errors become 500 JSON", async () => {
  assert.equal((await call(makeEnv(), "GET", "/nope")).status, 404);
  const env = makeEnv({ CLAIMS: { list: async () => { throw new Error("kv down"); } } });
  const r = await call(env, "GET", "/claims");
  assert.equal(r.status, 500);
  assert.equal(r.data.error, "internal error");
});
