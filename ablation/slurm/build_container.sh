#!/bin/bash
#SBATCH --job-name=build-container
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=ablation/slurm/logs/%x_%j.log

# Build ablation/ablation-cespgrn.sif on DAIC from ablation/container_pixi.def.
# Builds on node-local /tmp, then copies the image into ablation/.
# The cache also lives on /tmp: umbrella is a Windows share where chmod is
# not permitted, which breaks Apptainer's blob cache.
#
# Usage (from the repo root):
#   bash ablation/slurm/sbatch.sh ablation/slurm/build_container.sh

set -euo pipefail

echo "== ${SLURM_JOB_NAME:-local} (job ${SLURM_JOB_ID:-none}) on $(hostname), started $(date '+%Y-%m-%d %H:%M')"
echo "What: ${JOB_DESC:-Build the Apptainer image ablation/ablation-cespgrn.sif from container_pixi.def}"
echo

SIF=ablation-cespgrn.sif
OUT=ablation/$SIF
export APPTAINER_CACHEDIR=/tmp/$USER/apptainer-cache
export APPTAINER_TMPDIR=/tmp/$USER/apptainer-tmp
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

apptainer build --force "/tmp/$USER/$SIF" ablation/container_pixi.def
# Plain cp, not mv: mv tries to preserve permissions, which umbrella refuses
cp "/tmp/$USER/$SIF" "$OUT"
rm "/tmp/$USER/$SIF"
