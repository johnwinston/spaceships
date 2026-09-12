import { test } from "node:test";
import assert from "node:assert/strict";
import { claimCode, normalise, verifyCode, ALPHABET } from "../src/claimcode.js";

const SECRET = "test-secret";
// Shared with tests/test_claimcode.py -- both implementations must agree.
const VECTORS = { "p4-01": "GQE2-Q3K7", "xq4_153": "C6CZ-BH9W" };

test("known vectors match the Python implementation", async () => {
  for (const [ship, code] of Object.entries(VECTORS)) {
    assert.equal(await claimCode(ship, SECRET), code);
  }
});

test("codes use the plotter-safe alphabet", async () => {
  for (let n = 1; n < 60; n++) {
    const code = await claimCode(`p4-${String(n).padStart(2, "0")}`, SECRET);
    assert.match(code, /^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/);
    for (const ch of code.replace("-", "")) assert.ok(ALPHABET.includes(ch));
  }
});

test("normalise forgives case, spacing and look-alikes", () => {
  assert.equal(normalise(" gqe2 q3k7 "), "GQE2Q3K7");
  assert.equal(normalise("oi1l-abcd"), "0111ABCD");
  assert.equal(normalise("short"), null);
  assert.equal(normalise("UUUU-UUUU"), null);
  assert.equal(normalise(42), null);
});

test("verifyCode accepts the right code and rejects the rest", async () => {
  assert.ok(await verifyCode("p4-01", "gqe2-q3k7", SECRET));
  assert.ok(await verifyCode("p4-01", "GQE2Q3K7", SECRET));
  assert.equal(await verifyCode("p4-01", "GQE2-Q3K8", SECRET), false);
  assert.equal(await verifyCode("p4-02", "GQE2-Q3K7", SECRET), false);
  assert.equal(await verifyCode("p4-01", "", SECRET), false);
  assert.equal(await verifyCode("p4-01", "GQE2-Q3K7", "other-secret"), false);
});
