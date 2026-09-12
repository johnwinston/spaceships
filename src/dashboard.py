"""Self-contained HTML review dashboard for searched ships.

`cleanup.py` curates one ship at a time through a tkinter keep/delete
prompt, which is fine for a handful and painful for a few hundred.  This
renders the whole pool as one page: every ship drawn to scale, sortable,
filterable, with keep/cut state you can toggle and copy back out.

Generation 0 needs no rule table -- the .lif file is the pattern -- so the
default run is instant and dependency-free.  `--animate` additionally
steps each ship through its period with lifelib, which costs a one-time
~20s shared-object compile per distinct rule.

Usage:
    python -m src.dashboard --periods 4 5 6 7
    python -m src.dashboard --periods 4 --animate
    python -m src.dashboard --periods 4 6 --fragment -o review.html
"""
import argparse
import json
import os
import re

from . import config
from . import lif2rle

RARITY_BY_PERIOD = {"4": "common", "5": "uncommon", "6": "rare", "7": "legendary"}

_SEARCH_RE = re.compile(
    r"^#Search w(\d+) p(\d+) k(\d+) ([avug]) m(\d+)", re.M
)
_FIT_RE = re.compile(
    r"^#Fit (\d+)x(\d+) cells, ([\d.]+)mm cell, (\d+)% of box", re.M
)

SYMMETRY_NAMES = {"v": "even", "u": "odd", "g": "gutter", "a": "asym"}


def parse_meta(text):
    """Pull the search/fit annotations auto_ntzfind wrote into a .lif."""
    meta = {}
    found = _SEARCH_RE.search(text)
    if found:
        meta.update(
            search_width=int(found.group(1)),
            offset=int(found.group(3)),
            symmetry=found.group(4),
            max_length=int(found.group(5)),
        )
    fit = _FIT_RE.search(text)
    if fit:
        meta.update(
            width=int(fit.group(1)),
            height=int(fit.group(2)),
            cell_mm=float(fit.group(3)),
            fill=int(fit.group(4)),
        )
    return meta


def load_ships(periods, base=None):
    """Read every .lif for the given periods into review records."""
    base = base or config.PIPELINE_BASE
    ships = []
    for period in periods:
        folder = os.path.join(base, "ntzfind_patterns", str(period))
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder), key=_natural_key):
            if not name.endswith(".lif"):
                continue
            path = os.path.join(folder, name)
            text = open(path).read()
            try:
                cells, rule = lif2rle.parse_life105(text)
            except ValueError:
                continue
            meta = parse_meta(text)
            ships.append(dict(
                meta,
                id="p%s-%s" % (period, name[:-4]),
                file="%s/%s" % (period, name),
                period=int(period),
                rule=rule or "unknown",
                cells=cells,
                population=len(cells),
                rarity=RARITY_BY_PERIOD.get(str(period), "legendary"),
            ))
    return ships


def _natural_key(name):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]


def add_phases(ships, lifelib):
    """Step each ship through its period so the page can animate it."""
    from . import engine, ruletable

    tables = {}
    for index, ship in enumerate(ships, 1):
        rule = ship["rule"]
        if rule not in tables:
            print("  [%d/%d] table for %s" % (index, len(ships), rule))
            tables[rule] = ruletable.table_for_rule(rule, lifelib)
        gens = list(engine.run(ship["cells"], tables[rule], ship["period"]))
        ship["phases"] = [_normalise(g) for g in gens[:ship["period"]]]
    return ships


def _normalise(cells):
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    return sorted((x - min_x, y - min_y) for x, y in cells)


def cells_path(cells):
    """One SVG path drawing every live cell as a unit square."""
    return "".join("M%d %dh1v1h-1z" % (x, y) for x, y in sorted(cells))


def ship_payload(ship):
    """The JSON record the page needs; cells become path strings."""
    frames = ship.get("phases") or [ship["cells"]]
    paths = [cells_path(f) for f in frames]
    width = ship.get("width") or max(x for x, _ in ship["cells"]) + 1
    height = ship.get("height") or max(y for _, y in ship["cells"]) + 1
    return {
        "id": ship["id"],
        "file": ship["file"],
        "period": ship["period"],
        "rule": ship["rule"],
        "rarity": ship["rarity"],
        "pop": ship["population"],
        "w": width,
        "h": height,
        "fill": ship.get("fill", 0),
        "cell": ship.get("cell_mm", 0.0),
        "sym": SYMMETRY_NAMES.get(ship.get("symmetry", ""), "?"),
        "k": ship.get("offset", 0),
        "paths": paths,
    }


STYLE = """
:root{--paper:#f7f8f6;--panel:#fdfdfc;--ink:#16181c;--dim:#71766f;
--line:#d9dcd6;--hair:#e8eae5;--keep:#2b5fa8;--cut:#b83a2e;--grid:#eceee9}
@media (prefers-color-scheme:dark){:root{--paper:#141613;--panel:#1c1f1b;
--ink:#e6e8e3;--dim:#8b9188;--line:#32362f;--hair:#26291f;--keep:#7fa3e0;
--cut:#e0796c;--grid:#232620}}
:root[data-theme=dark]{--paper:#141613;--panel:#1c1f1b;--ink:#e6e8e3;
--dim:#8b9188;--line:#32362f;--hair:#26291f;--keep:#7fa3e0;--cut:#e0796c;
--grid:#232620}
:root[data-theme=light]{--paper:#f7f8f6;--panel:#fdfdfc;--ink:#16181c;
--dim:#71766f;--line:#d9dcd6;--hair:#e8eae5;--keep:#2b5fa8;--cut:#b83a2e;
--grid:#eceee9}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:400 14px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;
font-variant-numeric:tabular-nums}
.wrap{max-width:1240px;margin:0 auto;padding:28px 18px 72px}
h1{font:500 19px/1.3 system-ui,sans-serif;margin:0 0 3px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:12.5px;margin:0 0 22px;max-width:62ch}
.tiers{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));
gap:1px;background:var(--line);border:1px solid var(--line);
border-radius:8px;overflow:hidden;margin-bottom:20px}
.tier{background:var(--panel);padding:10px 12px;display:flex;
flex-direction:column;gap:6px}
.tier b{font:500 11px/1 system-ui,sans-serif;text-transform:uppercase;
letter-spacing:.09em;color:var(--dim)}
.tier .n{font-size:19px;line-height:1}
.tier .n s{text-decoration:none;color:var(--dim);font-size:12px}
.meter{height:3px;background:var(--grid);border-radius:2px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--keep)}
.bar{display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:11px 0;
border-block:1px solid var(--line);margin-bottom:18px;position:sticky;top:0;
background:var(--paper);z-index:5}
select,button{font:inherit;font-size:12px;padding:5px 9px;color:var(--ink);
background:var(--panel);border:1px solid var(--line);border-radius:5px;
cursor:pointer}
select:hover,button:hover{border-color:var(--dim)}
:focus-visible{outline:2px solid var(--keep);outline-offset:1px}
.count{margin-left:auto;color:var(--dim);font-size:12px}
.grid{display:grid;gap:12px;
grid-template-columns:repeat(auto-fill,minmax(172px,1fr))}
.card{border:1px solid var(--line);border-radius:9px;background:var(--panel);
padding:9px;display:flex;flex-direction:column;gap:7px}
.card.cut{opacity:.3}
.card.keep{border-color:var(--keep);box-shadow:inset 0 0 0 1px var(--keep)}
.art{aspect-ratio:63.5/88.9;display:flex;align-items:center;
justify-content:center;background:var(--paper);border:1px solid var(--hair);
border-radius:3px;padding:11%}
.art svg{max-width:100%;max-height:100%;display:block}
.art path{fill:var(--ink)}
.fill{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim)}
.fill .meter{flex:1}
.meta{font-size:10.5px;color:var(--dim);line-height:1.5}
.meta b{color:var(--ink);font-weight:400}
.rule{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
overflow:hidden;word-break:break-all;margin-top:3px;opacity:.72}
.tags{display:flex;flex-wrap:wrap;gap:4px;font-size:10px}
.tag{padding:1px 5px;border:1px solid var(--line);border-radius:3px;
color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.acts{display:flex;gap:5px}
.acts button{flex:1;padding:4px;font-size:11px}
.acts .keepbtn.on{background:var(--keep);border-color:var(--keep);color:#fff}
.acts .cutbtn.on{background:var(--cut);border-color:var(--cut);color:#fff}
.out{margin-top:22px}
.out label{font:500 11px/1 system-ui,sans-serif;text-transform:uppercase;
letter-spacing:.09em;color:var(--dim)}
textarea{width:100%;height:140px;margin-top:7px;font:inherit;font-size:11.5px;
background:var(--panel);color:var(--ink);border:1px solid var(--line);
border-radius:7px;padding:10px;resize:vertical}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

SCRIPT = """
const cards=new Map();let state={};
try{state=JSON.parse(localStorage.getItem('automons-review')||'{}')}catch(e){}
const save=()=>localStorage.setItem('automons-review',JSON.stringify(state));
function svgFor(s){const p=s.paths.map((d,i)=>
`<path d="${d}"${i?' style="display:none"':''}/>`).join('');
return `<svg viewBox="0 0 ${s.w} ${s.h}" preserveAspectRatio="xMidYMid meet">${p}</svg>`}
function build(s){
 const el=document.createElement('div');el.className='card';el.dataset.id=s.id;
 el.innerHTML=`<div class="art">${svgFor(s)}</div>
 <div class="fill"><span class="meter"><i style="width:${s.fill}%"></i></span>
 ${s.fill}%</div>
 <div class="tags"><span class="tag">${s.rarity}</span>
 <span class="tag">${s.k>1?s.k:''}c/${s.period}</span>
 <span class="tag">${s.sym}</span></div>
 <div class="meta"><b>${s.w}\\u00d7${s.h}</b> cells \\u00b7 <b>${s.pop}</b> live
 \\u00b7 ${s.cell.toFixed(2)}mm
 <span class="rule" title="${s.rule}">${s.rule}</span></div>
 <div class="acts"><button class="keepbtn">keep</button>
 <button class="cutbtn">cut</button></div>`;
 const paths=[...el.querySelectorAll('path')];
 if(paths.length>1){let t=null,i=0;
  el.querySelector('.art').addEventListener('mouseenter',()=>{
   t=setInterval(()=>{paths[i].style.display='none';
    i=(i+1)%paths.length;paths[i].style.display=''},170)});
  el.querySelector('.art').addEventListener('mouseleave',()=>{
   clearInterval(t);paths[i].style.display='none';i=0;paths[0].style.display=''});}
 const sync=()=>{const v=state[s.id];
  el.classList.toggle('keep',v==='keep');el.classList.toggle('cut',v==='cut');
  el.querySelector('.keepbtn').classList.toggle('on',v==='keep');
  el.querySelector('.cutbtn').classList.toggle('on',v==='cut')};
 el.querySelector('.keepbtn').onclick=()=>{
  state[s.id]=state[s.id]==='keep'?undefined:'keep';save();sync();tally()};
 el.querySelector('.cutbtn').onclick=()=>{
  state[s.id]=state[s.id]==='cut'?undefined:'cut';save();sync();tally()};
 sync();cards.set(s.id,{el,s});return el}
const TARGETS={common:45,uncommon:30,rare:18,legendary:7};
function tally(){
 const k=SHIPS.filter(s=>state[s.id]==='keep').length;
 const c=SHIPS.filter(s=>state[s.id]==='cut').length;
 document.getElementById('count').textContent=
  `${SHIPS.length} found \\u00b7 ${k} kept \\u00b7 ${c} cut`;
 Object.keys(TARGETS).forEach(t=>{
  const el=document.getElementById('t-'+t);if(!el)return;
  const found=SHIPS.filter(s=>s.rarity===t).length;
  const kept=SHIPS.filter(s=>s.rarity===t&&state[s.id]==='keep').length;
  el.querySelector('.n').innerHTML=
   `${kept}<s>/${TARGETS[t]} kept \\u00b7 ${found} found</s>`;
  el.querySelector('.meter i').style.width=
   Math.min(100,100*kept/TARGETS[t])+'%';});
 const want=document.getElementById('ox').value;
 document.getElementById('out').value=
  SHIPS.filter(s=>state[s.id]===want).map(s=>s.file).join('\\n')}
function render(){
 const g=document.getElementById('grid');g.innerHTML='';
 const per=document.getElementById('fp').value;
 const sym=document.getElementById('fs').value;
 const sort=document.getElementById('so').value;
 let list=SHIPS.filter(s=>(per==='all'||s.period==+per)&&
  (sym==='all'||s.sym===sym));
 const key={fill:s=>-s.fill,pop:s=>-s.pop,w:s=>-s.w,h:s=>-s.h,
  period:s=>s.period};
 list=[...list].sort((a,b)=>key[sort](a)-key[sort](b));
 list.forEach(s=>g.appendChild(cards.get(s.id)?.el||build(s)));
 tally()}
['fp','fs','so'].forEach(id=>
 document.getElementById(id).addEventListener('change',render));
document.getElementById('ox').addEventListener('change',tally);
document.getElementById('clear').onclick=()=>{
 state={};save();cards.forEach(({el,s})=>{el.className='card';
  el.querySelectorAll('button').forEach(b=>b.classList.remove('on'))});tally()};
render();
"""


def render_html(ships, fragment=False, title="Spaceships search review"):
    payload = [ship_payload(s) for s in ships]
    periods = sorted({s["period"] for s in payload})
    animated = any(len(s["paths"]) > 1 for s in payload)
    tiers = "".join(
        '<div class="tier" id="t-%s"><b>%s</b><span class="n"></span>'
        '<span class="meter"><i></i></span></div>' % (t, t)
        for t in ("common", "uncommon", "rare", "legendary")
    )
    body = """<div class="wrap">
<h1>%s</h1>
<p class="sub">Each preview sits in the real card proportion with the 6mm
margin drawn, so what you see is what plots.%s Marks are saved in this
browser; the keep list is copyable at the bottom.</p>
<div class="tiers">%s</div>
<div class="bar">
<select id="fp"><option value="all">all periods</option>%s</select>
<select id="fs"><option value="all">all symmetries</option>%s</select>
<select id="so"><option value="fill">sort: box fill</option>
<option value="pop">sort: population</option>
<option value="w">sort: width</option><option value="h">sort: height</option>
<option value="period">sort: period</option></select>
<button id="clear">reset marks</button>
<span class="count" id="count"></span>
</div>
<div class="grid" id="grid"></div>
<div class="out"><label for="out">export</label>
<select id="ox"><option value="keep">keep list</option>
<option value="cut">cut list</option></select>
<textarea id="out" readonly></textarea></div>
</div>
<script>const SHIPS=%s;</script>
<script>%s</script>""" % (
        title,
        " Hover a ship to fly it." if animated else "",
        tiers,
        "".join('<option value="%d">period %d</option>' % (p, p) for p in periods),
        "".join('<option value="%s">%s</option>' % (n, n)
                for n in sorted({s["sym"] for s in payload})),
        json.dumps(payload, separators=(",", ":")),
        SCRIPT,
    )
    style = "<style>%s</style>" % STYLE
    if fragment:
        return style + body
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>%s</title>%s</head><body>%s</body></html>"
        % (title, style, body)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", required=True)
    parser.add_argument("--animate", action="store_true",
                        help="step each ship through its period (needs lifelib)")
    parser.add_argument("--fragment", action="store_true",
                        help="emit style+body only, no <html> wrapper")
    parser.add_argument("-o", "--out", default="review.html")
    args = parser.parse_args()

    ships = load_ships(args.periods)
    if not ships:
        print("no ships found for periods %s" % " ".join(args.periods))
        return
    if args.animate:
        from submodules import lifelib
        print("building transition tables for %d ships..." % len(ships))
        add_phases(ships, lifelib)

    html = render_html(ships, fragment=args.fragment)
    with open(args.out, "w") as handle:
        handle.write(html)
    print("%d ships -> %s (%.0f KB)" % (
        len(ships), args.out, len(html) / 1024.0
    ))


if __name__ == "__main__":
    main()
