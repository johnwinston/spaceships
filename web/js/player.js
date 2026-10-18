/* Player UI: canvas rendering, run controls, drawing. */
(function () {
  "use strict";

  var E = window.Spaceships.engine;
  var GRID = 72;            // toroidal world size
  var world = null;
  var ship = null;
  var initialCells = [];
  var running = false;
  var timer = null;
  var speedMs = 100;   // replaced from the slider at init
  var cellPx = 12;

  var canvas, ctx;

  function $(id) { return document.getElementById(id); }

  var SLOWEST_MS = 600;
  var FASTEST_MS = 16;

  function speedFromSlider(pos) {
    var t = Math.min(1, Math.max(0, pos / 100));
    return Math.round(SLOWEST_MS * Math.pow(FASTEST_MS / SLOWEST_MS, t));
  }

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
    var w = 0, h = 0;
    initialCells.forEach(function (c) {
      if (c[0] + 1 > w) w = c[0] + 1;
      if (c[1] + 1 > h) h = c[1] + 1;
    });
    world.placeCells(initialCells,
                     Math.floor((GRID - w) / 2),
                     Math.floor((GRID - h) / 2));
    draw();
    updateCounters();
  }

  function drawGrid(w, h) {
    // Graph paper: a hairline per cell, a brighter one every ten, so a
    // pattern can be read off and counted rather than just watched.
    var i, px;
    ctx.lineWidth = 1;
    for (var pass = 0; pass < 2; pass++) {
      var every = pass === 0 ? 1 : 10;
      ctx.strokeStyle = pass === 0 ? "#242424" : "#3d3d3d";
      ctx.beginPath();
      for (i = 0; i <= w; i++) {
        if (i % every) continue;
        if (pass === 0 && i % 10 === 0) continue;
        px = i * cellPx + 0.5;
        ctx.moveTo(px, 0);
        ctx.lineTo(px, h * cellPx);
      }
      for (i = 0; i <= h; i++) {
        if (i % every) continue;
        if (pass === 0 && i % 10 === 0) continue;
        px = i * cellPx + 0.5;
        ctx.moveTo(0, px);
        ctx.lineTo(w * cellPx, px);
      }
      ctx.stroke();
    }
  }

  function draw() {
    var w = world.width, h = world.height;
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGrid(w, h);
    ctx.fillStyle = "#ffffff";
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        if (world.get(x, y)) {
          // inset by one so the grid line stays visible between cells
          ctx.fillRect(x * cellPx + 1, y * cellPx + 1, cellPx - 1, cellPx - 1);
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


  function cellAt(ev) {
    var rect = canvas.getBoundingClientRect();
    return [
      Math.floor((ev.clientX - rect.left) / rect.width * world.width),
      Math.floor((ev.clientY - rect.top) / rect.height * world.height),
    ];
  }

  function inBounds(x, y) {
    return x >= 0 && y >= 0 && x < world.width && y < world.height;
  }

  function wireDrawing() {
    // Drag to draw. The first cell decides whether the stroke paints or
    // erases, so dragging back over your own line rubs it out.
    var painting = false, value = 1, lastX = 0, lastY = 0;

    function paint(x, y) {
      if (inBounds(x, y)) world.set(x, y, value);
    }

    function paintLine(x0, y0, x1, y1) {
      // Pointer events skip cells on a fast drag; walk the gap.
      var steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0));
      if (!steps) { paint(x1, y1); return; }
      for (var i = 0; i <= steps; i++) {
        paint(Math.round(x0 + (x1 - x0) * i / steps),
              Math.round(y0 + (y1 - y0) * i / steps));
      }
    }

    canvas.addEventListener("pointerdown", function (ev) {
      var c = cellAt(ev);
      if (!inBounds(c[0], c[1])) return;
      ev.preventDefault();
      canvas.setPointerCapture(ev.pointerId);
      painting = true;
      value = world.get(c[0], c[1]) ? 0 : 1;
      lastX = c[0]; lastY = c[1];
      paint(c[0], c[1]);
      draw();
      updateCounters();
    });

    canvas.addEventListener("pointermove", function (ev) {
      if (!painting) return;
      var c = cellAt(ev);
      if (c[0] === lastX && c[1] === lastY) return;
      paintLine(lastX, lastY, c[0], c[1]);
      lastX = c[0]; lastY = c[1];
      draw();
      updateCounters();
    });

    function stop(ev) {
      if (!painting) return;
      painting = false;
      if (canvas.hasPointerCapture(ev.pointerId)) {
        canvas.releasePointerCapture(ev.pointerId);
      }
    }
    canvas.addEventListener("pointerup", stop);
    canvas.addEventListener("pointercancel", stop);
  }

  function wireControls() {
    $("playpause").onclick = function () { setRunning(!running); };
    $("stepbtn").onclick = function () { setRunning(false); tick(); };
    $("resetbtn").onclick = function () { setRunning(false); resetWorld(); };
    $("speed").oninput = function () {
      speedMs = speedFromSlider(parseInt(this.value, 10));
      if (running) setRunning(true);
    };
    wireDrawing();
  }

  function deckSize(catalog) {
    // Deck ships carry an edition number; demo entries (edition 0) don't.
    return Object.keys(catalog).filter(function (k) {
      return Number(catalog[k].edition) > 0;
    }).length;
  }

  async function loadCatalog() {
    try {
      var res = await fetch("catalog.json", { cache: "no-cache" });
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

    var payload = window.Spaceships.shipurl.decodeHash(location.hash);
    var catalog = await loadCatalog();
    // No payload at all -> demo ship (first catalog entry, or a glider).
    if (!payload.apgcode && !payload.rleText) {
      var first = Object.keys(catalog)[0];
      if (first) payload.apgcode = first;
    }
    ship = window.Spaceships.shipurl.resolveShip(payload, catalog);
    if (!ship.rleText) {
      ship.rleText = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!";
      ship.rule = "b3s23";
    }

    var table = buildTable(ship);
    if (!table) {
      status(
        "This link doesn't carry a transition table and the rule '" +
        ship.rule + "' isn't totalistic — regenerate the link with " +
        "src/build_deck.py.", true);
      return;
    }

    var parsed = window.Spaceships.rle.parse(ship.rleText);
    initialCells = parsed.cells;

    world = new E.World(GRID, GRID, table);
    // The catalog id (p4-01) is a filing code, not a name -- the rule is
    // what actually identifies a ship, so it carries the header.
    $("shipname").textContent = ship.edition
      ? ("#" + ship.edition + " of " + deckSize(catalog)) : "";
    $("shiprule").textContent = ship.rule;
    $("shipmeta").textContent = [
      ship.rarity, ship.period && ("period-" + ship.period),
    ].filter(Boolean).join(" · ");
    speedMs = speedFromSlider(parseInt($("speed").value, 10));
    wireControls();
    resetWorld();
    setRunning(false); // frozen on generation 0 until the visitor presses Play
    status("Drag on the grid to draw or erase. This ship is yours to fly.");
    // A `c=` in the link (a QR that carries the code) pre-fills the form.
    window.Spaceships.claimUI.init(ship, payload.claim);
  }

  window.addEventListener("hashchange", function () { location.reload(); });
  document.addEventListener("DOMContentLoaded", init);
})();
