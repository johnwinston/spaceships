/* Table-driven cellular-automaton engine.
 *
 * Mirror of src/ruletable.py + src/engine.py — keep in sync.
 *
 * The transition table has 512 entries indexed by
 *   index = center*256 + sum(neighbour_i << i)
 * with neighbours ordered clockwise from north:
 *   i:  0  1   2  3   4  5   6  7
 *       N  NE  E  SE  S  SW  W  NW
 *
 * Tables arrive either as 128 hex chars (from the Python pipeline, which
 * uses lifelib as the oracle for isotropic non-totalistic rules) or are
 * built locally for outer-totalistic rules like b3s23.
 */
(function () {
  "use strict";

  // (dx, dy), y increases downward. Same order as src/ruletable.py.
  var NEIGH = [
    [0, -1], [1, -1], [1, 0], [1, 1],
    [0, 1], [-1, 1], [-1, 0], [-1, -1],
  ];

  function tableFromHex(hex) {
    if (!hex || hex.length !== 128) return null;
    var table = new Uint8Array(512);
    for (var j = 0; j < 128; j++) {
      var nibble = parseInt(hex[j], 16);
      if (isNaN(nibble)) return null;
      for (var k = 0; k < 4; k++) {
        table[j * 4 + k] = (nibble >> k) & 1;
      }
    }
    return table;
  }

  // "b3s23", "B3/S23", "b36s23" -> table; null if the rule has INT letters.
  function totalisticTable(rule) {
    var m = /^b(\d*)s(\d*)$/.exec(rule.toLowerCase().replace(/\//g, ""));
    if (!m) return null;
    var birth = {}, survive = {};
    m[1].split("").forEach(function (d) { birth[+d] = true; });
    m[2].split("").forEach(function (d) { survive[+d] = true; });
    var table = new Uint8Array(512);
    for (var idx = 0; idx < 512; idx++) {
      var center = idx >> 8;
      var n = 0;
      for (var i = 0; i < 8; i++) n += (idx >> i) & 1;
      table[idx] = (center === 0 ? birth[n] : survive[n]) ? 1 : 0;
    }
    return table;
  }

  // Toroidal grid world.
  function World(width, height, table) {
    this.width = width;
    this.height = height;
    this.table = table;
    this.grid = new Uint8Array(width * height);
    this.generation = 0;
  }

  World.prototype.get = function (x, y) {
    return this.grid[y * this.width + x];
  };

  World.prototype.set = function (x, y, v) {
    this.grid[y * this.width + x] = v ? 1 : 0;
  };

  World.prototype.toggle = function (x, y) {
    var i = y * this.width + x;
    this.grid[i] = this.grid[i] ? 0 : 1;
  };

  World.prototype.clear = function () {
    this.grid.fill(0);
    this.generation = 0;
  };

  World.prototype.population = function () {
    var p = 0;
    for (var i = 0; i < this.grid.length; i++) p += this.grid[i];
    return p;
  };

  World.prototype.placeCells = function (cells, offsetX, offsetY) {
    for (var i = 0; i < cells.length; i++) {
      var x = (cells[i][0] + offsetX + this.width) % this.width;
      var y = (cells[i][1] + offsetY + this.height) % this.height;
      this.set(x, y, 1);
    }
  };

  World.prototype.step = function () {
    var w = this.width, h = this.height;
    var src = this.grid, table = this.table;
    var dst = new Uint8Array(w * h);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var idx = src[y * w + x] ? 256 : 0;
        for (var i = 0; i < 8; i++) {
          var nx = (x + NEIGH[i][0] + w) % w;
          var ny = (y + NEIGH[i][1] + h) % h;
          if (src[ny * w + nx]) idx |= 1 << i;
        }
        dst[y * w + x] = table[idx];
      }
    }
    this.grid = dst;
    this.generation++;
  };

  window.Spaceships = window.Spaceships || {};
  window.Spaceships.engine = {
    NEIGH: NEIGH,
    tableFromHex: tableFromHex,
    totalisticTable: totalisticTable,
    World: World,
  };
})();
