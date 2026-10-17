import { test } from "node:test";
import assert from "node:assert/strict";
import { waitForSignature } from "../src/solana.js";

// Confirming a transfer by polling signature statuses (no websockets in Workers).
const SIG = new Uint8Array(64);
const noSleep = async () => {};

function statuses(...seq) {
  let i = 0;
  return async (sigs) => {
    assert.deepEqual(sigs, [SIG]);
    return [seq[Math.min(i++, seq.length - 1)]];
  };
}

test("waits through unknown and processed until confirmed", async () => {
  const got = await waitForSignature(
    statuses(null, { commitment: "processed", error: null }, { commitment: "confirmed", error: null }),
    SIG, { sleep: noSleep });
  assert.equal(got.commitment, "confirmed");
});

test("finalized counts as confirmed", async () => {
  const got = await waitForSignature(statuses({ commitment: "finalized", error: null }), SIG, { sleep: noSleep });
  assert.equal(got.commitment, "finalized");
});

test("throws when the transaction failed on chain", async () => {
  await assert.rejects(
    waitForSignature(statuses({ commitment: "confirmed", error: { InstructionError: [0, "Custom"] } }), SIG, { sleep: noSleep }),
    /transaction failed/);
});

test("throws after the timeout if never confirmed", async () => {
  await assert.rejects(
    waitForSignature(statuses(null), SIG, { timeoutMs: 0, sleep: noSleep }),
    /not confirmed in time/);
});
