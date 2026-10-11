import { test } from "node:test";
import assert from "node:assert/strict";
import { deckFromCatalog, estimateSol, collectionUri, SOL_PER_ASSET, SOL_PER_COLLECTION } from "../src/deck.mjs";

const catalog = {
  xq4_153: { edition: null, period: "4" },          // demo ship, not a card
  "p5-01": { edition: "3", period: "5" },
  "p4-01": { edition: "1", period: "4" },
  "p4-02": { edition: "2", period: "4" },
};

test("the deck is every card in edition order, demo ships left out", () => {
  const deck = deckFromCatalog(catalog, "https://example.com/automons");
  assert.deepEqual(deck.map((s) => s.id), ["p4-01", "p4-02", "p5-01"]);
  assert.equal(deck[2].name, "Spaceship #3");
  assert.equal(deck[0].uri, "https://example.com/automons/nft/p4-01.json");
  assert.equal(collectionUri("https://example.com/automons/"),
               "https://example.com/automons/nft/collection.json");
});

test("the estimate only counts what's still to mint", () => {
  const deck = deckFromCatalog(catalog, "https://x/");
  const fresh = estimateSol(deck, { assets: {} });
  assert.equal(fresh.remaining, 3);
  assert.ok(Math.abs(fresh.mint - (SOL_PER_COLLECTION + 3 * SOL_PER_ASSET)) < 1e-12);
  const half = estimateSol(deck, { collection: "C", assets: { "p4-01": "A" } });
  assert.equal(half.remaining, 2);
  assert.ok(Math.abs(half.mint - 2 * SOL_PER_ASSET) < 1e-12);
});

test("99 cards cost about a third of a SOL", () => {
  const big = {};
  for (let i = 1; i <= 99; i++) big["s" + i] = { edition: String(i) };
  const { mint } = estimateSol(deckFromCatalog(big, "https://x/"), { assets: {} });
  assert.ok(mint > 0.3 && mint < 0.33, String(mint));
});
