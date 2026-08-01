"""Central configuration for the automons pipeline.

Every machine-specific path and project-wide constant lives here so the
pipeline can run somewhere other than the original workstation.  Override
anything with an environment variable.
"""
import os

# ---------------------------------------------------------------------------
# Local tool paths (search + Golly stages)
# ---------------------------------------------------------------------------

# Base directory Golly scripts read/write (auto_ntzfind output, rle output).
GOLLY_BASE = os.environ.get(
    "AUTOMONS_GOLLY_BASE",
    "/home/winston/devel/play/golly/Scripts/Python/",
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
    "https://john-winston.com/automons/",
)

# Catagolue object pages remain useful as a reference link in metadata.
CATAGOLUE_URL = "https://catagolue.hatsya.com/object/"

# ---------------------------------------------------------------------------
# NFT metadata
# ---------------------------------------------------------------------------

NFT_SYMBOL = os.environ.get("AUTOMONS_NFT_SYMBOL", "AUTOMON")
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
