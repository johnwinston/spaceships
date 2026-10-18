/* The collection page: every ship in the deck, as its photographed card,
 * by rarity, with its claim. */
(function () {
  "use strict";
  var TIER_ORDER = ["legendary", "rare", "uncommon", "common"];

  function shipHref(id) {
    return "ship.html#v=1&a=" + encodeURIComponent(id);
  }

  function claimLine(claim) {
    var el = document.createElement("div");
    if (claim) {
      el.className = "claim";
      el.textContent = (claim.name ? "claimed · " + claim.name : "claimed") +
        (claim.wallet ? " · NFT in wallet" : "");
    } else {
      el.className = "claim unclaimed";
      el.textContent = "unclaimed";
    }
    return el;
  }

  function card(id, e, deckSize, claim) {
    var a = document.createElement("a");
    a.className = "card" + (claim ? " is-claimed" : "");
    a.href = shipHref(id);
    var img = document.createElement("img");
    img.src = "img/t/" + encodeURIComponent(id) + ".jpg";   // the plotted card, photographed
    img.alt = "Pen-plotted card #" + e.edition + ", ship " + id;
    img.loading = "lazy";
    a.appendChild(img);
    var rule = document.createElement("div");
    rule.className = "code";
    rule.textContent = e.rule;
    a.appendChild(rule);
    var meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = "#" + e.edition + " of " + deckSize + " · period-" + e.period;
    a.appendChild(meta);
    a.appendChild(claimLine(claim));
    return a;
  }

  function render(catalog, claims) {
    var deck = Object.keys(catalog).filter(function (id) {
      return Number(catalog[id].edition) > 0;   // demo entries aren't cards
    });
    var byTier = {};
    deck.forEach(function (id) {
      var tier = catalog[id].rarity || "common";
      (byTier[tier] = byTier[tier] || []).push(id);
    });
    var main = document.getElementById("tiers");
    main.textContent = "";
    TIER_ORDER.forEach(function (tier) {
      var ids = byTier[tier];
      if (!ids) return;
      ids.sort(function (a, b) {
        return Number(catalog[a].edition) - Number(catalog[b].edition);
      });
      var h2 = document.createElement("h2");
      h2.textContent = tier;
      main.appendChild(h2);
      var grid = document.createElement("div");
      grid.className = "grid";
      ids.forEach(function (id) {
        grid.appendChild(card(id, catalog[id], deck.length, claims[id]));
      });
      main.appendChild(grid);
    });
    return deck.length;
  }

  async function init() {
    var status = document.getElementById("status");
    var catalog;
    try {
      var res = await fetch("catalog.json", { cache: "no-cache" });
      catalog = await res.json();
    } catch (err) {
      status.textContent = "could not load catalog: " + err;
      return;
    }
    var claims = {};
    render(catalog, claims);
    status.textContent = "";
    try {
      claims = await window.Spaceships.claims.list();
      render(catalog, claims);
    } catch (err) {
      status.textContent = "claims are unavailable right now";
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
