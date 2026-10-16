#!/bin/bash
#SBATCH --job-name=ci-pti-drafts
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# PTI: rerun the index variants (t4) then the DRAFT team figures (docs/figures/drafts/). Local files only.
# Submit from the repo root:  sbatch slurm/14_pti_drafts.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t4_index_variants.py > /dev/null
$RUN scripts/03_report/pti_draft_figures.py
