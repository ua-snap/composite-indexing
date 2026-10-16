#!/bin/bash
#SBATCH --job-name=ci-t3-splice
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# T3 (Q8): ESA GST -> GIPL surface splice test (needs slurm/10). Local files only.
# Submit from the repo root:  sbatch slurm/12_t3_splice.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t3_surface_splice.py
