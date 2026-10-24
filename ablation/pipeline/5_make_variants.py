"""
Make the variants for experiments 3 and 5 from one built dataset (2_build_dataset.py output).

Experiment 5, worse priors, written into the dataset dir as extra masks (1 = edge not allowed):
    masks_random.npy    per cell, the same number of allowed edges as the ATAC prior, placed at random
    masks_shared.npy    one prior for every cell: the edges allowed in the most cells, as many as the
                        ATAC prior allows on average (removes cell-specificity, keeps the density)
    masks_noise0.3.npy  the ATAC prior built with noise 0.3 instead of 0.01 (2_build_dataset.py --fp 0.3)

Experiment 3, RNA without signal, written as a new dataset dir <data>_shuffledRNA: each gene's
expression permuted across cells independently (keeps every gene's distribution, destroys
co-expression and the cell neighbourhoods), with the same ground truth and priors.

Usage (from the repo root):
    python ablation/pipeline/5_make_variants.py --data ablation/data/scMultiSim/<dataset> \
        --raw ablation/data/scMultiSim/raw/<raw> --seed 0
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np


def prior_stats(masks, graph_gt):
    upper = np.triu_indices(masks.shape[1], k=1)
    p = masks[:, upper[0], upper[1]] == 0
    t = graph_gt[:, upper[0], upper[1]] != 0
    tp = (p & t).sum(axis=1)
    return {"precision": float(np.mean(tp / np.maximum(p.sum(axis=1), 1))),
            "recall": float(np.mean(tp / np.maximum(t.sum(axis=1), 1))),
            "density": float(p.mean())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--noise", type=float, default=0.3)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    masks = np.load(os.path.join(args.data, "masks_atac.npy"))
    graph_gt = np.load(os.path.join(args.data, "graph_gt.npy"))
    ncells, ngenes, _ = masks.shape
    upper = np.triu_indices(ngenes, k=1)
    allowed = masks[:, upper[0], upper[1]] == 0          # cells x gene pairs
    stats = {"atac": prior_stats(masks, graph_gt)}

    def to_masks(allowed_pairs):
        out = np.ones((ncells, ngenes, ngenes), dtype=np.uint8)
        out[:, upper[0], upper[1]] = ~allowed_pairs
        out[:, upper[1], upper[0]] = ~allowed_pairs
        return out

    # random prior: same number of allowed pairs per cell
    random_allowed = np.zeros_like(allowed)
    for i, k in enumerate(allowed.sum(axis=1)):
        random_allowed[i, rng.choice(allowed.shape[1], size=k, replace=False)] = True
    np.save(os.path.join(args.data, "masks_random.npy"), to_masks(random_allowed))

    # shared prior: the most frequently allowed pairs, as many as a cell allows on average
    k = int(round(allowed.sum(axis=1).mean()))
    top = np.argsort(-allowed.sum(axis=0), kind="stable")[:k]
    shared_allowed = np.zeros(allowed.shape[1], dtype=bool)
    shared_allowed[top] = True
    np.save(os.path.join(args.data, "masks_shared.npy"), to_masks(np.repeat(shared_allowed[None], ncells, axis=0)))

    # noisier prior: the same build step with a higher noise level
    noisy_dir = args.data.rstrip("/") + f"_noise{args.noise:g}"
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "2_build_dataset.py"),
                    "--raw", args.raw, "--out", noisy_dir, "--fp", str(args.noise), "--seed", str(args.seed)], check=True)
    shutil.copyfile(os.path.join(noisy_dir, "masks_atac.npy"), os.path.join(args.data, f"masks_noise{args.noise:g}.npy"))

    for name in ["random", "shared", f"noise{args.noise:g}"]:
        stats[name] = prior_stats(np.load(os.path.join(args.data, f"masks_{name}.npy")), graph_gt)

    # shuffled RNA, same ground truth and priors
    shuffled_dir = args.data.rstrip("/") + "_shuffledRNA"
    os.makedirs(shuffled_dir, exist_ok=True)
    counts = np.load(os.path.join(args.data, "counts_rna_true.npy"))
    shuffled = np.stack([rng.permutation(counts[:, g]) for g in range(counts.shape[1])], axis=1)
    np.save(os.path.join(shuffled_dir, "counts_rna_true.npy"), shuffled)
    for f in ["graph_gt.npy", "masks_atac.npy", "masks_tf.npy", "meta_cells.tsv"]:
        shutil.copyfile(os.path.join(args.data, f), os.path.join(shuffled_dir, f))

    with open(os.path.join(args.data, "variant_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print("priors vs ground truth:", json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
