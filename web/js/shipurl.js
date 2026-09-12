/* URL-fragment payload decoder. Mirror of src/shipurl.py — keep in sync.
 *
 *   #v=1&a=<apgcode>&r=<rule>              -> look ship up in catalog.json
 *   #v=1&r=<rule>&p=<b64url rle>&t=<hex>   -> fully self-contained
 */
(function () {
  "use strict";

  function b64urlDecode(data) {
    var b64 = data.replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    return decodeURIComponent(
      atob(b64).split("").map(function (c) {
        return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
      }).join("")
    );
  }

  // Returns {version, apgcode, rule, rleText, tableHex, name, claim}
  // (`apgcode` is the `a=` catalog key -- a deck id like p4-01 these days)
  function decodeHash(hash) {
    var out = {};
    var params = new URLSearchParams((hash || "").replace(/^#/, ""));
    if (params.get("v")) out.version = params.get("v");
    if (params.get("a")) out.apgcode = params.get("a");
    if (params.get("r")) out.rule = params.get("r");
    if (params.get("t")) out.tableHex = params.get("t");
    if (params.get("n")) out.name = params.get("n");
    if (params.get("c")) out.claim = params.get("c");
    if (params.get("p")) {
      try {
        out.rleText = b64urlDecode(params.get("p"));
      } catch (e) {
        console.error("bad p parameter", e);
      }
    }
    return out;
  }

  // Merge URL payload with a catalog entry (URL fields win).
  function resolveShip(payload, catalog) {
    var entry = (payload.apgcode && catalog && catalog[payload.apgcode]) || {};
    return {
      id: payload.apgcode || null,       // catalog key (p4-01); `apgcode` is the legacy alias
      apgcode: payload.apgcode || null,
      name: payload.name || entry.name || payload.apgcode || "unnamed ship",
      rule: payload.rule || entry.rule || "b3s23",
      rleText: payload.rleText || entry.rle || null,
      tableHex: payload.tableHex || entry.table || null,
      rarity: entry.rarity || null,
      edition: entry.edition || null,
      period: entry.period || null,
      claim: payload.claim || null,
    };
  }

  window.Spaceships = window.Spaceships || {};
  window.Spaceships.shipurl = { decodeHash: decodeHash, resolveShip: resolveShip };
})();
