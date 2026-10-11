/* The collection page: every ship in the deck, by rarity, with its claim. */
(function () {
  "use strict";
  var TIER_ORDER = ["legendary", "rare", "uncommon", "common"];
  var TIER_BLURB = {
    legendary: "period 7 — rarest of the search",
    rare: "period 6",
    uncommon: "period 5",
    common: "period 4",
  };

  function drawShip(canvas, rleText) {
    var parsed = window.Spaceships.rle.parse(rleText);
    var cells = parsed.cells;
    if (!cells.length) return;
    var maxX = 0, maxY = 0;
    cells.forEach(function (c) {
      if (c[0] > maxX) maxX = c[0];
      if (c[1] > maxY) maxY = c[1];
    });
    var w = maxX + 1, h = maxY + 1;
    // card-shaped canvas grid, ship centred, 1-cell padding minimum
    var cw = 150, ch = 210;
    canvas.width = cw; canvas.height = ch;
    var cell = Math.min(cw / (w + 2), ch / (h + 2));
    var ox = (cw - w * cell) / 2, oy = (ch - h * cell) / 2;
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    cells.forEach(function (c) {
      ctx.fillRect(ox + c[0] * cell + 0.5, oy + c[1] * cell + 0.5,
                   cell - 1, cell - 1);
    });
  }

  function playerHref(id) {
    return "play.html#v=1&a=" + encodeURIComponent(id);
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
    a.href = playerHref(id);
    var canvas = document.createElement("canvas");
    a.appendChild(canvas);
    var rule = document.createElement("div");
    rule.className = "code";
    rule.textContent = e.rule;
    a.appendChild(rule);
    var meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = "#" + e.edition + " of " + deckSize + " · period-" + e.period;
    a.appendChild(meta);
    a.appendChild(claimLine(claim));
    drawShip(canvas, e.rle);
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
      var claimed = ids.filter(function (id) { return claims[id]; }).length;
      var h2 = document.createElement("h2");
      h2.textContent = tier + " ";
      var small = document.createElement("small");
      small.textContent = "· " + ids.length + " · " + (TIER_BLURB[tier] || "") +
        (window.Spaceships.claims.available() ? " · " + claimed + " claimed" : "");
      h2.appendChild(small);
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

  function tally(deckSize, claims) {
    var n = Object.keys(claims).length;
    var el = document.getElementById("tally");
    if (!window.Spaceships.claims.available()) {
      el.textContent = deckSize + " ships. Claims open soon.";
    } else {
      el.textContent = n + " of " + deckSize + " claimed.";
    }
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
    var deckSize = render(catalog, claims);
    status.textContent = "";
    document.getElementById("count").textContent = deckSize;
    try {
      claims = await window.Spaceships.claims.list();
      render(catalog, claims);
    } catch (err) {
      status.textContent = "claims are unavailable right now";
    }
    tally(deckSize, claims);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
