#!/bin/bash
#SBATCH --job-name=ci-landcover-agg
#SBATCH --partition=t1small
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Extract (if needed) + aggregate land-cover products to the GIPL 1 km grid; with --analyze, run the analysis last.
# Usage (repo root):  sbatch slurm/06_landcover_agg.slurm nlcd2001 [nlcd2011 ...] [--analyze]
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
RUN="${MAMBA_EXE:-$HOME/.local/bin/micromamba} run -n arcticdem-pisr python -I"
LC=/import/beegfs/CMIP6/jdpaul3/composite-indexing-data/landcover
declare -A ZIP=([nlcd2001]=NLCD_2001_Land_Cover_AK_20200724 [nlcd2011]=NLCD_2011_Land_Cover_AK_20200724
                [nlcd2016]=NLCD_2016_Land_Cover_AK_20200724)
analyze=0
for p in "$@"; do
    [ "$p" = "--analyze" ] && { analyze=1; continue; }
    z=${ZIP[$p]}
    if [ ! -d "$LC/extracted/$z" ]; then mkdir -p "$LC/extracted/$z"; unzip -n -q "$LC/zip/$z.zip" -d "$LC/extracted/$z"; fi
    [ -f "$LC/agg/${p}_counts.npz" ] || { echo "$(date -Is) aggregate $p"; $RUN scripts/02_tests/t3f_landcover.py aggregate "$p"; }
done
[ $analyze = 1 ] && { echo "$(date -Is) analyze"; $RUN scripts/02_tests/t3f_landcover.py analyze; }
echo "$(date -Is) all done"
