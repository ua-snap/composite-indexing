#!/bin/bash
#SBATCH --job-name=ci-ptic
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# PTI_COMPOSITE.md: composite 0-1 index (t5). Needs results/t4/index_variants.nc (slurm/15). Local files only.
# Submit from the repo root:  sbatch slurm/16_ptic.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t5_composite.py
$RUN scripts/03_report/test_area_maps.py  # test-area maps for PTI.md and PTI_COMPOSITE.md
