# Solana mint plan

Goal: each physical pen-plotted card carries a QR code. Scanning it opens
the web player for that exact ship, and the card's owner can mint that
ship's NFT to their wallet. ~100 one-of-one NFTs.

## Why this isn't a vanilla candy machine

Candy machines vend a *random* item from a pool. Here every card maps to a
*specific* ship, and only the person physically holding the card should be
able to mint it. That's the "claim" pattern (as used by POAP-style drops):

1. Each card's QR encodes the play URL **plus a single-use claim token**
   (`c=` parameter, see `src/shipurl.py`). The token is an HMAC of the
   apgcode under a secret you keep offline, so tokens can't be forged from
   the public catalog.
2. The player page shows **Mint on Solana** (`web/js/mint.js`). The user
   connects a wallet (Phantom/Solflare via wallet-adapter).
3. The page POSTs `{apgcode, claim, wallet}` to a tiny claim service. The
   service verifies the HMAC, checks the apgcode hasn't been claimed yet,
   then mints (or transfers) the asset to the user's wallet and records
   the claim.

The claim service is the only piece that holds a key. A single serverless
function (Vercel/Cloudflare) with a funded keypair is enough for 100 mints.

## Recommended stack (2026)

- **Metaplex Core** (`mpl-core`) assets, one per ship — the cheapest full
  NFT primitive on Solana (~0.003–0.004 SOL rent each; the whole set of
  100 costs well under 1 SOL to mint, plus ~0.02 SOL of tx fees).
  Compressed NFTs (Bubblegum) are cheaper still but add Merkle-tree
  infrastructure that isn't worth it at n=100.
- **Umi + JS SDK** (`@metaplex-foundation/umi`,
  `@metaplex-foundation/mpl-core`) in the claim service.
- **Irys (Arweave)** for permanent storage of the gif + metadata JSON
  produced by `python -m src.nft_metadata` — a few cents per file.
- A **Core Collection** asset so all 100 ships group under one verified
  collection in wallets and marketplaces.

## Build order

1. **Metadata** — run the pipeline, then `python -m src.nft_metadata
   --periods ...`. Upload gifs, re-run with `--image-base`, upload JSONs.
2. **Devnet dry run** — script `createCollection` + `create` (mint one
   Core asset per metadata URI) against devnet. Verify how wallets render
   the gif + `animation_url` (the player link).
3. **Claim service** — one endpoint:
   `POST /api/claim {apgcode, claim, wallet}`.
   Storage can be a single JSON/KV of `apgcode -> {claimed, tx}`.
   Secrets: `CLAIM_HMAC_KEY`, `MINT_AUTHORITY_KEYPAIR`, RPC URL
   (Helius/Triton free tier is fine at this scale).
4. **Wire the player** — set `CLAIM_ENDPOINT` in `web/js/mint.js`, add
   wallet-adapter, test the full scan → play → mint loop on devnet.
5. **Mainnet** — rotate keys, re-upload nothing (Arweave is permanent),
   flip cluster, mint the collection, generate production QR codes with
   claim tokens, plot the cards.

## Decisions to make

- **Mint-on-claim vs pre-mint + transfer.** Mint-on-claim (recommended):
  nothing exists until a card is scanned, unclaimed ships cost nothing.
  Pre-mint looks better on marketplaces before the drop but you pay rent
  up front and the transfer flow is slightly more code.
- **Price.** Free claim (card price covers it) is simplest — the claim
  service pays fees. Charging in SOL means the service builds a
  transaction the user signs-and-pays; slightly more code.
- **Claim token placement.** In the same QR = anyone who sees a good photo
  of the card back can mint. Common mitigations: scratch-off sticker over
  the QR, or a second private QR inside the packaging.
