#!/bin/bash
#SBATCH --job-name=ci-dl-landcover
#SBATCH --partition=transfer
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=06:00:00
#SBATCH --output=/beegfs/CMIP6/jdpaul3/composite-indexing-data/logs/%x_%j.out
# Public land cover for the GIPL stuck-cell test: NLCD Alaska 2001/2011/2016 (USGS ScienceBase item
# 5f650b8682ce38aaa23be1bd, 20200724 release). Sequential; resumable (-C -). (NALCMS 2015 "USA" tile was dropped:
# it covers only the lower 48.)
# Submit from the repo root:  sbatch slurm/05_download_landcover.slurm
set -euo pipefail
D=/import/beegfs/CMIP6/jdpaul3/composite-indexing-data/landcover/zip
SB="https://www.sciencebase.gov/catalog/file/get/5f650b8682ce38aaa23be1bd?f=__disk__"
get() {  # name url expected_bytes
    echo "$(date -Is) start $1"
    curl -sS -L --retry 5 --retry-delay 10 -C - -o "$D/$1" "$2"
    sz=$(stat -c %s "$D/$1"); echo "$(date -Is) done  $1: $sz bytes (expected $3)"
    [ "$sz" = "$3" ] || { echo "SIZE MISMATCH $1"; exit 1; }
    unzip -tq "$D/$1" && echo "zip OK $1"
    sleep 2
}
get NLCD_2001_Land_Cover_AK_20200724.zip "${SB}44%2Fbb%2Fa5%2F44bba57099c49da13ada58bcc3de3c58f60e667d" 405697879
get NLCD_2011_Land_Cover_AK_20200724.zip "${SB}30%2F73%2F28%2F307328c535692447a555c9f24e4e788748bb6e9d" 408659726
get NLCD_2016_Land_Cover_AK_20200724.zip "${SB}13%2F7f%2Fb5%2F137fb52a85239da9b37797327cb161d46e03f6c2" 408811745
echo "$(date -Is) all done"
