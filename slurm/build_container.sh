#!/bin/bash
#SBATCH --job-name=build-container
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=slurm/logs/.slurm/%j.log

# Build ablation-cespgrn.sif on DAIC from container_pixi.def.
# Builds on node-local /tmp, then moves the image into the repo root.
# The cache also lives on /tmp: umbrella is a Windows share where chmod is
# not permitted, which breaks Apptainer's blob cache.
# Output goes to slurm/logs/<date>/<time>_build-container_<job id>.log.
#
# Usage (from the repo root):
#   sbatch slurm/build_container.sh

set -euo pipefail

LOG_DIR=slurm/logs/$(date +%Y-%m-%d)
mkdir -p "$LOG_DIR"
exec > "$LOG_DIR/$(date +%H%M%S)_${SLURM_JOB_NAME}_${SLURM_JOB_ID}.log" 2>&1

SIF=ablation-cespgrn.sif
export APPTAINER_CACHEDIR=/tmp/$USER/apptainer-cache
export APPTAINER_TMPDIR=/tmp/$USER/apptainer-tmp
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

apptainer build --force "/tmp/$USER/$SIF" container_pixi.def
# Plain cp, not mv: mv tries to preserve permissions, which umbrella refuses
cp "/tmp/$USER/$SIF" "$SIF"
rm "/tmp/$USER/$SIF"
