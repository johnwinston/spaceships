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

  // Resolves {ok, updated, claim} or {ok: false, message}; throws only on
  // network failure.
  async function claim(ship, code, name) {
    var res = await fetch(endpoint() + "/claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ship: ship, code: code, name: name || "" }),
    });
    var data = {};
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      return { ok: false, message: data.error || ("claim failed (" + res.status + ")") };
    }
    return { ok: true, updated: Boolean(data.updated), claim: data.claim };
  }

  window.Spaceships = window.Spaceships || {};
  window.Spaceships.claims = { available: available, list: list, get: get, claim: claim };
})();
