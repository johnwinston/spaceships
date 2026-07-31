/* Player UI: canvas rendering, run controls, cell editing. */
(function () {
  "use strict";

  var E = window.Automons.engine;
  var GRID = 128;           // toroidal world size
  var world = null;
  var ship = null;
  var initialCells = [];
  var running = false;
  var timer = null;
  var speedMs = 100;
  var cellPx = 6;

  var canvas, ctx;

  function $(id) { return document.getElementById(id); }

  function status(msg, isError) {
    var el = $("status");
    el.textContent = msg;
    el.className = isError ? "error" : "";
  }

  function buildTable(shipInfo) {
    var table = null;
    if (shipInfo.tableHex) table = E.tableFromHex(shipInfo.tableHex);
    if (!table) table = E.totalisticTable(shipInfo.rule);
    return table;
  }

  function resetWorld() {
    world.clear();
    var offX = Math.floor(GRID / 2) - 8;
    var offY = Math.floor(GRID / 2) - 8;
    world.placeCells(initialCells, offX, offY);
    draw();
    updateCounters();
  }

  function draw() {
    var w = world.width, h = world.height;
    ctx.fillStyle = "#0b0f14";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffd75e";
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        if (world.get(x, y)) {
          ctx.fillRect(x * cellPx, y * cellPx, cellPx - 1, cellPx - 1);
        }
      }
    }
  }

  function updateCounters() {
    $("generation").textContent = world.generation;
    $("population").textContent = world.population();
  }

  function tick() {
    world.step();
    draw();
    updateCounters();
  }

  function setRunning(on) {
    running = on;
    $("playpause").textContent = on ? "Pause" : "Play";
    if (timer) { clearInterval(timer); timer = null; }
    if (on) timer = setInterval(tick, speedMs);
  }

  function wireControls() {
    $("playpause").onclick = function () { setRunning(!running); };
    $("stepbtn").onclick = function () { setRunning(false); tick(); };
    $("resetbtn").onclick = function () { setRunning(false); resetWorld(); };
    $("clearbtn").onclick = function () {
      setRunning(false);
      world.clear();
      draw();
      updateCounters();
    };
    $("speed").oninput = function () {
      speedMs = 510 - parseInt(this.value, 10);
      if (running) setRunning(true);
    };
    canvas.onclick = function (ev) {
      var rect = canvas.getBoundingClientRect();
      var x = Math.floor((ev.clientX - rect.left) / rect.width * world.width);
      var y = Math.floor((ev.clientY - rect.top) / rect.height * world.height);
      if (x >= 0 && y >= 0 && x < world.width && y < world.height) {
        world.toggle(x, y);
        draw();
        updateCounters();
      }
    };
    $("mintbtn").onclick = async function () {
      var result = await window.Automons.mint.mintShip(ship);
      status(result.message, !result.ok);
    };
  }

  async function loadCatalog() {
    try {
      var res = await fetch("catalog.json");
      if (res.ok) return await res.json();
    } catch (e) {
      // file:// or offline — self-contained links still work
    }
    return {};
  }

  async function init() {
    canvas = $("board");
    ctx = canvas.getContext("2d");
    canvas.width = GRID * cellPx;
    canvas.height = GRID * cellPx;

    var payload = window.Automons.shipurl.decodeHash(location.hash);
    var catalog = await loadCatalog();
    // No payload at all -> demo ship (first catalog entry, or a glider).
    if (!payload.apgcode && !payload.rleText) {
      var first = Object.keys(catalog)[0];
      if (first) payload.apgcode = first;
    }
    ship = window.Automons.shipurl.resolveShip(payload, catalog);
    if (!ship.rleText) {
      ship.rleText = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!";
      ship.rule = "b3s23";
      ship.name = ship.name === "unnamed ship" ? "golden glider" : ship.name;
    }

    var table = buildTable(ship);
    if (!table) {
      status(
        "This link doesn't carry a transition table and the rule '" +
        ship.rule + "' isn't totalistic — regenerate the link with " +
        "src/build_catalog.py.", true);
      return;
    }

    var parsed = window.Automons.rle.parse(ship.rleText);
    initialCells = parsed.cells;

    world = new E.World(GRID, GRID, table);
    $("shipname").textContent = ship.name;
    $("shiprule").textContent = ship.rule;
    $("shipmeta").textContent = [
      ship.apgcode, ship.rarity, ship.period && ("period-" + ship.period),
    ].filter(Boolean).join(" · ");
    if (!window.Automons.mint.mintAvailable()) {
      $("mintbtn").classList.add("disabled");
    }

    wireControls();
    resetWorld();
    setRunning(true);
    status("Click cells to edit while paused. This ship is yours to fly.");
  }

  window.addEventListener("hashchange", function () { location.reload(); });
  document.addEventListener("DOMContentLoaded", init);
})();
