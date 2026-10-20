#!/bin/bash
#SBATCH --job-name=ablation
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=slurm/out/%j_%x.out

# Run any command inside the container, with the repo mounted at /workspace.
#
# Usage (from the repo root):
#   sbatch slurm/run.sh python path/to/script.py --arg value
#   sbatch --qos=medium --time=12:00:00 slurm/run.sh python ...   # override resources

SIF=${SIF:-ablation-cespgrn.sif}

apptainer run --containall \
  --bind "$PWD":/workspace \
  --bind /tudelft.net:/tudelft.net \
  --pwd /workspace \
  "$SIF" "$@"
