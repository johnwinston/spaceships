/* Point the minted collection and every asset at a new site.
 *
 *   node src/repoint.mjs --cluster mainnet-beta --site https://john-winston.com/spaceships/ --dry-run
 *   node src/repoint.mjs --cluster mainnet-beta --site ... --spend-real-sol
 *
 * Rewrites the on-chain uri of the collection and of each asset in
 * chain/deployments/<cluster>.json to <site>/nft/<id>.json (the vault is
 * the update authority).  Anything already pointing there is skipped, so
 * a re-run after a rate limit or crash only does what's left.  Mainnet
 * refuses to start without --spend-real-sol; --dry-run reads the chain
 * and prints the cost without sending anything.
 */
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { createUmi } from "@metaplex-foundation/umi-bundle-defaults";
import { keypairIdentity, publicKey } from "@metaplex-foundation/umi";
import {
  mplCore, fetchAsset, fetchCollection, update, updateCollection,
} from "@metaplex-foundation/mpl-core";
import { CLUSTERS, collectionUri, loadState } from "./deck.mjs";

const LAMPORTS = 1e9;
const FEE_LAMPORTS = 5000;          // one signature per update
const RENT_LAMPORTS_PER_BYTE = 6960; // rent-exempt rate; a longer uri grows the account

const { values: args } = parseArgs({
  options: {
    cluster: { type: "string", default: "devnet" },
    keypair: { type: "string" },
    rpc: { type: "string" },
    site: { type: "string" },
    "spend-real-sol": { type: "boolean", default: false },
    "dry-run": { type: "boolean", default: false },
  },
});

const cluster = args.cluster;
if (!CLUSTERS[cluster]) die(`--cluster must be one of: ${Object.keys(CLUSTERS).join(", ")}`);
if (!args.site) die("--site is required, e.g. https://john-winston.com/spaceships/");
if (cluster === "mainnet-beta" && !args["spend-real-sol"] && !args["dry-run"]) {
  die("mainnet spends real SOL. Re-run with --dry-run to see the cost, then --spend-real-sol.");
}
const base = args.site.endsWith("/") ? args.site : args.site + "/";

const state = loadState(cluster);
if (!state.collection || !state.assets) die(`nothing minted on ${cluster} yet`);

const keypairPath = (args.keypair || join(homedir(), ".config", "spaceships", "vault.keypair.json"))
  .replace(/^~(?=\/)/, homedir());
const umi = createUmi(args.rpc || CLUSTERS[cluster], { commitment: "confirmed" }).use(mplCore());
const vault = umi.eddsa.createKeypairFromSecretKey(
  Uint8Array.from(JSON.parse(readFileSync(keypairPath, "utf8"))));
umi.use(keypairIdentity(vault));
if (state.vault !== String(vault.publicKey)) {
  die(`this ${cluster} deployment belongs to vault ${state.vault}, not ${vault.publicKey}`);
}

const collection = await fetchCollection(umi, publicKey(state.collection));
const todo = [];
if (collection.uri !== collectionUri(base)) {
  todo.push({ id: "collection", from: collection.uri, to: collectionUri(base) });
}
for (const [id, address] of Object.entries(state.assets)) {
  const asset = await fetchAsset(umi, publicKey(address));
  const to = `${base}nft/${id}.json`;
  if (asset.uri !== to) todo.push({ id, asset, from: asset.uri, to });
}

const grow = todo.reduce((n, t) => n + Math.max(0, t.to.length - t.from.length), 0);
const cost = (todo.length * FEE_LAMPORTS + grow * RENT_LAMPORTS_PER_BYTE) / LAMPORTS;
const balance = Number((await umi.rpc.getBalance(vault.publicKey)).basisPoints) / LAMPORTS;
const assetCount = Object.keys(state.assets).length;
console.log(`${cluster}: ${todo.length} of ${assetCount + 1} uris to change (collection + ${assetCount} assets)`);
if (todo[0]) console.log(`e.g. ${todo[0].from}\n  -> ${todo[0].to}`);
console.log(`estimated cost: ${cost.toFixed(6)} SOL; vault balance ${balance.toFixed(4)} SOL`);
if (args["dry-run"] || !todo.length) process.exit(0);
if (balance < cost) die(`the vault needs ${cost.toFixed(6)} SOL; send the difference to ${state.vault}`);

for (const t of todo) {
  const builder = t.id === "collection"
    ? updateCollection(umi, { collection: collection.publicKey, uri: t.to })
    : update(umi, { asset: t.asset, collection, uri: t.to });
  await builder.sendAndConfirm(umi);
  console.log(`${t.id}  ${t.to}`);
}
console.log(`done: ${todo.length} uris now point at ${base}`);
process.exit(0); // umi keeps a websocket open, which would hold node alive

function die(message) {
  console.error(message);
  process.exit(1);
}
