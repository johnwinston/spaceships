"""Each card's plotted front, as the site shows it.

The claim page opens on the card as it came off the plotter: the same
graph-paper grid, crosshatched cells and "Period 4 / 27 of 45" labels
that src.impose sends to the pen, one card per SVG, ink on paper.

    python -m src.card_art          -> web/art/<id>.svg for every deck card
"""
import argparse
import os
import re

from . import config
from . import impose
from . import plot_svg

OUT_DIR = os.path.join("web", "art")
PAPER = "#f6f3ec"
NUMBER = re.compile(r"-?\d+\.\d+")


def _round(svg):
    """Two decimals is 0.01 mm, far below the 0.35 mm pen."""
    return NUMBER.sub(lambda m: ("%.2f" % float(m.group())).rstrip("0").rstrip("."), svg)


def card_svg(card):
    layers = impose._card_front_layers_hatched(card["cells"], card["labels"])
    w, h = config.CARD_WIDTH_MM, config.CARD_HEIGHT_MM
    svg = [plot_svg._svg_header(w, h),
           '<rect width="%g" height="%g" fill="%s"/>' % (w, h, PAPER)]
    for name in impose.STYLE_LAYERS["hatched"]:
        if name in layers:
            svg.append(plot_svg._layer(name, layers[name]))
    svg.append("</svg>")
    return _round("".join(svg))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", default=["4", "5", "6", "7"])
    parser.add_argument("-o", "--out", default=OUT_DIR)
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    deck = impose.load_deck(args.periods)
    for card in deck:
        with open(os.path.join(args.out, card["id"] + ".svg"), "w") as f:
            f.write(card_svg(card))
    print("wrote %d card fronts to %s" % (len(deck), args.out))


if __name__ == "__main__":
    main()
