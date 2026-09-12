#!/bin/bash
# Return the AxiDraw carriage to home (0,0) via the EBB's HM command.
# CRITICAL: never send EM (motor enable/disable) here — EM RESETS the
# step counter, making the board believe wherever it stands is home.
# The counter is zeroed by saxi at the start of each run (at true home),
# so HM is always safe: mid-run kills leave motors on and the counter
# valid; a completed run is already home; a fresh power-up at home is a
# no-op.
set -u
DEV=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$DEV" ] || { echo "no AxiDraw device"; exit 1; }
printf "SP,1\r" > "$DEV"      # pen up (EBB's stored up position)
sleep 0.5
printf "HM,8000\r" > "$DEV"   # return to (0,0) at ~100 mm/s
sleep 6
echo "carriage homed on $DEV"
