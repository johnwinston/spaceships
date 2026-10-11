/* Sending a ship's NFT out of the vault.
 *
 * Every ship is pre-minted (chain/src/premint.mjs) as a Metaplex Core
 * asset owned by the vault wallet.  A successful claim with a wallet
 * address transfers that asset to the buyer; the vault pays the fee
 * (~0.000005 SOL), so the buyer needs no SOL at all.
 *
 *   SOLANA_RPC_URL      secret: an RPC endpoint for the cluster in assets.json
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

    /** Transfer `asset` from the vault to `wallet`; resolves the tx signature. */
    async send(asset, wallet) {
      const result = await transferV1(umi, {
        asset: publicKey(asset),
        newOwner: publicKey(wallet),
        collection,
      }).sendAndConfirm(umi);
      return base58.deserialize(result.signature)[0];
    },
  };
}
