/* Pre-mint the whole collection into the vault.
 *
 *   node src/premint.mjs --keypair ~/.config/spaceships/vault.keypair.json
 *   node src/premint.mjs --keypair ... --cluster mainnet-beta --spend-real-sol
 *
 * Creates one Metaplex Core collection ("Spaceships") and one Core asset
 * per card, all owned by the vault, each pointing at
 * <site>/nft/<id>.json (written by `python -m src.nft_metadata`).
 *
 * Safe to re-run: every asset is recorded in chain/deployments/<cluster>.json
 * as soon as it exists, and a re-run only mints what's missing.  Devnet
 * is the default and costs nothing (free test SOL, --airdrop); mainnet
 * refuses to start without --spend-real-sol and prints the cost first.
 */
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { createUmi } from "@metaplex-foundation/umi-bundle-defaults";
import { generateSigner, keypairIdentity, publicKey, sol } from "@metaplex-foundation/umi";
import { mplCore, create, createCollection, fetchCollection } from "@metaplex-foundation/mpl-core";
import {
  REPO, CLUSTERS, COLLECTION_NAME, deckFromCatalog, collectionUri,
  estimateSol, loadState, saveState,
} from "./deck.mjs";

const { values: args } = parseArgs({
  options: {
    cluster: { type: "string", default: "devnet" },
    keypair: { type: "string" },
    rpc: { type: "string" },
    site: { type: "string", default: "https://john-winston.com/spaceships/" },
    catalog: { type: "string", default: join(REPO, "web", "catalog.json") },
    only: { type: "string" },             // comma-separated ship ids, for a trial run
    airdrop: { type: "boolean", default: false },
    "spend-real-sol": { type: "boolean", default: false },
    "dry-run": { type: "boolean", default: false },
  },
});

const cluster = args.cluster;
if (!CLUSTERS[cluster]) die(`--cluster must be one of: ${Object.keys(CLUSTERS).join(", ")}`);
if (cluster === "mainnet-beta" && !args["spend-real-sol"] && !args["dry-run"]) {
  die("mainnet spends real SOL. Re-run with --dry-run to see the cost, then --spend-real-sol.");
}

const catalog = JSON.parse(readFileSync(args.catalog, "utf8"));
let deck = deckFromCatalog(catalog, args.site);
if (args.only) {
  const keep = new Set(args.only.split(",").map((s) => s.trim()));
  deck = deck.filter((s) => keep.has(s.id));
}
const state = loadState(cluster);
const cost = estimateSol(deck, state);
console.log(`${cluster}: ${deck.length} ships, ${cost.remaining} still to mint`);
console.log(`estimated cost: ${cost.mint.toFixed(4)} SOL to mint, `
  + `plus ~${cost.transfers.toFixed(4)} SOL kept for claim transfers`);

const keypairPath = (args.keypair || join(homedir(), ".config", "spaceships", "vault.keypair.json"))
  .replace(/^~(?=\/)/, homedir());
const umi = createUmi(args.rpc || CLUSTERS[cluster], { commitment: "confirmed" }).use(mplCore());
const secret = Uint8Array.from(JSON.parse(readFileSync(keypairPath, "utf8")));
const vault = umi.eddsa.createKeypairFromSecretKey(secret);
umi.use(keypairIdentity(vault));
if (state.vault && state.vault !== String(vault.publicKey)) {
  die(`this ${cluster} deployment belongs to vault ${state.vault}, not ${vault.publicKey}`);
}
state.vault = String(vault.publicKey);
console.log(`vault: ${state.vault}`);

if (args.airdrop) {
  if (cluster !== "devnet") die("--airdrop is devnet only");
  await umi.rpc.airdrop(vault.publicKey, sol(1));
}
const balance = Number((await umi.rpc.getBalance(vault.publicKey)).basisPoints) / 1e9;
console.log(`balance: ${balance.toFixed(4)} SOL`);
if (args["dry-run"]) process.exit(0);
const needed = cost.mint + cost.transfers;
if (balance < needed) {
  die(`the vault needs ${needed.toFixed(4)} SOL; send the difference to ${state.vault}`
    + (cluster === "devnet" ? " (or pass --airdrop)" : ""));
}

await checkMetadata(deck[0]);

if (!state.collection) {
  const signer = generateSigner(umi);
  await createCollection(umi, {
    collection: signer,
    name: COLLECTION_NAME,
    uri: collectionUri(args.site),
  }).sendAndConfirm(umi);
  state.collection = String(signer.publicKey);
  saveState(state);
  console.log(`collection: ${state.collection}`);
}
const collection = await fetchCollection(umi, publicKey(state.collection));

state.assets = state.assets || {};
for (const ship of deck) {
  if (state.assets[ship.id]) continue;
  const asset = generateSigner(umi);
  await create(umi, {
    asset,
    collection,
    name: ship.name,
    uri: ship.uri,
    owner: vault.publicKey,
  }).sendAndConfirm(umi);
  state.assets[ship.id] = String(asset.publicKey);
  saveState(state); // after every mint, so a crash never loses one
  console.log(`${ship.id}  ${ship.name}  ${asset.publicKey}`);
}
console.log(`done: ${Object.keys(state.assets).length} ships in the vault on ${cluster}`);

async function checkMetadata(ship) {
  if (!ship) return;
  try {
    const res = await fetch(ship.uri);
    if (res.ok) return;
    console.warn(`warning: ${ship.uri} returned ${res.status}; wallets will show no image until it's live`);
  } catch {
    console.warn(`warning: couldn't fetch ${ship.uri}; wallets will show no image until it's live`);
  }
}

function die(message) {
  console.error(message);
  process.exit(1);
}
