#!/bin/bash
# Submit the reproduction of paper Fig. 2b (CeSpGRN with the ATAC prior) and the paper's β ablation
# (Fig. S3c, β = 0 means no prior at all), with as few jobs as possible:
#
#   per seed, only when its datasets don't exist yet (CPU):
#       1_simulate.R + 2_build_dataset.py for every noise level
#   per dataset (GPU):
#       run_dataset.sh = 3_run_cespgrn.py (all bandwidths, λs and both β) + 4_ensemble.py per β
#
# Usage (from the repo root, on the DAIC login node):
#   bash ablation/slurm/submit_reproduction.sh                                  # 3 seeds x 2 noise levels, 8000 cells
#   NUM_CELLS=400 SEEDS=0 FPS=0.01 GPU=0 QOS=short TIME=01:00:00 CPUS=4 MEM=8G \
#     bash ablation/slurm/submit_reproduction.sh                                # small CPU test run
#   P_ZERO=0.2 NOISE=links SEEDS=0 bash ablation/slurm/submit_reproduction.sh  # rebuilt prior
#
# P_ZERO is scMultiSim's atac.p_zero (default 0.8), NOISE the noise mode of 2_build_dataset.py (default
# per-entry). Non-default values add _pz<P_ZERO> and _<NOISE> to the raw and dataset directory names.

set -euo pipefail

NUM_CELLS=${NUM_CELLS:-8000}
SEEDS=${SEEDS:-"0 1 2"}
FPS=${FPS:-"0.01 0.1"}
P_ZERO=${P_ZERO:-0.8}
NOISE=${NOISE:-per-entry}
pz_suffix=""
[ "$P_ZERO" = 0.8 ] || pz_suffix="_pz${P_ZERO}"
noise_suffix=""
[ "$NOISE" = per-entry ] || noise_suffix="_${NOISE}"
GPU=${GPU:-1}
# resources for each dataset job
QOS=${QOS:-medium}
TIME=${TIME:-12:00:00}
CPUS=${CPUS:-16}
MEM=${MEM:-96G}

GPU_FLAG=()
[ "$GPU" = 1 ] && GPU_FLAG=(--gres=gpu:1)

log_dir=ablation/slurm/logs/$(date +%Y-%m-%d)
mkdir -p "$log_dir"

submit() {
  sbatch --parsable --output="$log_dir/$(date +%H%M%S)_%x_%j.log" "$@"
}

dataset() {  # dataset dir for a noise level and seed
  echo "ablation/data/scMultiSim/simulated_${NUM_CELLS}_20_10_100_$1_$2_0_4${pz_suffix}${noise_suffix}"
}

for seed in $SEEDS; do
  raw=ablation/data/scMultiSim/raw/cells${NUM_CELLS}_seed${seed}${pz_suffix}

  # simulate and build only the datasets that are missing, all in one CPU job
  steps=()
  [ -f "$raw/grn_edges.tsv" ] || steps+=("Rscript ablation/pipeline/1_simulate.R $seed $raw $NUM_CELLS $P_ZERO")
  for fp in $FPS; do
    data=$(dataset "$fp" "$seed")
    [ -f "$data/prior_stats.json" ] || \
      steps+=("python ablation/pipeline/2_build_dataset.py --raw $raw --out $data --fp $fp --seed $seed --noise $NOISE")
  done
  dep=()
  if [ ${#steps[@]} -gt 0 ]; then
    prep=$(JOB_DESC="Simulate seed $seed (${NUM_CELLS} cells, atac.p_zero $P_ZERO) if missing, and build its datasets for noise $FPS ($NOISE noise)" \
      submit -J "prep-s${seed}${pz_suffix}${noise_suffix}" --qos=short --time=01:00:00 --cpus-per-task=2 --mem=32G \
      ablation/slurm/run.sh bash -c "set -e; $(IFS=';'; echo "${steps[*]}")")
    dep=(--dependency=afterok:"$prep")
    echo "seed $seed: prepare data $prep"
  fi

  for fp in $FPS; do
    data=$(dataset "$fp" "$seed")
    name=$(basename "$data")
    job=$(JOB_DESC="Fig. 2b reproduction on $name: CeSpGRN for all bandwidths and lambdas with the ATAC prior (beta 1) and without it (beta 0), then ensemble and scores" \
      submit -J "cespgrn-${fp}-s${seed}${pz_suffix}${noise_suffix}" ${dep[@]+"${dep[@]}"} \
      --qos="$QOS" --time="$TIME" --cpus-per-task="$CPUS" --mem="$MEM" ${GPU_FLAG[@]+"${GPU_FLAG[@]}"} \
      ablation/slurm/run.sh bash ablation/pipeline/run_dataset.sh "$data" "ablation/results/scmultisim/$name")
    echo "  $name: CeSpGRN + scores $job"
  done
done
