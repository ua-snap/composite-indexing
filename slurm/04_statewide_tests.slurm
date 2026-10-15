#!/bin/bash
#SBATCH --job-name=ci-statewide-tests
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# STATSGO2 overlay (t3d) + MAAT vs MAGT on unaffected cells (t1). Local files only; needs the 5-class
# statewide_frozen_class.tif from slurm/02_gipl_statewide.slurm.
# Submit from the repo root:  sbatch slurm/04_statewide_tests.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
echo "== t3d STATSGO2 overlay"; $RUN scripts/02_tests/t3d_statsgo_overlay.py
echo "== t1 MAAT vs MAGT";      $RUN scripts/02_tests/t1_maat_vs_magt.py
