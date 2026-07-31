/* RLE codec. Mirror of src/rle.py — keep in sync. */
(function () {
  "use strict";

  // Returns { cells: [[x,y], ...] normalised to origin, rule: string|null }
  function parse(text) {
    var rule = null;
    var body = [];
    text.split(/\r?\n/).forEach(function (line) {
      line = line.trim();
      if (!line || line[0] === "#") return;
      if (line[0] === "x") {
        var m = /rule\s*=\s*([^,\s]+)/.exec(line);
        if (m) rule = m[1];
        return;
      }
      body.push(line);
    });
    var s = body.join("");

    var cells = [];
    var x = 0, y = 0, count = "";
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      if (ch >= "0" && ch <= "9") { count += ch; continue; }
      var n = count ? parseInt(count, 10) : 1;
      count = "";
      if (ch === "b" || ch === ".") {
        x += n;
      } else if (ch === "$") {
        y += n; x = 0;
      } else if (ch === "!") {
        break;
      } else if (/[a-zA-Z]/.test(ch)) {
        for (var k = 0; k < n; k++) { cells.push([x, y]); x++; }
      }
    }
    if (!cells.length) return { cells: [], rule: rule };
    var minX = Infinity, minY = Infinity;
    cells.forEach(function (c) {
      if (c[0] < minX) minX = c[0];
      if (c[1] < minY) minY = c[1];
    });
    return {
      cells: cells.map(function (c) { return [c[0] - minX, c[1] - minY]; }),
      rule: rule,
    };
  }

  window.Automons = window.Automons || {};
  window.Automons.rle = { parse: parse };
})();
