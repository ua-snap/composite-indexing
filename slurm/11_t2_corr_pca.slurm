#!/bin/bash
#SBATCH --job-name=ci-t2-corr-pca
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# T1 Spearman + T2 PCA/VIF on the feature cube (needs slurm/10). Local files only.
# Submit from the repo root:  sbatch slurm/11_t2_corr_pca.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t2_correlation_pca.py
