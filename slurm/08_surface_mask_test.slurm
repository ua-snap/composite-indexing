#!/bin/bash
#SBATCH --job-name=ci-surface-mask
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Q12: does GIPL magtsurface need the stuck-cell mask? (reads <data>/gipl_tif; local only, no server requests).
# Submit from the repo root:  sbatch slurm/08_surface_mask_test.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t3h_surface_mask_test.py
