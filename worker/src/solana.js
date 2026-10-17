/* Sending a ship's NFT out of the vault.
 *
 * Every ship is pre-minted (chain/src/premint.mjs) as a Metaplex Core
 * asset owned by the vault wallet.  A successful claim with a wallet
 * address transfers that asset to the buyer; the vault pays the fee
 * (~0.000005 SOL), so the buyer needs no SOL at all.
 *
 *   SOLANA_RPC_URL      secret: an RPC endpoint for the cluster in deployment.json
 *                       (not the public solana.com ones: they 403 Workers)
 *   VAULT_SECRET_KEY    secret: the vault keypair, as the JSON byte array
 *                       solana-keygen / chain/src/new-vault.mjs write
 *
 * Loaded lazily by index.js, so the claim service still works (name-only
 * claims) before anything is minted.
 */
import { createUmi } from "@metaplex-foundation/umi-bundle-defaults";
import { keypairIdentity, publicKey } from "@metaplex-foundation/umi";
import { base58 } from "@metaplex-foundation/umi/serializers";
import { mplCore, fetchAssetV1, transferV1 } from "@metaplex-foundation/mpl-core";

export function makeChain(env, deployment) {
  if (!env.SOLANA_RPC_URL || !env.VAULT_SECRET_KEY) return null;
  const umi = createUmi(env.SOLANA_RPC_URL, { commitment: "confirmed" }).use(mplCore());
  const secret = Uint8Array.from(JSON.parse(env.VAULT_SECRET_KEY));
  const vault = umi.eddsa.createKeypairFromSecretKey(secret);
  umi.use(keypairIdentity(vault));
  const collection = deployment.collection ? publicKey(deployment.collection) : undefined;

  return {
    vault: String(vault.publicKey),

    async ownerOf(asset) {
      const fetched = await fetchAssetV1(umi, publicKey(asset));
      return String(fetched.owner);
    },

    /** Transfer `asset` from the vault to `wallet`; resolves the tx signature.
     *  Confirms by polling rather than umi's sendAndConfirm: that waits on a
     *  websocket subscription which never fires inside a Worker, so it sat
     *  until the blockhash expired and threw although the transfer landed. */
    async send(asset, wallet) {
      const signature = await transferV1(umi, {
        asset: publicKey(asset),
        newOwner: publicKey(wallet),
        collection,
      }).send(umi);
      await waitForSignature((sigs) => umi.rpc.getSignatureStatuses(sigs), signature);
      return base58.deserialize(signature)[0];
    },
  };
}

const CONFIRMED = new Set(["confirmed", "finalized"]);

/** Poll `getStatuses([signature])` until the transaction is confirmed.
 *  Throws if it failed on chain or isn't confirmed within `timeoutMs`
 *  (index.js then asks the chain who owns the asset). */
export async function waitForSignature(getStatuses, signature, {
  timeoutMs = 30000, intervalMs = 1000,
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
} = {}) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const [status] = await getStatuses([signature]);
    if (status && status.error) {
      throw new Error(`transaction failed: ${JSON.stringify(status.error)}`);
    }
    if (status && CONFIRMED.has(status.commitment)) return status;
    if (Date.now() >= deadline) throw new Error("transaction not confirmed in time");
    await sleep(intervalMs);
  }
}
