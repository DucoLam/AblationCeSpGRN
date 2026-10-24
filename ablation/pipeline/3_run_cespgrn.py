"""
Run CeSpGRN on one simulated dataset for every kernel bandwidth, sparsity weight, β and prior,
exactly as upstream test/scripts_scmultisim/test_scmultisim.py does, and save per run (β, prior) and
bandwidth the sum of the partial-correlation graphs over the λs (before the final prior cut) for
4_ensemble.py.

Upstream's ensemble runs 4 bandwidths x 4 lambdas. The kernel, covariance and the kernel-weighted
covariance inside G_admm_mask depend only on the bandwidth, so they are computed once per bandwidth
and shared by every λ, β and prior (the solver's mask is swapped between priors).

Two differences from upstream's script, neither changes the result:
- With β = 0 upstream passes no mask at all. Here the mask is passed but multiplied by β = 0
  in every update, and the cut only happens for β > 0, so the numbers are the same.
- G_admm_mask.train recomputes the partial correlations of all cells after every batch of cells
  and keeps only the last; those intermediate passes are skipped, and the same upstream function
  (g_admm.construct_weighted_G) runs once on the final thetas.

Priors are read from masks_<name>.npy in the dataset dir (atac, tf, or variants from 5_make_variants.py).
Output: <out-root>/beta_1_<prior>/ per prior and <out-root>/beta_0/, each with Gs_soft_sum_bw<σ>.npy
and run_bw<σ>.json, and scores_per_setting.csv: every single bandwidth x λ network, after the same
prior cut as the ensemble, scored per cell (the networks themselves are not kept).

Usage (from the repo root):
    python ablation/pipeline/3_run_cespgrn.py --data ablation/data/scMultiSim/<dataset> \
        --out-root ablation/results/scmultisim/<dataset>
"""
import argparse
import json
import os
import sys
import time

# upstream CeSpGRN code (src/) and our replacements for its unpublished modules (ablation/lib/)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../src"))
sys.path.append(os.path.join(HERE, "../lib"))

import numpy as np
import pandas as pd
import torch
from sklearn.decomposition import PCA

import bmk
import cov
import g_admm
import kernel

construct_weighted_G = g_admm.construct_weighted_G


def run_dir(out_root, beta, prior):
    return os.path.join(out_root, f"beta_{beta:g}_{prior}" if beta > 0 else "beta_0")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--bandwidths", type=float, nargs="+", default=[0.01, 0.1, 1, 10])
    parser.add_argument("--lambs", type=float, nargs="+", default=[0.01, 0.05, 0.1, 0.5])
    parser.add_argument("--betas", type=float, nargs="+", default=[1, 0])
    parser.add_argument("--priors", nargs="+", default=["atac"], help="masks_<name>.npy to use when beta > 0")
    parser.add_argument("--truncate", type=int, default=100)
    parser.add_argument("--weighted-kt", type=int, choices=[0, 1], default=1)
    parser.add_argument("--no-setting-scores", action="store_true", help="don't score each bandwidth x λ")
    args = parser.parse_args()

    njobs = len(os.sched_getaffinity(0))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"njobs {njobs}, device {device}", flush=True)

    counts_rna = np.load(os.path.join(args.data, "counts_rna_true.npy"))
    libsize = np.median(np.sum(counts_rna, axis=1))
    counts_rna_norm = counts_rna / (np.sum(counts_rna, axis=1, keepdims=True) + 1e-6) * libsize
    counts_rna_norm = np.log1p(counts_rna_norm)

    def load_mask(name):
        return torch.FloatTensor(np.load(os.path.join(args.data, f"masks_{name}.npy")).astype(np.float32))

    # one run per prior for β > 0; β = 0 uses no prior, so it runs once
    runs = [(beta, prior) for beta in args.betas for prior in (args.priors if beta > 0 else [args.priors[0]])]
    X_pca = PCA(n_components=20).fit_transform(counts_rna_norm)
    Gs_gt = None if args.no_setting_scores else np.load(os.path.join(args.data, "graph_gt.npy"))
    setting_scores = {}  # run dir -> per-cell scores of each bandwidth x λ

    for bandwidth in args.bandwidths:
        start = time.time()
        K, K_trun = kernel.calc_kernel_neigh(X_pca, bandwidth=bandwidth, truncate=True, truncate_param=args.truncate)
        empir_cov = cov.est_cov_para(X=counts_rna_norm, K_trun=K_trun, weighted_kt=bool(args.weighted_kt), njobs=njobs)
        gadmm_batch = g_admm.G_admm_mask(X=counts_rna_norm[:, None, :], K=K, mask=None,
                                         pre_cov=torch.FloatTensor(empir_cov), batchsize=512, device=device)
        print(f"bandwidth {bandwidth}: kernel + covariance {time.time() - start:.0f} s", flush=True)

        for beta, prior in runs:
            gadmm_batch.mask = load_mask(prior)
            out = run_dir(args.out_root, beta, prior)
            os.makedirs(out, exist_ok=True)
            Gs_soft_sum = 0
            for lamb in args.lambs:
                start = time.time()
                g_admm.construct_weighted_G = lambda thetas, njobs=1: np.zeros_like(thetas)  # skip per-batch passes
                try:
                    gadmm_batch.train(max_iters=100, n_intervals=100, alpha=2, lamb=lamb, rho=1.7,
                                      theta_init_offset=0.1, beta=beta, njobs=njobs)
                finally:
                    g_admm.construct_weighted_G = construct_weighted_G
                Gs = construct_weighted_G(gadmm_batch.thetas, njobs=njobs)
                Gs_soft_sum = Gs_soft_sum + Gs
                print(f"bandwidth {bandwidth}, beta {beta:g}, prior {prior}, lambda {lamb}: {time.time() - start:.0f} s", flush=True)

                if Gs_gt is not None:
                    # same final cut as the ensemble in 4_ensemble.py
                    Gs_cut = Gs * (1 - gadmm_batch.mask.numpy()) if beta > 0 else Gs
                    scores = bmk.calc_scores_para(Gs_cut, Gs_gt, model=f"CeSpGRN ({prior})" if beta > 0 else "CeSpGRN (w/o beta)",
                                                  bandwidth=bandwidth, truncate_param=args.truncate, lamb=lamb, beta=beta,
                                                  njobs=njobs)
                    setting_scores.setdefault(out, []).append(scores)
                    pd.concat(setting_scores[out], ignore_index=True).to_csv(os.path.join(out, "scores_per_setting.csv"))
                    print(f"  AUPRC {scores['AUPRC (abs)'].mean():.3f}, Eprec {scores['Early Precision (abs)'].mean():.3f}", flush=True)
                del Gs

            np.save(os.path.join(out, f"Gs_soft_sum_bw{bandwidth}.npy"), Gs_soft_sum.astype(np.float32))
            with open(os.path.join(out, f"run_bw{bandwidth}.json"), "w") as f:
                json.dump({"data": args.data, "bandwidth": bandwidth, "lambs": args.lambs, "beta": beta,
                           "prior": prior, "truncate": args.truncate, "weighted_kt": args.weighted_kt,
                           "n_settings": len(args.lambs)}, f, indent=2)
        del gadmm_batch, empir_cov, K, K_trun


if __name__ == "__main__":
    main()
