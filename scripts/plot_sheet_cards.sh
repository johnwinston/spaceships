#!/bin/bash
# Plot a sheet one card at a time: each card's grid (fast pass), then its
# cells+label (slow pass), before moving to the next card.  Aborts the
# whole run on the first saxi failure.
set -u
DEV=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "FAILED: no AxiDraw serial device found"; exit 1; }
echo "device: $DEV"
"$(dirname "$0")/plotter_home.sh" || exit 1
DIR="$(dirname "$0")/../plots/sheets/plot/cards"
SHEET="${1:?usage: plot_sheet_cards.sh s01 [start_card] [end_card]}"
START="${2:-1}"
END="${3:-9}"
for c in 1 2 3 4 5 6 7 8 9; do
  [ "$c" -lt "$START" ] && continue
  [ "$c" -gt "$END" ] && break
  grid="$DIR/${SHEET}_c${c}_grid.svg"
  inks="$DIR/${SHEET}_c${c}_inks.svg"
  [ -f "$grid" ] || { echo "done: no card $c"; break; }
  echo "card $c: grid"
  saxi plot --device "$DEV" --no-fit-page --paper-size 279.4x215.9mm --margin 0 \
    --pen-up-height 20 --pen-down-height 68 --pen-up-max-velocity 100 --pen-up-acceleration 200 --pen-lift-duration 0.35 --pen-drop-duration 0.25 \
    --pen-down-max-velocity 50 --pen-down-acceleration 200 "$grid" \
    || { echo "FAILED on card $c grid"; exit 1; }
  echo "card $c: cells+label"
  saxi plot --device "$DEV" --no-fit-page --paper-size 279.4x215.9mm --margin 0 \
    --pen-up-height 20 --pen-down-height 68 --pen-up-max-velocity 100 --pen-up-acceleration 200 --pen-lift-duration 0.35 --pen-drop-duration 0.25 \
    --pen-down-max-velocity 25 --pen-down-acceleration 100 "$inks" \
    || { echo "FAILED on card $c inks"; exit 1; }
  echo "card $c: complete"
done
echo "cut lines"
saxi plot --device "$DEV" --no-fit-page --paper-size 279.4x215.9mm --margin 0 \
  --pen-up-height 20 --pen-down-height 68 \
  --pen-up-max-velocity 100 --pen-up-acceleration 200 --pen-lift-duration 0.35 --pen-drop-duration 0.25 \
  --pen-down-max-velocity 50 --pen-down-acceleration 200 "$DIR/../cuts_baked.svg" \
  || { echo "FAILED on cut lines"; exit 1; }
echo "sheet $SHEET complete"
