"""
Turn one raw scMultiSim simulation (1_simulate.R output) into a CeSpGRN benchmark dataset:
ground-truth GRNs, the per-cell ATAC prior with false-positive noise, and the TF prior.

The ATAC prior follows paper Section 2.3 and Fig. S1. A TF-target edge is allowed in cell i
when an open region links them:

    prior_i = 1[ RG^T . diag(open_i) . RT_i > 0 ]

RG is region x gene, RT_i is region x TF, open_i marks regions with ATAC > 0 in cell i.
RT_i is rebuilt per cell from that cell's GRN with scMultiSim's own rule (.regionToTFMatrix):
a TF is linked to a region when it positively regulates a gene behind that region. This matches
the per-cell region_tf_{i}.txt files upstream reads; --region-tf global uses scMultiSim's single RT.

Noise (fp, "false positive connections", Note 1.8): every 0 in RG and RT becomes 1 with
probability fp, only in the copies used for the prior. The same noise applies to all cells.

Outputs match what upstream's scripts compute from their text files:
    counts_rna_true.npy  (cells x genes)
    graph_gt.npy         (cells x genes x genes), symmetric, as G_gt + G_gt.T
    masks_atac.npy       (cells x genes x genes), 1 = edge not allowed
    masks_tf.npy         (cells x genes x genes), 1 = target-target edge
    prior_stats.json     precision and recall of the prior against the ground truth
"""

import argparse
import json
import os
import shutil

import numpy as np
import pandas as pd


def read_matrix(path):
    return pd.read_csv(path, sep="\t", header=None).values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True, help="1_simulate.R output directory")
    parser.add_argument("--out", required=True)
    parser.add_argument("--fp", type=float, required=True, help="noise level, e.g. 0.01 or 0.1")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--region-tf", choices=["per-cell", "global"], default="per-cell")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    counts = pd.read_csv(os.path.join(args.raw, "counts_rna_true.tsv"), sep="\t", index_col=0).T.values
    atac = pd.read_csv(os.path.join(args.raw, "counts_atac_true.tsv"), sep="\t", index_col=0).T.values
    region_gene = read_matrix(os.path.join(args.raw, "region_to_gene.tsv")) > 0
    region_tf_global = read_matrix(os.path.join(args.raw, "region_to_tf.tsv")) > 0
    regulators = pd.read_csv(os.path.join(args.raw, "regulators.tsv"), sep="\t")["regulator"].values - 1
    edges = pd.read_csv(os.path.join(args.raw, "grn_edges.tsv"), sep="\t")

    ncells, ngenes = counts.shape
    nregions = region_gene.shape[0]
    nregs = len(regulators)
    reg_col = {g: k for k, g in enumerate(regulators)}
    print(f"{ncells} cells, {ngenes} genes, {nregions} regions, {nregs} regulators")

    # Per-cell GRN as gene x regulator effects, and the symmetric gene x gene ground truth
    geff = np.zeros((ncells, ngenes, nregs), dtype=np.float32)
    cells = edges["cell"].values - 1
    targets = edges["target"].values - 1
    regs = edges["regulator"].values - 1
    geff[cells, targets, [reg_col[r] for r in regs]] = edges["weight"].values
    graph_gt = np.zeros((ncells, ngenes, ngenes), dtype=np.float32)
    graph_gt[:, :, regulators] = geff
    graph_gt = graph_gt + graph_gt.transpose(0, 2, 1)

    # Noise on the copies of the cross-modality matrices used for the prior
    rng = np.random.default_rng([args.seed, round(args.fp * 1e6)])
    region_gene_noisy = region_gene | (rng.random(region_gene.shape) < args.fp)
    region_tf_noise = rng.random((nregions, nregs)) < args.fp

    is_open = atac > 0
    masks_atac = np.ones((ncells, ngenes, ngenes), dtype=np.uint8)
    stats = {"precision": [], "recall": [], "density": []}
    upper = np.triu_indices(ngenes, k=1)
    for i in range(ncells):
        if args.region_tf == "per-cell":
            region_tf = (region_gene.astype(np.int32) @ (geff[i] > 0).astype(np.int32)) > 0
        else:
            region_tf = region_tf_global
        region_tf = region_tf | region_tf_noise
        open_i = is_open[i]
        prior_gene_tf = (region_gene_noisy[open_i].T.astype(np.int32) @ region_tf[open_i].astype(np.int32)) > 0
        prior = np.zeros((ngenes, ngenes), dtype=bool)
        prior[:, regulators] = prior_gene_tf
        prior = prior | prior.T
        masks_atac[i] = ~prior

        p, t = prior[upper], graph_gt[i][upper] != 0
        stats["precision"].append((p & t).sum() / max(p.sum(), 1))
        stats["recall"].append((p & t).sum() / max(t.sum(), 1))
        stats["density"].append(p.mean())

    # TF prior (Scenario 1), as in upstream test_scmultisim.py: only target-target edges masked
    mask_tf = np.ones((ngenes, ngenes), dtype=np.uint8)
    mask_tf[regulators, :] = 0
    mask_tf[:, regulators] = 0
    masks_tf = np.repeat(mask_tf[None], ncells, axis=0)

    np.save(os.path.join(args.out, "counts_rna_true.npy"), counts)
    np.save(os.path.join(args.out, "graph_gt.npy"), graph_gt)
    np.save(os.path.join(args.out, "masks_atac.npy"), masks_atac)
    np.save(os.path.join(args.out, "masks_tf.npy"), masks_tf)
    shutil.copyfile(os.path.join(args.raw, "meta_cells.tsv"), os.path.join(args.out, "meta_cells.tsv"))

    summary = {k: float(np.mean(v)) for k, v in stats.items()}
    summary.update(vars(args))
    with open(os.path.join(args.out, "prior_stats.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("ATAC prior vs ground truth (mean over cells):", {k: round(summary[k], 3) for k in stats})


if __name__ == "__main__":
    main()
