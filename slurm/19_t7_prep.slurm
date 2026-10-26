#!/bin/bash
#SBATCH --job-name=ci-t7prep
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --array=0-15
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%A_%a.out
# GIPL forcing test (T7): annual air temperature on valid GIPL cells, one array task per candidate source
# (`python scripts/02_tests/t7_gipl_forcing.py list`). Reads SNAP's archive zips READ-ONLY via GDAL /vsizip/
# (GDAL_PAM_ENABLED=NO: no sidecar files). Resumable. Submit from the repo root:  sbatch slurm/19_t7_prep.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export GDAL_PAM_ENABLED=NO
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
$RUN scripts/02_tests/t7_gipl_forcing.py prep "${SLURM_ARRAY_TASK_ID}"
