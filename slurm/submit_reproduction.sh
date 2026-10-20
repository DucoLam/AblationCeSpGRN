#!/bin/bash
# Submit the full reproduction of paper Fig. 2b (CeSpGRN with the ATAC prior) and the paper's
# beta ablation (Fig. S3c, beta = 0 means no prior at all) as a chain of SLURM jobs:
#
#   simulate (R, per seed) -> build dataset (per seed x noise) -> CeSpGRN (per bandwidth) -> ensemble + scores
#
# Usage (from the repo root, on the DAIC login node):
#   bash slurm/submit_reproduction.sh                                   # full: 3 seeds x 2 noise levels, 8000 cells
#   NUM_CELLS=400 SEEDS=0 FPS=0.01 bash slurm/submit_reproduction.sh    # quick end-to-end check
#   GPU=0 bash slurm/submit_reproduction.sh                             # CeSpGRN on CPU when GPUs are scarce

set -euo pipefail

NUM_CELLS=${NUM_CELLS:-8000}
SEEDS=${SEEDS:-"0 1 2"}
FPS=${FPS:-"0.01 0.1"}
BANDWIDTHS=${BANDWIDTHS:-"0.01 0.1 1 10"}
GPU=${GPU:-1}

GPU_FLAG=()
[ "$GPU" = 1 ] && GPU_FLAG=(--gres=gpu:1)

submit() {
  sbatch --parsable "$@"
}

for seed in $SEEDS; do
  raw=data/scMultiSim/raw/cells${NUM_CELLS}_seed${seed}
  sim=$(submit -J "sim-s${seed}" --qos=medium --time=12:00:00 --cpus-per-task=2 --mem=32G \
    slurm/run.sh Rscript simulator/scmultisim/simulate.R "$seed" "$raw" "$NUM_CELLS")
  echo "seed $seed: simulate $sim"

  for fp in $FPS; do
    name=simulated_${NUM_CELLS}_20_10_100_${fp}_${seed}_0_4
    data=data/scMultiSim/$name
    build=$(submit -J "build-${fp}-s${seed}" --dependency=afterok:"$sim" --qos=short --time=01:00:00 \
      --cpus-per-task=2 --mem=16G \
      slurm/run.sh python simulator/scmultisim/build_dataset.py --raw "$raw" --out "$data" --fp "$fp" --seed "$seed")

    for variant in "beta_1_atac:1" "beta_0:0"; do
      run=results/scmultisim/$name/${variant%%:*}
      beta=${variant##*:}
      cespgrn_jobs=()
      for bw in $BANDWIDTHS; do
        cespgrn_jobs+=("$(submit -J "cespgrn-${fp}-s${seed}-b${beta}-bw${bw}" --dependency=afterok:"$build" \
          --qos=medium --time=08:00:00 --cpus-per-task=16 --mem=64G ${GPU_FLAG[@]+"${GPU_FLAG[@]}"} \
          slurm/run.sh python test/scripts_ablation/run_cespgrn.py --data "$data" --out "$run" \
            --bandwidth "$bw" --beta "$beta" --prior atac)")
      done
      deps=$(IFS=:; echo "${cespgrn_jobs[*]}")
      model="CeSpGRN (ATAC)"; [ "$beta" = 0 ] && model="CeSpGRN (w/o beta)"
      ens=$(submit -J "ensemble-${fp}-s${seed}-b${beta}" --dependency=afterok:"$deps" --qos=short \
        --time=02:00:00 --cpus-per-task=8 --mem=48G \
        slurm/run.sh python test/scripts_ablation/ensemble.py --data "$data" --run "$run" \
          --model "$model" $([ "$beta" = 1 ] && echo --score-priors))
      echo "  $name ${variant%%:*}: build $build, cespgrn ${cespgrn_jobs[*]}, ensemble $ens"
    done
  done
done
