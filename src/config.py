"""Central configuration for the automons pipeline.

Every machine-specific path and project-wide constant lives here so the
pipeline can run somewhere other than the original workstation.  Override
anything with an environment variable.
"""
import os

# ---------------------------------------------------------------------------
# Local tool paths (search pipeline stages)
# ---------------------------------------------------------------------------

# Base directory for pipeline intermediates: ntzfind's Life 1.05 output
# (ntzfind_patterns/<period>/) and converted RLEs (rles/<period>/).
# Historically this pointed into a Golly scripts directory because the
# .lif -> .rle step ran inside Golly; that step is now headless
# (src/lif2rle.py), so the default is repo-local and gitignored.
# AUTOMONS_GOLLY_BASE is honoured as a legacy override.
PIPELINE_BASE = (
    os.environ.get("AUTOMONS_PIPELINE_BASE")
    or os.environ.get("AUTOMONS_GOLLY_BASE")
    or os.path.join("data", "pipeline")
)

NTZFIND_BIN = os.environ.get(
    "AUTOMONS_NTZFIND_BIN",
    "./submodules/ntzfind/ntzfind",
)

# ---------------------------------------------------------------------------
# Web player / QR codes
# ---------------------------------------------------------------------------

# Public base URL of the hosted web player (web/ directory of this repo).
# The QR code on the back of each card points here.  GitHub Pages project
# site; the repo owner's custom domain (john-winston.com) applies to all
# project pages, so this — not johnwinston.github.io — is the canonical URL.
SITE_BASE_URL = os.environ.get(
    "AUTOMONS_SITE_URL",
    "https://john-winston.com/spaceships/",
)

# Catagolue object pages remain useful as a reference link in metadata.
CATAGOLUE_URL = "https://catagolue.hatsya.com/object/"

# ---------------------------------------------------------------------------
# Claims (claimcode.py, worker/)
# ---------------------------------------------------------------------------

# Environment variable holding the shared claim-code secret.  Card backs
# and the claim service both derive codes from it; it never lives in the
# repo.  Mint one with `python -m src.claimcode --new-secret`.
CLAIM_SECRET_ENV = "AUTOMONS_CLAIM_SECRET"
# Cap height of the claim code plotted under the QR on the card back.
CARD_CLAIM_CAP_MM = float(os.environ.get("AUTOMONS_CARD_CLAIM_CAP_MM", "3.0"))
# Gap between the QR's quiet zone and the claim code's cap line.
CARD_CLAIM_GAP_MM = 1.5

# ---------------------------------------------------------------------------
# NFT metadata
# ---------------------------------------------------------------------------

NFT_SYMBOL = os.environ.get("AUTOMONS_NFT_SYMBOL", "SHIPS")
NFT_DESCRIPTION = (
    "An isotropic cellular-automaton spaceship discovered by search. "
    "Scan the card, fly the ship, own the rule."
)
# Royalty basis points (500 = 5%). Used by nft_metadata.py.
NFT_SELLER_FEE_BASIS_POINTS = int(
    os.environ.get("AUTOMONS_NFT_ROYALTY_BPS", "500")
)

# ---------------------------------------------------------------------------
# Pen plotting (plot_svg.py)
# ---------------------------------------------------------------------------

# Card dimensions in millimetres (standard poker card).
CARD_WIDTH_MM = float(os.environ.get("AUTOMONS_CARD_W_MM", "63.5"))
CARD_HEIGHT_MM = float(os.environ.get("AUTOMONS_CARD_H_MM", "88.9"))
# Margin kept clear of pen strokes on every side.
CARD_MARGIN_MM = float(os.environ.get("AUTOMONS_CARD_MARGIN_MM", "6.0"))
# QR module (pixel) size on the card back.
QR_TARGET_MM = float(os.environ.get("AUTOMONS_QR_MM", "38.0"))
# Pen nib width; drives stroke width and the QR hatch-fill spacing.
PEN_WIDTH_MM = float(os.environ.get("AUTOMONS_PEN_MM", "0.35"))

# Common card grid (impose.py, hatched style).  Every card front shows
# the same box of cells -- width x height available to the ship -- with
# one cell of padding around it, so every card has the same cell size
# and the same graph-paper grid.  A ship larger than the box does not
# fit the deck and is left off the sheets.
CARD_GRID_BOX = tuple(
    int(v) for v in os.environ.get("AUTOMONS_CARD_BOX", "16x25").lower().split("x")
)
# Label band under the grid ("Period 4" bottom-left, "n of N" bottom-right):
# band height reserved below the grid, cap height of the stroke font, and
# the distance from the grid's bottom edge to the text baseline.
CARD_LABEL_BAND_MM = float(os.environ.get("AUTOMONS_CARD_LABEL_BAND_MM", "5.0"))
CARD_LABEL_CAP_MM = float(os.environ.get("AUTOMONS_CARD_LABEL_CAP_MM", "2.3"))
CARD_LABEL_BASELINE_MM = 3.5

# ---------------------------------------------------------------------------
# Spaceship search (auto_ntzfind.py, shipfit.py)
# ---------------------------------------------------------------------------

# ntzfind `w` values to sweep.  These are *search* widths, not ship widths:
# the ship's full width depends on the symmetry flag (2w for "v").  Memory
# in ntzfind.cpp scales as 4**w -- the submodule README measures ~19 GB at
# w11 -- so every extra width here costs roughly 4x the last one.
SEARCH_WIDTHS = tuple(
    int(w)
    for w in os.environ.get("AUTOMONS_SEARCH_WIDTHS", "6,7,8").split(",")
)
# ntzfind `k` values: cells travelled per period.  Pairs with k >= period
# are superluminal and get skipped.
SEARCH_OFFSETS = tuple(
    int(k)
    for k in os.environ.get("AUTOMONS_SEARCH_OFFSETS", "1,2").split(",")
)
# ntzfind symmetry flags to sweep: a=asymmetric, u=odd, v=even, g=gutter.
# Card-width ships are only reachable through a symmetric search --
# asymmetric would need w12+, which the 4**w memory curve puts out of
# reach -- so "a" is not in the default sweep.  Each flag has its own
# silhouette (v even-bilateral, u odd-bilateral, g split by an empty
# centre column) and its own width parity, so sweeping all three is what
# keeps a curated deck from looking like 52 of the same ship.
SEARCH_SYMMETRIES = tuple(
    s.strip()
    for s in os.environ.get("AUTOMONS_SEARCH_SYMMETRIES", "v,u,g").split(",")
    if s.strip()
)
# ntzfind `l`: abandon a search that reaches this depth.
SEARCH_DEPTH_LIMIT = int(os.environ.get("AUTOMONS_SEARCH_DEPTH", "200"))
# Keep ships whose width:height is within this fraction of the card's
# printable aspect (0.25 = +/-25%).
SEARCH_ASPECT_TOLERANCE = float(
    os.environ.get("AUTOMONS_SEARCH_ASPECT_TOL", "0.25")
)
# Minimum live-cell count.  Aspect and fill both say nothing about how
# *solid* a ship reads on the card: a wispy 12-cell ship can fill 96% of
# the box and still plot as a few scattered marks.  Calibrated against a
# manual period-7 curation pass where cuts ran 6-48 cells and keepers
# 61-104, with no overlap -- 55 sits in the gap.  Set to 0 to disable.
SEARCH_MIN_POPULATION = int(
    os.environ.get("AUTOMONS_SEARCH_MIN_POP", "55")
)
# Seconds before a single ntzfind invocation is abandoned.
SEARCH_TIMEOUT_S = float(os.environ.get("AUTOMONS_SEARCH_TIMEOUT", "120"))
