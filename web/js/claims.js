/* Client for the claim service (worker/src/index.js). */
(function () {
  "use strict";

  function endpoint() {
    var cfg = window.Spaceships.config || {};
    return cfg.CLAIM_ENDPOINT ? String(cfg.CLAIM_ENDPOINT).replace(/\/+$/, "") : null;
  }

  function available() { return Boolean(endpoint()); }

  async function list() {
    if (!available()) return {};
    var res = await fetch(endpoint() + "/claims", { cache: "no-cache" });
    if (!res.ok) throw new Error("claim service returned " + res.status);
    return (await res.json()).claims || {};
  }

  async function get(ship) {
    if (!available()) return null;
    var res = await fetch(endpoint() + "/claims/" + encodeURIComponent(ship),
                          { cache: "no-cache" });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("claim service returned " + res.status);
    return (await res.json()).claim || null;
  }

  // Resolves {ok, updated, claim} or {ok: false, message, claim?}; throws only on
  // network failure.
  async function claim(ship, code, name, wallet) {
    var res = await fetch(endpoint() + "/claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ship: ship, code: code, name: name || "", wallet: wallet || "" }),
    });
    var data = {};
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      return { ok: false, message: data.error || ("claim failed (" + res.status + ")"),
               claim: data.claim || null };
    }
    return { ok: true, updated: Boolean(data.updated), claim: data.claim };
  }

  window.Spaceships = window.Spaceships || {};
  // Solana Explorer page for an address on the claim's cluster.
  function explorerUrl(address, cluster) {
    var url = "https://explorer.solana.com/address/" + encodeURIComponent(address);
    return cluster && cluster !== "mainnet-beta" ? url + "?cluster=" + encodeURIComponent(cluster) : url;
  }

  function shortAddress(address) {
    return address.length > 12 ? address.slice(0, 4) + "…" + address.slice(-4) : address;
  }

  window.Spaceships.claims = {
    available: available, list: list, get: get, claim: claim,
    explorerUrl: explorerUrl, shortAddress: shortAddress,
  };
})();
