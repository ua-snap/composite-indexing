#!/bin/bash
#SBATCH --job-name=ci-summarize-fwi
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Wildfire Variant B: summarize the local CMIP6 FWI release (read-only, ~10 GB read) for Alaska, 2040-2069.
# Submit from the repo root:  sbatch slurm/21_summarize_fwi.slurm
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
ENV=$HOME/micromamba/envs/arcticdem-pisr
env PROJ_DATA=$ENV/share/proj $ENV/bin/python -I scripts/01_data/summarize_fwi.py
