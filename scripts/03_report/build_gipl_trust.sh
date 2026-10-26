#!/usr/bin/env bash
# Build docs/GIPL_TRUST.pdf (two-page GIPL data quality summary).
#   1. figures: scripts/03_report/gipl_trust_figures.py -> docs/figures/gipl_trust_*.pdf (reads <data>/results/t6/)
#   2. xelatex docs/GIPL_TRUST.tex (aux files and font caches in .claude/scratch/, PDF copied to docs/)
# Usage: bash scripts/03_report/build_gipl_trust.sh [--no-figures]
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="$REPO/.claude/scratch/latex"
mkdir -p "$BUILD" "$REPO/.claude/scratch/cache"
export XDG_CACHE_HOME="$REPO/.claude/scratch/cache" MPLCONFIGDIR="$REPO/.claude/scratch/cache/mpl" \
       TEXMFVAR="$REPO/.claude/scratch/cache/texmf-var"

if [[ "${1:-}" != "--no-figures" ]]; then
  micromamba run -n arcticdem-pisr python -I "$REPO/scripts/03_report/gipl_trust_figures.py"
fi
cd "$REPO/docs"
xelatex -interaction=nonstopmode -halt-on-error -output-directory="$BUILD" GIPL_TRUST.tex > "$BUILD/xelatex.out"
cp "$BUILD/GIPL_TRUST.pdf" "$REPO/docs/GIPL_TRUST.pdf"
grep -E "Output written|Overfull|Underfull|Warning" "$BUILD/xelatex.out" || true
