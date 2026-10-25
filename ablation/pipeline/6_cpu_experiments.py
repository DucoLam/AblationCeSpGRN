"""
The CPU-only experiments, from the saved results of one dataset (3_run_cespgrn.py + 4_ensemble.py).
Every network is scored per cell three ways: upstream's AUPRC and early precision (the paper's
metrics, bmk_beeline) and standard AUPRC (sklearn average_precision_score, which does not reward
ties; experiment 8). The upper triangle is used for the standard AUPRC; upstream uses the full matrix.

    --exp 4  soft penalty vs hard cut, 2 x 2: neither (β = 0), cut only (β = 0, then the prior cut),
             penalty only (β = 1 without the cut), both (β = 1 with the cut, as the paper)
    --exp 6  scores counted only inside the prior: among the edges the prior allows, does the RNA
             put the true ones first? Baseline is the expected AUPRC of a random order of those edges
             (exact, from the number of allowed and true edges); the share of true edges is also kept.
    --exp 7  plain correlation with the same prior and cut: global Pearson correlation of the
             log-normalised RNA, and (--kernel) CeSpGRN's own input, the kernel-weighted Kendall
             correlation per cell, averaged over the same 4 bandwidths
    --exp 8  standard AUPRC for the networks 4_ensemble.py scored: CeSpGRN with and without the
             prior, and the ATAC and TF priors alone (a network whose run is missing is skipped, e.g.
             no β = 0 run for the shuffled-RNA and worse-prior runs of run_followup.sh)

--prior picks the run and mask: beta_1_<prior>/ and masks_<prior>.npy (default atac).

Output: <out>/exp<N>_scores.csv (one row per cell and network) and a summary on stdout.

Usage (from the repo root):
    python ablation/pipeline/6_cpu_experiments.py --exp 4 --data ablation/data/scMultiSim/<dataset> \
        --results ablation/results/scmultisim/<dataset> --out ablation/results/scmultisim/<dataset>/cpu
"""
import argparse
import glob
import json
import os
import sys
from multiprocessing import Pool

# upstream CeSpGRN code (src/) and our replacements for its unpublished modules (ablation/lib/)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../src"))
sys.path.append(os.path.join(HERE, "../lib"))

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

import bmk

UPPER = None  # upper-triangle indices, set once the gene count is known


def _standard_ap(pair):
    G_inf, G_gt = pair
    y = G_gt[UPPER] != 0
    return average_precision_score(y, np.abs(G_inf[UPPER])) if y.any() else np.nan


def score(G, G_gt, model, njobs):
    """Upstream's per-cell AUPRC and early precision, plus standard AUPRC."""
    scores = bmk.calc_scores_para(G, G_gt, model=model, njobs=njobs)
    with Pool(njobs) as pool:
        scores["AUPRC (standard)"] = pool.map(_standard_ap, list(zip(G, G_gt)), chunksize=64)
    return scores


def random_order_ap(n, m):
    # expected average precision of a uniformly random order of n items with m true:
    # a true item at rank k has precision (1 + expected other true items above it) / k
    k = np.arange(1, n + 1)
    return np.mean((1 + (k - 1) * (m - 1) / max(n - 1, 1)) / k)


def _inside_prior(args):
    G_inf, G_gt, allowed = args
    keep = allowed[UPPER]
    y, s = G_gt[UPPER][keep] != 0, np.abs(G_inf[UPPER][keep])
    if not y.any():
        return np.nan, np.nan, np.nan, np.nan
    k = int(y.sum())
    top = np.argsort(-s, kind="stable")[:k]
    return average_precision_score(y, s), y[top].mean(), y.mean(), random_order_ap(len(y), k)


def score_inside_prior(G, G_gt, allowed, model, njobs):
    with Pool(njobs) as pool:
        rows = pool.map(_inside_prior, list(zip(G, G_gt, allowed)), chunksize=64)
    rows = np.array(rows)
    return pd.DataFrame({"time": np.arange(len(G)), "model": model,
                         "AUPRC inside prior": rows[:, 0], "Top-k precision inside prior": rows[:, 1],
                         "Share true inside prior": rows[:, 2], "Random order AUPRC inside prior": rows[:, 3]})


def ensemble_without_cut(run_dir):
    configs = [json.load(open(r)) for r in sorted(glob.glob(os.path.join(run_dir, "run_bw*.json")))]
    n_settings = sum(c["n_settings"] for c in configs)
    return sum(np.load(os.path.join(run_dir, f"Gs_soft_sum_bw{c['bandwidth']}.npy")) for c in configs) / n_settings


def log_norm_rna(data):
    counts = np.load(os.path.join(data, "counts_rna_true.npy"))
    libsize = np.median(np.sum(counts, axis=1))
    return np.log1p(counts / (np.sum(counts, axis=1, keepdims=True) + 1e-6) * libsize)


def main():
    global UPPER
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=int, choices=[4, 6, 7, 8], required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--results", required=True, help="results dir of 3_run_cespgrn.py / 4_ensemble.py for this dataset")
    parser.add_argument("--out", required=True)
    parser.add_argument("--kernel", action="store_true", help="exp 7: also the kernel-weighted correlation per cell (slow)")
    parser.add_argument("--prior", default="atac", help="beta_1_<prior>/ run and masks_<prior>.npy to use")
    parser.add_argument("--bandwidths", type=float, nargs="+", default=[0.01, 0.1, 1, 10])
    parser.add_argument("--truncate", type=int, default=100)
    args = parser.parse_args()
    njobs = len(os.sched_getaffinity(0))
    os.makedirs(args.out, exist_ok=True)

    G_gt = np.load(os.path.join(args.data, "graph_gt.npy"))
    allowed = np.load(os.path.join(args.data, f"masks_{args.prior}.npy")) == 0
    UPPER = np.triu_indices(G_gt.shape[1], k=1)
    beta1, beta0 = os.path.join(args.results, f"beta_1_{args.prior}"), os.path.join(args.results, "beta_0")
    has_beta0 = os.path.exists(os.path.join(beta0, "cespgrn_ensemble.npy"))
    scores = []

    if args.exp == 4:
        G = np.load(os.path.join(beta0, "cespgrn_ensemble.npy"))
        scores.append(score(G, G_gt, "Neither (beta 0)", njobs))
        scores.append(score(G * allowed, G_gt, "Cut only", njobs))
        del G
        G = ensemble_without_cut(beta1)
        scores.append(score(G, G_gt, "Penalty only", njobs))
        scores.append(score(G * allowed, G_gt, "Penalty + cut (paper)", njobs))

    elif args.exp == 6:
        for model, G in [("CeSpGRN (paper)", lambda: np.load(os.path.join(beta1, "cespgrn_ensemble.npy"))),
                         ("Penalty only", lambda: ensemble_without_cut(beta1)),
                         ("RNA only (beta 0)", lambda: np.load(os.path.join(beta0, "cespgrn_ensemble.npy")))]:
            if model.startswith("RNA only") and not has_beta0:
                continue
            scores.append(score_inside_prior(G(), G_gt, allowed, model, njobs))

    elif args.exp == 7:
        X = log_norm_rna(args.data)
        corr = np.nan_to_num(np.corrcoef(X.T)).astype(np.float32)
        np.fill_diagonal(corr, 0)
        G = np.broadcast_to(corr, G_gt.shape) * allowed
        scores.append(score(G, G_gt, "Correlation + cut", njobs))
        scores.append(score_inside_prior(G, G_gt, allowed, "Correlation + cut", njobs))
        del G
        if args.kernel:
            import cov
            import kernel
            from sklearn.decomposition import PCA
            X_pca = PCA(n_components=20).fit_transform(X)
            G = 0
            for bandwidth in args.bandwidths:
                _, K_trun = kernel.calc_kernel_neigh(X_pca, bandwidth=bandwidth, truncate=True, truncate_param=args.truncate)
                C = cov.est_cov_para(X=X, K_trun=K_trun, weighted_kt=True, njobs=njobs)
                C[:, np.arange(C.shape[1]), np.arange(C.shape[1])] = 0
                G = G + C / len(args.bandwidths)
                print(f"kernel correlation, bandwidth {bandwidth} done", flush=True)
            np.save(os.path.join(args.out, "kernel_correlation_ensemble.npy"), G.astype(np.float32))
            scores.append(score(G * allowed, G_gt, "Kernel correlation + cut", njobs))
            scores.append(score_inside_prior(G * allowed, G_gt, allowed, "Kernel correlation + cut", njobs))

    elif args.exp == 8:
        prior_tf = 1 - np.load(os.path.join(args.data, "masks_tf.npy"))
        for model, G in [(f"CeSpGRN ({args.prior.upper()})", lambda: np.load(os.path.join(beta1, "cespgrn_ensemble.npy"))),
                         (f"Prior ({args.prior.upper()})", lambda: allowed.astype(np.float32)),
                         ("Prior (TF)", lambda: prior_tf.astype(np.float32)),
                         ("CeSpGRN (w/o beta)", lambda: np.load(os.path.join(beta0, "cespgrn_ensemble.npy")))]:
            if model == "CeSpGRN (w/o beta)" and not has_beta0:
                continue
            scores.append(score(G(), G_gt, model, njobs))

    scores = pd.concat(scores, ignore_index=True)
    scores.to_csv(os.path.join(args.out, f"exp{args.exp}_scores.csv"))
    print(scores.drop(columns=[c for c in ["time", "bandwidth", "truncate_param", "lambda", "beta"] if c in scores])
          .groupby("model", sort=False).mean().round(3).to_string())


if __name__ == "__main__":
    main()
