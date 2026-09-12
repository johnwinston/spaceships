#!/bin/bash
# Plot the shared cut lines (card boundaries + outer edges) on the
# sheet currently taped to the machine.  Same for every 3x3 sheet.
set -u
DIR="$(dirname "$0")/../plots/sheets/plot"
"$(dirname "$0")/plotter_home.sh" || exit 1
DEV=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
saxi plot --device "$DEV" --no-fit-page --paper-size 279.4x215.9mm --margin 0 \
  --pen-up-height 20 --pen-down-height 68 \
  --pen-up-max-velocity 100 --pen-up-acceleration 200 --pen-lift-duration 0.35 --pen-drop-duration 0.25 \
  --pen-down-max-velocity 50 --pen-down-acceleration 200 "$DIR/cuts_baked.svg" \
  && echo "cuts complete"
