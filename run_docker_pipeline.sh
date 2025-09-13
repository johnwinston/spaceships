#!/usr/bin/env bash

# Simple Docker wrapper for Automons on Apple Silicon (forces x86_64).
# Usage examples:
#   bash run_docker_pipeline.sh                         # default: rle2apgcode 4
#   bash run_docker_pipeline.sh rle2apgcode 6           # convert RLEs for period 6
#   bash run_docker_pipeline.sh clear-files 4           # clear Golly RLEs and patterns for period 4
#   bash run_docker_pipeline.sh auto-ntzfind 4 12       # ntzfind 12 ships then convert
#   bash run_docker_pipeline.sh all 4 12 --no-clear     # full flow, skip clearing
# You can override your local Golly install path by exporting GOLLY_DIR before running.

set -euo pipefail

# Resolve repo root to mount into container
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"

# Configure your local Golly installation directory.
# Can be overridden by exporting GOLLY_DIR before running this script.
: "${GOLLY_DIR:=/Volumes/Macintosh HD/Users/winston/devel/golly-4.3-mac}"

# Parse arguments
CMD="${1:-rle2apgcode}"
PERIOD="${2:-4}"
ITERATIONS="${3:-10}"
# Extra args (e.g., --no-clear)
shift $(( $# > 0 ? 1 : 0 )) || true
shift $(( ${#} > 0 ? 1 : 0 )) || true
shift $(( ${#} > 0 ? 1 : 0 )) || true
EXTRA_ARGS="$*"

DOCKER_IMAGE="python:3.11-bullseye"

echo "Running: command=$CMD period=$PERIOD iterations=$ITERATIONS GOLLY_DIR=$GOLLY_DIR"

# Build the Python command to run inside the container
if [[ "$CMD" == "auto-ntzfind" || "$CMD" == "all" ]]; then
  PY_CMD="python main.py $CMD $PERIOD $ITERATIONS $EXTRA_ARGS"
else
  PY_CMD="python main.py $CMD $PERIOD $EXTRA_ARGS"
fi

docker run --rm --platform=linux/amd64 \
  -v "$REPO_DIR":/work \
  -v "$GOLLY_DIR":/golly \
  -e GOLLY_DIR=/golly \
  -w /work \
  "$DOCKER_IMAGE" \
  bash -lc "apt-get update && apt-get install -y --no-install-recommends build-essential git && \
            pip install --no-cache-dir -r requirements.txt && \
            python -c 'from submodules import lifelib; print(lifelib.compile_rules(\"b3s23\"))' && \
            mkdir -p /golly/Scripts/Python/rles/$PERIOD /golly/Scripts/Python/ntzfind_patterns/$PERIOD && \
            $PY_CMD | cat"


