#!/bin/bash
#SBATCH --job-name=ci-t6
#SBATCH --partition=analysis
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# GIPL_ISSUE_2.md: start-up, level bias, drift, 0 degC classes (t6 analyze) + borehole / CUSP comparison (t6b)
# + figures (docs/figures/gipl2_*.png).
# Needs slurm/17 (stacks) and the borehole / CUSP downloads. Local files only.
# Submit from the repo root:  sbatch slurm/18_t6_analyze.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t6_gipl_levels.py analyze
$RUN scripts/02_tests/t6b_sites.py boreholes
$RUN scripts/02_tests/t6b_sites.py cusp
$RUN scripts/02_tests/t6b_sites.py compare
$RUN scripts/03_report/gipl_issue2_figures.py
