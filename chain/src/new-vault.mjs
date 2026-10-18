/* Make the vault wallet: the one that holds every unclaimed ship and
 * pays the claim fees.
 *
 *   node src/new-vault.mjs [path]
 *
 * Writes a keypair file in the same format solana-keygen uses (a JSON
 * array of 64 bytes) and prints its address.  Default path:
 * ~/.config/spaceships/vault.keypair.json.  Never commit it; it is the
 * one key that can move unclaimed ships.  The same bytes go into the
 * claim service with `wrangler secret put VAULT_SECRET_KEY`.
 */
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { webcrypto } from "node:crypto";
import { createUmi } from "@metaplex-foundation/umi-bundle-defaults";

const path = process.argv[2] || join(homedir(), ".config", "spaceships", "vault.keypair.json");
if (existsSync(path)) {
  console.error(`${path} already exists; refusing to overwrite a wallet.`);
  process.exit(1);
}
// No network needed; umi is only used for its ed25519 implementation.
const umi = createUmi("https://api.devnet.solana.com");
const seed = webcrypto.getRandomValues(new Uint8Array(32));
const kp = umi.eddsa.createKeypairFromSeed(seed);
mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
writeFileSync(path, JSON.stringify(Array.from(kp.secretKey)) + "\n", { mode: 0o600 });
console.log(`vault address: ${kp.publicKey}`);
console.log(`keypair file:  ${path}`);

