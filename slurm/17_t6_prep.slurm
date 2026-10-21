#!/bin/bash
#SBATCH --job-name=ci-t6prep
#SBATCH --partition=analysis
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# GIPL_ISSUE_2.md: annual stacks of GIPL (4 depths x 3 runs x 2 RCPs), model/CRU MAAT and ESA on valid GIPL cells.
# Local files only. Resumable (skips finished stacks). Submit from the repo root:  sbatch slurm/17_t6_prep.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t6_gipl_levels.py prep
