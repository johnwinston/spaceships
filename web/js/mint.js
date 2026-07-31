/* Solana mint integration — scaffolding only.
 *
 * The mint flow (see chain/README.md for the full plan):
 *   1. User scans the card's QR -> lands here with #a=<apgcode>&c=<claim>.
 *   2. "Connect wallet" via Solana wallet-adapter (Phantom/Solflare/etc.).
 *   3. POST {apgcode, claim, wallet} to the claim endpoint; the endpoint
 *      verifies the claim token (HMAC, single-use) and either mints a
 *      Metaplex Core asset to the wallet or transfers the pre-minted one.
 *   4. Show the transaction signature / explorer link.
 *
 * Nothing on this page holds a private key; the claim service signs.
 */
(function () {
  "use strict";

  // Set these when the chain side is deployed.
  var CLAIM_ENDPOINT = null; // e.g. "https://automons.example.com/api/claim"
  var CLUSTER = "devnet";    // switch to "mainnet-beta" for launch

  function mintAvailable() {
    return Boolean(CLAIM_ENDPOINT);
  }

  async function mintShip(ship) {
    if (!mintAvailable()) {
      return {
        ok: false,
        message:
          "Minting isn't wired up yet — the claim service hasn't been " +
          "deployed. See chain/README.md in the automons repo for the plan.",
      };
    }
    if (!ship.claim) {
      return {
        ok: false,
        message:
          "This link has no claim token. Scan the QR on a physical card " +
          "to mint its NFT.",
      };
    }
    // TODO: wallet-adapter connect, then:
    // const res = await fetch(CLAIM_ENDPOINT, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     apgcode: ship.apgcode,
    //     claim: ship.claim,
    //     wallet: walletPublicKey.toBase58(),
    //     cluster: CLUSTER,
    //   }),
    // });
    return { ok: false, message: "Mint flow not implemented yet." };
  }

  window.Automons = window.Automons || {};
  window.Automons.mint = { mintShip: mintShip, mintAvailable: mintAvailable };
})();
