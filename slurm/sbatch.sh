#!/bin/bash
# sbatch with a readable log file: slurm/logs/<date>/<time>_<job name>_<job id>.log
#
# SLURM can't put dates in file names, so the date and time (of submission) are filled in
# here. SLURM itself writes the log, so tools that ask SLURM for a job's output file
# (scontrol, lazyslurm) find it.
#
# Usage (from the repo root), same arguments as sbatch:
#   bash slurm/sbatch.sh -J kernel-sweep slurm/run.sh python path/to/script.py
#   bash slurm/sbatch.sh --gres=gpu:1 slurm/run.sh python ...

log_dir=slurm/logs/$(date +%Y-%m-%d)
mkdir -p "$log_dir"
exec sbatch --output="$log_dir/$(date +%H%M%S)_%x_%j.log" "$@"
