#!/bin/bash
# Everything for one simulated dataset, in one job: CeSpGRN for all bandwidths, λs and both β
# (step 3), then the ensemble, prior cut and scores per β (step 4). Runs inside the container.
#
# Usage (from the repo root): bash ablation/pipeline/run_dataset.sh <data dir> <results dir>

set -euo pipefail
data=$1
out=$2

python ablation/pipeline/3_run_cespgrn.py --data "$data" --out-root "$out"
python ablation/pipeline/4_ensemble.py --data "$data" --run "$out/beta_1_atac" --model "CeSpGRN (ATAC)" --score-priors
python ablation/pipeline/4_ensemble.py --data "$data" --run "$out/beta_0" --model "CeSpGRN (w/o beta)"
