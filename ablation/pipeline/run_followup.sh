#!/bin/bash
# Experiments 3 and 5 on one dataset (seed 0, noise 0.01), in one job. Runs inside the container.
#   5_make_variants.py  random prior, shared prior, noise-0.3 prior, and a shuffled-RNA copy
#   3_run_cespgrn.py    CeSpGRN (β = 1) with each worse prior, and with shuffled RNA + the real prior
#   4_ensemble.py       ensemble, prior cut and scores per run, plus each prior alone
#
# Usage (from the repo root): bash ablation/pipeline/run_followup.sh [data dir] [raw dir] [results dir]

set -euo pipefail
data=${1:-ablation/data/scMultiSim/simulated_8000_20_10_100_0.01_0_0_4}
raw=${2:-ablation/data/scMultiSim/raw/cells8000_seed0}
out=${3:-ablation/results/scmultisim/followup_seed0_noise0.01}

python ablation/pipeline/5_make_variants.py --data "$data" --raw "$raw" --seed 0

# experiment 5: same RNA, worse priors
python ablation/pipeline/3_run_cespgrn.py --data "$data" --out-root "$out/priors" --betas 1 --priors random shared noise0.3
for prior in random shared noise0.3; do
  python ablation/pipeline/4_ensemble.py --data "$data" --run "$out/priors/beta_1_$prior" \
    --model "CeSpGRN ($prior prior)" --score-priors
done

# experiment 3: RNA without signal, real prior
python ablation/pipeline/3_run_cespgrn.py --data "${data}_shuffledRNA" --out-root "$out/shuffledRNA" --betas 1 --priors atac
python ablation/pipeline/4_ensemble.py --data "${data}_shuffledRNA" --run "$out/shuffledRNA/beta_1_atac" \
  --model "CeSpGRN (shuffled RNA)"
