import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import deployment from "../src/deployment.json" with { type: "json" };

// Sending NFTs from the vault, against a fake chain.
const BASE = "https://claims.test";
const VAULT = "VauLt1111111111111111111111111111111111111";
const BUYER = "7Np41oeYqPefeNQEHSv1UDhYrehxin3NStELsSKCT4K2";
const OTHER = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin";
const ASSET = "Asset11111111111111111111111111111111111111";

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

function fakeChain({ fail = false } = {}) {
  const owners = new Map([[ASSET, VAULT]]);
  const sent = [];
  return {
    vault: VAULT,
    sent,
    owners,
    async ownerOf(asset) { return owners.get(asset); },
    async send(asset, wallet) {
      if (fail || owners.get(asset) !== VAULT) throw new Error("not the owner");
      owners.set(asset, wallet);
      sent.push([asset, wallet]);
      return "5igSig" + sent.length;
    },
  };
}

function makeEnv(chain) {
  return {
    CLAIMS: fakeKV(),
    CLAIM_SECRET: "test-secret",
    ALLOWED_ORIGINS: "",
    CLAIM_LIMITER: { limit: async () => ({ success: true }) },
    CHAIN: chain,
  };
}

async function claim(env, body) {
  const res = await worker.fetch(new Request(BASE + "/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }), env, {});
  return { status: res.status, data: await res.json() };
}

const CODE = "GQE2-Q3K7"; // p4-01 under test-secret

beforeEach(() => {
  deployment.cluster = "devnet";
  deployment.collection = null;
  deployment.assets = { "p4-01": ASSET };
});

test("a valid code plus a wallet sends the NFT and records it", async () => {
  const chain = fakeChain();
  const env = makeEnv(chain);
  const r = await claim(env, { ship: "p4-01", code: CODE, wallet: BUYER });
  assert.equal(r.status, 200);
  assert.deepEqual(chain.sent, [[ASSET, BUYER]]);
  assert.equal(r.data.claim.wallet, BUYER);
  assert.equal(r.data.claim.asset, ASSET);
  assert.equal(r.data.claim.cluster, "devnet");
  assert.ok(r.data.claim.tx);
});

test("the NFT only ever goes out once", async () => {
  const chain = fakeChain();
  const env = makeEnv(chain);
  await claim(env, { ship: "p4-01", code: CODE, wallet: BUYER });
  const again = await claim(env, { ship: "p4-01", code: CODE, wallet: OTHER });
  assert.equal(again.status, 409);
  assert.equal(again.data.claim.wallet, BUYER);
  assert.equal(chain.sent.length, 1);
  // A name-only update still works after the send.
  const named = await claim(env, { ship: "p4-01", code: CODE, name: "Ana" });
  assert.equal(named.status, 200);
  assert.equal(named.data.claim.wallet, BUYER);
});

test("if KV lost the record, the chain still stops a second send", async () => {
  const chain = fakeChain();
  chain.owners.set(ASSET, OTHER); // already out, but KV knows nothing
  const env = makeEnv(chain);
  const r = await claim(env, { ship: "p4-01", code: CODE, wallet: BUYER });
  assert.equal(r.status, 409);
  assert.equal(r.data.claim.wallet, OTHER);
});

test("a wrong code sends nothing", async () => {
  const chain = fakeChain();
  const r = await claim(makeEnv(chain), { ship: "p4-01", code: "GQE2-Q3K8", wallet: BUYER });
  assert.equal(r.status, 403);
  assert.equal(chain.sent.length, 0);
});

test("a malformed wallet is rejected", async () => {
  const chain = fakeChain();
  const r = await claim(makeEnv(chain), { ship: "p4-01", code: CODE, wallet: "0xabc" });
  assert.equal(r.status, 400);
  assert.equal(chain.sent.length, 0);
});

test("before minting, the claim is kept and the send is deferred", async () => {
  deployment.assets = {};
  const env = makeEnv(fakeChain());
  const r = await claim(env, { ship: "p4-01", code: CODE, wallet: BUYER, name: "Ana" });
  assert.equal(r.status, 503);
  assert.equal(r.data.claim.name, "Ana");
  assert.equal(r.data.claim.wallet, null);
});

test("an RPC failure is a retryable 502 and records no wallet", async () => {
  const env = makeEnv(fakeChain({ fail: true }));
  const r = await claim(env, { ship: "p4-01", code: CODE, wallet: BUYER });
  assert.equal(r.status, 502);
  assert.equal(r.data.claim.wallet, null);
});

test("the send finishes under waitUntil, so a page refresh can't cut it short", async () => {
  const chain = fakeChain();
  const env = makeEnv(chain);
  const pending = [];
  const ctx = { waitUntil(p) { pending.push(p); }, passThroughOnException() {} };
  const res = await worker.fetch(new Request(BASE + "/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ship: "p4-01", code: CODE, wallet: BUYER }),
  }), env, ctx);
  assert.equal(res.status, 200);
  assert.equal(pending.length, 1);
  await Promise.all(pending);
  const saved = await env.CLAIMS.get("claim:p4-01", "json");
  assert.equal(saved.wallet, BUYER);
});
