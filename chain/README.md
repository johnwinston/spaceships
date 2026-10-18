# Spaceships on Solana

Every card's ship is a Solana NFT. All 99 are minted up front into a
**vault** wallet that John controls. When someone buys a card, John hands
them that card's **claim QR** from a private booklet. They scan it, paste
their wallet address, and the claim service sends the ship from the vault
to their wallet. The buyer needs no SOL and pays nothing.

## Pieces

| Piece | Where | What it does |
|---|---|---|
| Metadata + art | `python -m src.nft_metadata` → `web/nft/` | One JSON + looping gif per ship, served by GitHub Pages at `<site>/nft/<id>.json` |
| Vault wallet | `chain/src/new-vault.mjs` | Makes the keypair that holds unclaimed ships and pays fees |
| Pre-mint | `chain/src/premint.mjs` | One Core collection + one Core asset per ship, owned by the vault; records addresses in `chain/deployments/<cluster>.json`, `worker/src/deployment.json`, `web/nft/deployment.json` |
| Claim booklet | `python -m src.claim_sheet` → `data/claim_sheet.html` | Private, printable: one QR per ship that opens the player with its claim code filled in |
| Claim service | `worker/` (`POST /claim` with `wallet`) | Checks the code, sends the asset from the vault (`worker/src/solana.js`), records who holds it; never sends a ship twice |
| Claim page | `web/play.html` | Code (prefilled from the QR), wallet address or "use my Phantom wallet", result with an explorer link |
| Collection | `web/index.html` | Every ship, claimed or not, and whether its NFT is in a wallet |

## Choices, and why

- **Solana, Metaplex Core.** Core is the cheapest full NFT on Solana and
  a transfer is a single instruction. Compressed NFTs would save a few
  dollars in total but need a paid indexer (DAS) to transfer each one.
  That isn't worth it at n = 99.
- **Pre-mint into a vault, transfer on claim.** All ships show up as one
  verified collection before anyone buys. The chain decides who holds
  each NFT, so a lost KV write can't send a ship twice: the second
  transfer fails because the vault no longer owns it.
- **Claim codes stay off the cards.** Plotted backs carry only the play
  link. The secret is in the booklet QR, which John keeps. Sheets 01–11
  were plotted with an 8-character code under the QR. Deploy the claim
  service with a **new** `CLAIM_SECRET` so those printed codes are dead.
- **Metadata on the site, not Arweave (for now).** Hosting it on the
  site is free. The vault is the update authority, so the URIs can move
  to permanent storage later without re-minting.
- **No royalties** for now. Adding a Royalties plugin to the collection
  is a later, one-transaction change.

## Cost

Per Metaplex's docs (Oct 2026), a Core asset costs about 0.003 SOL: about
0.0015 SOL of rent and a 0.0015 SOL protocol fee. A transfer is about
0.000005 SOL.

| | SOL |
|---|---|
| Collection | ~0.003 |
| 99 assets | ~0.31 |
| 99 claim transfers | ~0.001 |
| **Total** | **~0.32** (≈ $35 at $110/SOL) |

`premint.mjs --dry-run` prints the live estimate and the vault balance.
Devnet costs nothing.

## Runbook

Run everything below on the Mac from the repo root unless noted.

```bash
# 0. metadata + art live on the site (merge to master; Pages deploys web/)
python -m src.nft_metadata

# 1. vault wallet (once).  Prints its address; keep the file safe.
cd chain && npm install
node src/new-vault.mjs                      # ~/.config/spaceships/vault.keypair.json

# 2. devnet rehearsal: free test SOL, nothing real
node src/premint.mjs --airdrop --only p4-01,p4-02      # two ships first
node src/premint.mjs --airdrop                          # then the rest
#    (the public faucet is rate limited; faucet.solana.com works too)

# 3. claim service (worker/README.md has the first-time steps)
python -m src.claimcode --new-secret        # NEW secret, not the one on the plotted backs
npx wrangler secret put CLAIM_SECRET
npx wrangler secret put SOLANA_RPC_URL      # a Helius devnet URL; see Known limits
npx wrangler secret put VAULT_SECRET_KEY < ~/.config/spaceships/vault.keypair.json
npx wrangler deploy                         # deploys worker/src/deployment.json with it

# 4. booklet: same new secret
AUTOMONS_CLAIM_SECRET=... python -m src.claim_sheet     # data/claim_sheet.html, print it

# 5. mainnet: send ~0.33 SOL to the vault address, then
node src/premint.mjs --cluster mainnet-beta --dry-run
node src/premint.mjs --cluster mainnet-beta --spend-real-sol
#    commit the deployment files it wrote, set SOLANA_RPC_URL to a mainnet
#    RPC (Helius free tier is plenty), redeploy the worker, push web/
```

Steps 1 and 2 are safe to run any time. Step 5 spends real SOL.

## Known limits

- The public RPC endpoints (api.devnet / api.mainnet-beta.solana.com)
  answer 403 to any request from a Cloudflare Worker, so the claim
  service needs a third-party RPC even for the devnet rehearsal. A free
  Helius account gives both a devnet and a mainnet URL. Pre-minting from
  a laptop works against the public endpoints, though they rate limit;
  premint resumes where it stopped.
- The Worker loads the Solana libraries only when a claim includes a
  wallet. If a claim ever hits the free plan's CPU limit, the $5/month
  Workers plan raises it.
- KV is eventually consistent. Two claims racing on one ship can both
  write a name, but only one transfer can succeed.
