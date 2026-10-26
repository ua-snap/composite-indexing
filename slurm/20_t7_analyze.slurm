#!/bin/bash
#SBATCH --job-name=ci-t7
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# GIPL forcing test (T7, docs/GIPL_ISSUE_3.md): all analysis stages (mask ... wrf, ~30 min) + figures (gipl3_*.png).
# sites20 needs the t6b tables (slurm/18).
# Needs slurm/19 (all array tasks) and the t6 stacks. Submit from the repo root:
#   sbatch --dependency=afterok:<prep job id> slurm/20_t7_analyze.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export GDAL_PAM_ENABLED=NO
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t7_gipl_forcing.py analyze
$RUN scripts/03_report/gipl_forcing_figures.py
