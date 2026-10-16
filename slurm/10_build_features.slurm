#!/bin/bash
#SBATCH --job-name=ci-build-features
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Phase A: statewide 1 km feature cube (needs the outputs of slurm/09_prep_features.slurm). Local files only.
# Submit from the repo root:  sbatch slurm/10_build_features.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/01_data/build_features.py
