#!/bin/bash
#SBATCH --job-name=build-container
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=slurm/out/%j_%x.out

# Build ablation-cespgrn.sif on DAIC from container_pixi.def.
# Builds on node-local /tmp, then moves the image into the repo root.
# The cache also lives on /tmp: umbrella is a Windows share where chmod is
# not permitted, which breaks Apptainer's blob cache.
#
# Usage (from the repo root):
#   sbatch slurm/build_container.sh

set -euo pipefail

SIF=ablation-cespgrn.sif
export APPTAINER_CACHEDIR=/tmp/$USER/apptainer-cache
export APPTAINER_TMPDIR=/tmp/$USER/apptainer-tmp
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

apptainer build --force "/tmp/$USER/$SIF" container_pixi.def
mv "/tmp/$USER/$SIF" "$SIF"
