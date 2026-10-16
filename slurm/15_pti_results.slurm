#!/bin/bash
#SBATCH --job-name=ci-pti-results
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# PTI.md: everything that depends on the two-way table. Index variants + table figure + data sentences (t4), section 3
# per-area figures + summary, V1 vs V2 and test-area figures, and the draft figures. Local files only.
# Submit from the repo root:  sbatch slurm/15_pti_results.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
echo "== t4";      $RUN scripts/02_tests/t4_index_variants.py
echo "== results"; $RUN scripts/03_report/pti_results_figures.py
echo "== extra";   $RUN scripts/03_report/pti_extra_figures.py
echo "== drafts";  $RUN scripts/03_report/pti_draft_figures.py
