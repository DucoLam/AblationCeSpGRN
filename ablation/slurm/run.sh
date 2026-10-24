#!/bin/bash
#SBATCH --job-name=ablation
#SBATCH --partition=general
#SBATCH --qos=short
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=ablation/slurm/logs/%x_%j.log

# Run any command inside the container, with the whole repo (upstream code and ablation/) mounted at /workspace.
# Submit through ablation/slurm/sbatch.sh for a log at ablation/slurm/logs/<date>/<time>_<job name>_<job id>.log;
# name the job with -J so the log says what it was. Plain sbatch logs to ablation/slurm/logs/<job name>_<job id>.log.
#
# Usage (from the repo root):
#   bash ablation/slurm/sbatch.sh -J kernel-sweep ablation/slurm/run.sh python path/to/script.py --arg value
#   bash ablation/slurm/sbatch.sh --qos=medium --time=12:00:00 ablation/slurm/run.sh python ...   # override resources
#   bash ablation/slurm/sbatch.sh --gres=gpu:1 ablation/slurm/run.sh python ...                    # on a GPU
# Set JOB_DESC to one sentence saying what the job does; it is printed at the top of the log.

SIF=${SIF:-ablation/ablation-cespgrn.sif}

echo "== ${SLURM_JOB_NAME:-local} (job ${SLURM_JOB_ID:-none}) on $(hostname), started $(date '+%Y-%m-%d %H:%M')"
echo "What: ${JOB_DESC:-no description given (set JOB_DESC when submitting)}"
echo "Runs: $*"
echo

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
