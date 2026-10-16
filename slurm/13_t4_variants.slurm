#!/bin/bash
#SBATCH --job-name=ci-t4-variants
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# T4: index variants on the fixed scale (needs slurm/10 + make_regions.py). Local files only.
# Submit from the repo root:  sbatch slurm/13_t4_variants.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t4_index_variants.py
