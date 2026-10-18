/* Pure helpers shared by the chain scripts: which ships to mint, what
 * each is called, where its metadata lives, and what it all costs. */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const COLLECTION_NAME = "Spaceships";

// Cost model, in SOL (Metaplex docs, Oct 2026): a Core asset is ~0.0015
// rent + 0.0015 protocol fee + the tx fee; a collection about the same.
// Kept a little pessimistic so the balance check never runs short.
export const SOL_PER_ASSET = 0.0032;
export const SOL_PER_COLLECTION = 0.0032;
export const SOL_PER_TRANSFER = 0.00001;

export const CLUSTERS = {
  devnet: "https://api.devnet.solana.com",
  "mainnet-beta": "https://api.mainnet-beta.solana.com",
};

/** [{ id, edition, name, uri }] for every real card, in edition order. */
export function deckFromCatalog(catalog, site) {
  const base = site.endsWith("/") ? site : site + "/";
  return Object.entries(catalog)
    .filter(([, e]) => Number(e.edition) > 0)
    .sort((a, b) => Number(a[1].edition) - Number(b[1].edition))
    .map(([id, e]) => ({
      id,
      edition: Number(e.edition),
      // Must match src/nft_metadata.py's "name".
      name: "Spaceship #" + Number(e.edition),
      uri: base + "nft/" + id + ".json",
    }));
}

export function collectionUri(site) {
  return (site.endsWith("/") ? site : site + "/") + "nft/collection.json";
}

/** SOL still to spend to finish minting, given what's already on chain. */
export function estimateSol(deck, state) {
  const remaining = deck.filter((s) => !(state.assets || {})[s.id]).length;
  const collection = state.collection ? 0 : SOL_PER_COLLECTION;
  return {
    remaining,
    mint: collection + remaining * SOL_PER_ASSET,
    transfers: deck.length * SOL_PER_TRANSFER,
  };
}

/* ---- deployment record ------------------------------------------------
 * chain/deployments/<cluster>.json is the record of what exists on chain.
 * The active one is copied to worker/src/deployment.json (so the claim
 * service knows which asset is which ship) and web/nft/deployment.json
 * (so the site can link each ship to its NFT). */

export function statePath(cluster) {
  return join(REPO, "chain", "deployments", cluster + ".json");
}

export function loadState(cluster) {
  const path = statePath(cluster);
  if (!existsSync(path)) return { cluster, collection: null, vault: null, assets: {} };
  return JSON.parse(readFileSync(path, "utf8"));
}

export function saveState(state) {
  const text = JSON.stringify(state, null, 2) + "\n";
  for (const path of [
    statePath(state.cluster),
    join(REPO, "worker", "src", "deployment.json"),
    join(REPO, "web", "nft", "deployment.json"),
  ]) {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, text);
  }
}
