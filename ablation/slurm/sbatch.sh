#!/bin/bash
# sbatch with a readable log file: ablation/slurm/logs/<date>/<time>_<job name>_<job id>.log
#
# SLURM can't put dates in file names, so the date and time (of submission) are filled in
# here. SLURM itself writes the log, so tools that ask SLURM for a job's output file
# (scontrol, lazyslurm) find it.
#
# Usage (from the repo root), same arguments as sbatch:
#   bash ablation/slurm/sbatch.sh -J kernel-sweep ablation/slurm/run.sh python path/to/script.py
#   bash ablation/slurm/sbatch.sh --gres=gpu:1 ablation/slurm/run.sh python ...
#
# JOB_DESC (required): one sentence saying what the job does. run.sh prints it at the top of the log.
#   JOB_DESC="Score prior variants on seed 0" bash ablation/slurm/sbatch.sh -J probe ablation/slurm/run.sh python ...

if [ -z "${JOB_DESC:-}" ]; then
  echo "Set JOB_DESC to one sentence saying what the job does, e.g. JOB_DESC=\"...\" bash $0 ..." >&2
  exit 1
fi
export JOB_DESC

log_dir=ablation/slurm/logs/$(date +%Y-%m-%d)
mkdir -p "$log_dir"
exec sbatch --output="$log_dir/$(date +%H%M%S)_%x_%j.log" "$@"
