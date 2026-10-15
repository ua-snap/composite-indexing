#!/bin/bash
#SBATCH --job-name=ci-gipl-statewide
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Statewide extent of the GIPL frozen-1 m artefact (reads <data>/gipl_tif; local only, no server requests).
# Submit from the repo root:  sbatch slurm/02_gipl_statewide.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t3c_gipl_statewide.py
