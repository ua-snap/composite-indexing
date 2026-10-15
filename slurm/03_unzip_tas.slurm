#!/bin/bash
#SBATCH --job-name=ci-unzip-tas
#SBATCH --partition=transfer
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=04:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Extract SNAP 2 km monthly air temperature (READ-ONLY source on poseidon) into <data>/tas_tif/<set>/.
# 5modelAvg RCP 4.5 / 8.5 (2006-2100) + CRU TS 4.08 historical. Sequential, never overwrites (-n).
# Submit from the repo root:  sbatch slurm/03_unzip_tas.slurm
set -euo pipefail
B=/import/SNAP/poseidon/CKAN/CKAN_Data/Base/AK_CAN_2km
P=$B/projected/AR5_CMIP5_models/Projected_Monthly_and_Derived_Temperature_Products_2km_CMIP5_AR5/monthly
H=$B/historical/CRU_TS/Historical_Monthly_and_Derived_Temperature_Products_2km_CRU_TS
DST=/import/beegfs/CMIP6/jdpaul3/composite-indexing-data/tas_tif
for pair in "5modelAvg_rcp45:$P/tas_mean_C_AK_CAN_AR5_5modelAvg_rcp45_01_2006-12_2100.zip" \
            "5modelAvg_rcp85:$P/tas_mean_C_AK_CAN_AR5_5modelAvg_rcp85_01_2006-12_2100.zip" \
            "cru_ts408:$H/tas_AK_CAN_2km_CRU_TS408_historical.zip"; do
    set_=${pair%%:*}; zip=${pair#*:}
    mkdir -p "$DST/$set_"
    echo "$(date -Is) start $set_"
    unzip -n -q -j "$zip" '*.tif' -d "$DST/$set_"
    echo "$(date -Is) done  $set_: $(ls "$DST/$set_" | wc -l) files"
done
echo "$(date -Is) all done"
