#!/bin/bash
#SBATCH --job-name=ci-prep-features
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Phase A prep (local, read-only sources): ESA CCI 2021-2023 Alaska subsets (D12) + TII 1 km statistics.
# Submit from the repo root:  sbatch slurm/09_prep_features.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
echo "$(date -Is) ESA 2021-2023 subsets";  $RUN scripts/01_data/subset_esa_raw.py
echo "$(date -Is) TII 1 km statistics";    $RUN scripts/01_data/aggregate_tii.py
echo "$(date -Is) all done"
