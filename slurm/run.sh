#!/bin/bash
#SBATCH --job-name=ablation
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=slurm/logs/%x_%j.log

# Run any command inside the container, with the repo mounted at /workspace.
# Submit through slurm/sbatch.sh for a log at slurm/logs/<date>/<time>_<job name>_<job id>.log;
# name the job with -J so the log says what it was. Plain sbatch logs to slurm/logs/<job name>_<job id>.log.
#
# Usage (from the repo root):
#   bash slurm/sbatch.sh -J kernel-sweep slurm/run.sh python path/to/script.py --arg value
#   bash slurm/sbatch.sh --qos=medium --time=12:00:00 slurm/run.sh python ...   # override resources
#   bash slurm/sbatch.sh --gres=gpu:1 slurm/run.sh python ...                    # on a GPU

SIF=${SIF:-ablation-cespgrn.sif}

# Expose the host's NVIDIA driver only when SLURM gave us a GPU
NV=()
if [ -n "${SLURM_GPUS_ON_NODE:-}${CUDA_VISIBLE_DEVICES:-}" ]; then
  NV=(--nv)
fi

apptainer run --containall "${NV[@]}" \
  --bind "$PWD":/workspace \
  --bind /tudelft.net:/tudelft.net \
  --pwd /workspace \
  "$SIF" "$@"
