"""
Average the per-bandwidth runs of 3_run_cespgrn.py into upstream's ensemble GRN, apply the same
final prior cut as upstream (test_scmultisim.py lines 222-225), and score every cell.
Also scores the prior on its own, as upstream's eval_scores.py does ("Prior (ATAC)").

Usage (from the repo root):
    python ablation/pipeline/4_ensemble.py --data ablation/data/scMultiSim/<dataset> \
        --run ablation/results/scmultisim/<dataset>/<run> --model "CeSpGRN (ATAC)"
"""
import argparse
import glob
import json
import os
import sys

# upstream CeSpGRN code (src/) and our replacements for its unpublished modules (ablation/lib/)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../src"))
sys.path.append(os.path.join(HERE, "../lib"))

import numpy as np
import pandas as pd

import bmk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--score-priors", action="store_true", help="also score the ATAC and TF priors alone")
    args = parser.parse_args()
    njobs = len(os.sched_getaffinity(0))

    runs = sorted(glob.glob(os.path.join(args.run, "run_bw*.json")))
    configs = [json.load(open(r)) for r in runs]
    n_settings = sum(c["n_settings"] for c in configs)
    Gs_ensemble = sum(np.load(os.path.join(args.run, f"Gs_soft_sum_bw{c['bandwidth']}.npy")) for c in configs) / n_settings
    beta, prior = configs[0]["beta"], configs[0]["prior"]
    print(f"{len(configs)} bandwidths, {n_settings} settings, beta {beta}, prior {prior}")

    if beta > 0:
        masks = np.load(os.path.join(args.data, f"masks_{prior}.npy"))
        Gs_ensemble = Gs_ensemble * (1 - masks)
    np.save(os.path.join(args.run, "cespgrn_ensemble.npy"), Gs_ensemble)

    Gs_gt = np.load(os.path.join(args.data, "graph_gt.npy"))
    scores = [bmk.calc_scores_para(Gs_ensemble, Gs_gt, model=args.model, beta=beta, njobs=njobs)]
    if args.score_priors:
        for name in ["atac", "tf"]:
            prior_graph = 1 - np.load(os.path.join(args.data, f"masks_{name}.npy"))
            scores.append(bmk.calc_scores_para(prior_graph, Gs_gt, model=f"Prior ({name.upper()})", njobs=njobs))
    scores = pd.concat(scores, ignore_index=True)
    scores.to_csv(os.path.join(args.run, "scores.csv"))

    summary = scores.groupby("model")[["AUPRC (abs)", "Early Precision (abs)"]].mean()
    print(summary.round(3).to_string())


if __name__ == "__main__":
    main()
