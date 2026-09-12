# Claim service

One Cloudflare Worker plus one KV namespace. A buyer opens the player
from the QR on their card, types the claim code plotted under the QR,
and the collection page shows the ship as claimed (with their name, if
they give one).

Codes are never stored: both the card backs (`src/claimcode.py`) and this
Worker (`src/claimcode.js`) derive them as HMAC-SHA256 of the ship id
under one shared secret, so nothing in KV can be used to forge one.

## API

| Method | Path | Body | Result |
|---|---|---|---|
| GET | `/claims` | | `{ claims: { "p4-01": { name, claimedAt }, … } }` |
| GET | `/claims/<ship>` | | `{ claim }` or 404 |
| POST | `/claim` | `{ ship, code, name? }` | 200 `{ ok, updated, claim }`, 403 wrong code, 400 malformed, 429 too many tries |
| POST | `/admin/unclaim` | `{ ship }` + `Authorization: Bearer <ADMIN_TOKEN>` | 200 |

A valid code on an already-claimed ship updates the name, so a typo at
the booth is fixable by whoever holds the card. Writes are rate limited
per IP (12 per minute). CORS is open only to `ALLOWED_ORIGINS`.

## Deploy (first time)

```bash
cd worker
npm install                                   # wrangler (or use the global one)

# 1. one secret, shared with the plotting side
python -m src.claimcode --new-secret          # run from the repo root; keep it safe
npx wrangler secret put CLAIM_SECRET          # paste it
npx wrangler secret put ADMIN_TOKEN           # anything long and random

# 2. storage
npx wrangler kv namespace create CLAIMS       # paste the id into wrangler.jsonc

# 3. ship it
npx wrangler deploy                           # prints https://spaceships-claims.<acct>.workers.dev
```

Then set `CLAIM_ENDPOINT` in `web/js/config.js` to that URL and push
`web/` (GitHub Pages picks it up). Export the same secret as
`AUTOMONS_CLAIM_SECRET` before running `build_deck` / `impose`, or the
stickers and backs come out without codes.

## Run locally

```bash
cp .dev.vars.example .dev.vars               # CLAIM_SECRET=test-secret
npx wrangler dev                              # http://localhost:8787, local KV
curl -s localhost:8787/claims
curl -s -X POST localhost:8787/claim -H 'content-type: application/json' \
     -d '{"ship":"p4-01","code":"GQE2-Q3K7","name":"Ana"}'
```

`GQE2-Q3K7` is p4-01's code under the `test-secret` secret -- the shared
test vector in `test/claimcode.test.js` and `tests/test_claimcode.py`.

## Tests

```bash
node --test          # pure Node: claim codes + the fetch handler against a fake KV
```

## Booth day

- `AUTOMONS_CLAIM_SECRET=… python -m src.claimcode --deck data/deck.json`
  prints every ship's code -- the private sheet for the table.
- Undo a mistaken claim: `curl -X POST …/admin/unclaim -H 'Authorization: Bearer …' -d '{"ship":"p4-01"}'`.
- Watch it live: `npx wrangler tail`.

Known limits: KV is eventually consistent, so two people claiming the
same ship within about a minute could both see success (only the last
write sticks). At n≈100 cards sold in person that is not worth a
Durable Object.
