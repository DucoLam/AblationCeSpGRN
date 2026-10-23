"""
Run CeSpGRN on one simulated dataset for one kernel bandwidth and all sparsity weights,
exactly as upstream test/scripts_scmultisim/test_scmultisim.py does, and save the sum of the
resulting partial-correlation graphs (before the final prior cut) for 4_ensemble.py.

Upstream's ensemble runs 4 bandwidths x 4 lambdas. One job per bandwidth keeps each job's
covariance (the slow, CPU-bound step) in memory while its 4 lambdas run on the GPU.

Usage (from the repo root):
    python ablation/pipeline/3_run_cespgrn.py --data ablation/data/scMultiSim/<dataset> \
        --out ablation/results/scmultisim/<dataset>/<run> --bandwidth 0.1 --beta 1 --prior atac
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
import torch
from sklearn.decomposition import PCA

import cov
import g_admm
import kernel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bandwidth", type=float, required=True)
    parser.add_argument("--lambs", type=float, nargs="+", default=[0.01, 0.05, 0.1, 0.5])
    parser.add_argument("--beta", type=float, default=1)
    parser.add_argument("--prior", choices=["atac", "tf"], default="atac", help="used only when beta > 0")
    parser.add_argument("--truncate", type=int, default=100)
    parser.add_argument("--weighted-kt", type=int, choices=[0, 1], default=1)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    njobs = len(os.sched_getaffinity(0))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"njobs {njobs}, device {device}", flush=True)

    counts_rna = np.load(os.path.join(args.data, "counts_rna_true.npy"))
    libsize = np.median(np.sum(counts_rna, axis=1))
    counts_rna_norm = counts_rna / (np.sum(counts_rna, axis=1, keepdims=True) + 1e-6) * libsize
    counts_rna_norm = np.log1p(counts_rna_norm)

    # upstream: masks only when beta > 0; with beta = 0 the model runs without any prior
    masks = np.load(os.path.join(args.data, f"masks_{args.prior}.npy")).astype(np.float32) if args.beta > 0 else None

    start = time.time()
    X_pca = PCA(n_components=20).fit_transform(counts_rna_norm)
    K, K_trun = kernel.calc_kernel_neigh(X_pca, bandwidth=args.bandwidth, truncate=True, truncate_param=args.truncate)
    empir_cov = cov.est_cov_para(X=counts_rna_norm, K_trun=K_trun, weighted_kt=bool(args.weighted_kt), njobs=njobs)
    print(f"kernel + covariance: {time.time() - start:.0f} s", flush=True)

    Gs_soft_sum = 0
    for lamb in args.lambs:
        start = time.time()
        gadmm_batch = g_admm.G_admm_mask(X=counts_rna_norm[:, None, :], K=K, mask=masks,
                                         pre_cov=torch.FloatTensor(empir_cov), batchsize=512, device=device)
        gadmm_batch.train(max_iters=100, n_intervals=100, alpha=2, lamb=lamb, rho=1.7,
                          theta_init_offset=0.1, beta=args.beta, njobs=njobs)
        Gs_soft_sum = Gs_soft_sum + g_admm.construct_weighted_G(gadmm_batch.thetas, njobs=njobs)
        print(f"lambda {lamb}: {time.time() - start:.0f} s", flush=True)
        del gadmm_batch

    np.save(os.path.join(args.out, f"Gs_soft_sum_bw{args.bandwidth}.npy"), Gs_soft_sum.astype(np.float32))
    with open(os.path.join(args.out, f"run_bw{args.bandwidth}.json"), "w") as f:
        json.dump({**vars(args), "n_settings": len(args.lambs)}, f, indent=2)


if __name__ == "__main__":
    main()
