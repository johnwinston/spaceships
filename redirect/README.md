# /automons/ → /spaceships/ redirect

The site moved from john-winston.com/automons/ to john-winston.com/spaceships/
(2026-10-18). Cards plotted before then carry QR codes to /automons/, so the old
address must keep working.

At publish time, after `gh repo rename spaceships` on johnwinston/automons:

1. Create a new public repo **johnwinston/automons** containing only
   `index.html` and `404.html` from this folder.
2. Turn on GitHub Pages for it (Settings → Pages → Deploy from branch → main, /).
   The account's custom domain makes it john-winston.com/automons/.

`index.html` handles the root (`/automons/#v=1&a=p4-01…`); `404.html` handles
any deeper path (`/automons/nft/p4-01.json`, `/automons/play.html#…`). Both
rewrite `/automons` to `/spaceships` and keep the query and `#fragment`, which
carry the ship and, from the claim booklet, its claim code.

Wallets and NFT indexers don't run JavaScript, so this does not cover the
on-chain metadata; `chain/src/repoint.mjs` rewrites those uris instead.
