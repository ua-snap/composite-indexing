#!/bin/bash
#SBATCH --job-name=ci-unzip-gipl
#SBATCH --partition=transfer
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=06:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Extract the SNAP GIPL 2.0 GeoTIFF zips (READ-ONLY source on poseidon) into <data>/gipl_tif/<variable>/.
# Sequential (gentle on the NFS source); never overwrites (-n), so it is safe to resubmit after a failure.
# Priority variables first so analysis can start before the job ends.
# Submit from the repo root:  sbatch slurm/01_unzip_gipl.slurm
set -euo pipefail
SRC=/import/SNAP/poseidon/CKAN/CKAN_Data/Base/AK_1km/GIPL
DST=/import/beegfs/CMIP6/jdpaul3/composite-indexing-data/gipl_tif
for v in magt1m magtsurface permafrosttop talikthickness magt0.5m magt2m magt3m magt4m magt5m permafrostbase; do
    mkdir -p "$DST/$v"
    echo "$(date -Is) start $v"
    unzip -n -q "$SRC/gipl_${v}_cmip5_2021-2120.zip" -d "$DST/$v"
    echo "$(date -Is) done  $v: $(ls "$DST/$v" | wc -l) files, $(du -sh "$DST/$v" | cut -f1)"
done
echo "$(date -Is) all done"
