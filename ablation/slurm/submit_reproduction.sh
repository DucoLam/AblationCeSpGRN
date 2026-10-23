#!/bin/bash
# Submit the full reproduction of paper Fig. 2b (CeSpGRN with the ATAC prior) and the paper's
# beta ablation (Fig. S3c, beta = 0 means no prior at all) as a chain of SLURM jobs:
#
#   1_simulate.R (per seed) -> 2_build_dataset.py (per seed x noise) -> 3_run_cespgrn.py (per bandwidth)
#   -> 4_ensemble.py (averages the bandwidths, cuts with the prior, scores)   [all in ablation/pipeline/]
#
# Usage (from the repo root, on the DAIC login node):
#   bash ablation/slurm/submit_reproduction.sh                                   # full: 3 seeds x 2 noise levels, 8000 cells
#   NUM_CELLS=400 SEEDS=0 FPS=0.01 bash ablation/slurm/submit_reproduction.sh    # quick end-to-end check
#   GPU=0 bash ablation/slurm/submit_reproduction.sh                             # CeSpGRN on CPU when GPUs are scarce
#   NUM_CELLS=400 SEEDS=0 FPS=0.01 GPU=0 QOS=short TIME=00:30:00 CPUS=4 MEM=8G bash ablation/slurm/submit_reproduction.sh
#                                         # small CeSpGRN jobs start much sooner when the queue is full

set -euo pipefail

NUM_CELLS=${NUM_CELLS:-8000}
SEEDS=${SEEDS:-"0 1 2"}
FPS=${FPS:-"0.01 0.1"}
BANDWIDTHS=${BANDWIDTHS:-"0.01 0.1 1 10"}
GPU=${GPU:-1}
# resources for each CeSpGRN job (one per bandwidth)
QOS=${QOS:-medium}
TIME=${TIME:-08:00:00}
CPUS=${CPUS:-16}
MEM=${MEM:-64G}

GPU_FLAG=()
[ "$GPU" = 1 ] && GPU_FLAG=(--gres=gpu:1)

log_dir=ablation/slurm/logs/$(date +%Y-%m-%d)
mkdir -p "$log_dir"

submit() {
  sbatch --parsable --output="$log_dir/$(date +%H%M%S)_%x_%j.log" "$@"
}

for seed in $SEEDS; do
  raw=ablation/data/scMultiSim/raw/cells${NUM_CELLS}_seed${seed}
  sim=$(submit -J "sim-s${seed}" --qos=medium --time=12:00:00 --cpus-per-task=2 --mem=32G \
    ablation/slurm/run.sh Rscript ablation/pipeline/1_simulate.R "$seed" "$raw" "$NUM_CELLS")
  echo "seed $seed: simulate $sim"

  for fp in $FPS; do
    name=simulated_${NUM_CELLS}_20_10_100_${fp}_${seed}_0_4
    data=ablation/data/scMultiSim/$name
    build=$(submit -J "build-${fp}-s${seed}" --dependency=afterok:"$sim" --qos=short --time=01:00:00 \
      --cpus-per-task=2 --mem=16G \
      ablation/slurm/run.sh python ablation/pipeline/2_build_dataset.py --raw "$raw" --out "$data" --fp "$fp" --seed "$seed")

    for variant in "beta_1_atac:1" "beta_0:0"; do
      run=ablation/results/scmultisim/$name/${variant%%:*}
      beta=${variant##*:}
      cespgrn_jobs=()
      for bw in $BANDWIDTHS; do
        cespgrn_jobs+=("$(submit -J "cespgrn-${fp}-s${seed}-b${beta}-bw${bw}" --dependency=afterok:"$build" \
          --qos="$QOS" --time="$TIME" --cpus-per-task="$CPUS" --mem="$MEM" ${GPU_FLAG[@]+"${GPU_FLAG[@]}"} \
          ablation/slurm/run.sh python ablation/pipeline/3_run_cespgrn.py --data "$data" --out "$run" \
            --bandwidth "$bw" --beta "$beta" --prior atac)")
      done
      deps=$(IFS=:; echo "${cespgrn_jobs[*]}")
      model="CeSpGRN (ATAC)"; [ "$beta" = 0 ] && model="CeSpGRN (w/o beta)"
      ens=$(submit -J "ensemble-${fp}-s${seed}-b${beta}" --dependency=afterok:"$deps" --qos=short \
        --time=02:00:00 --cpus-per-task=8 --mem=48G \
        ablation/slurm/run.sh python ablation/pipeline/4_ensemble.py --data "$data" --run "$run" \
          --model "$model" $([ "$beta" = 1 ] && echo --score-priors))
      echo "  $name ${variant%%:*}: build $build, cespgrn ${cespgrn_jobs[*]}, ensemble $ens"
    done
  done
done
