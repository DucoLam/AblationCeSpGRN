"""Score candidate prior rules (which regions count as open, where noise goes) on one simulation, every 8th cell.

Usage (from the repo root): python ablation/tools/probe_prior_rules.py [raw_dir/] [full|short]

Openness: "atac>0" (current), "window q" (open in at least a fraction q of the 51 cells around it on
the same branch, ordered by pseudotime), "all" (every region open; upper bound).
Noise: "none", "rg+rt" (current: false links in region x gene and region x TF), "rg" (false links in region x gene
only, as the paper's Fig. 2 caption reads), "rg both ways" (region x gene links also dropped with prob fp).
"""
import sys

import numpy as np
import pandas as pd

sys.path[:0] = ["src", "ablation/lib"]
import bmk

raw = sys.argv[1] if len(sys.argv) > 1 else "ablation/data/scMultiSim/raw/cells8000_seed0/"
atac = pd.read_csv(raw + "counts_atac_true.tsv", sep="\t", index_col=0).T.values
meta = pd.read_csv(raw + "meta_cells.tsv", sep="\t")
rg = pd.read_csv(raw + "region_to_gene.tsv", sep="\t", header=None).values > 0
regulators = pd.read_csv(raw + "regulators.tsv", sep="\t")["regulator"].values - 1
edges = pd.read_csv(raw + "grn_edges.tsv", sep="\t")

ncells, nregions = atac.shape
ngenes, nregs = rg.shape[1], len(regulators)
reg_col = {g: k for k, g in enumerate(regulators)}
geff = np.zeros((ncells, ngenes, nregs), dtype=np.float32)
geff[edges["cell"].values - 1, edges["target"].values - 1,
     [reg_col[r] for r in edges["regulator"].values - 1]] = edges["weight"].values

cells = np.arange(0, ncells, 8)
gt = np.zeros((len(cells), ngenes, ngenes), dtype=np.float32)
gt[:, :, regulators] = geff[cells]
gt = gt + gt.transpose(0, 2, 1)
upper = np.triu_indices(ngenes, k=1)

# Fraction of the 51 neighbouring cells (same branch, by pseudotime) in which each region has reads
is_open = (atac > 0).astype(np.float32)
open_frac = np.zeros_like(is_open)
for _, idx in meta.groupby("pop").groups.items():
    idx = np.asarray(idx)[np.argsort(meta.loc[idx, "depth"].values)]
    c = np.vstack([np.zeros((1, nregions)), np.cumsum(is_open[idx], axis=0)])
    lo = np.clip(np.arange(len(idx)) - 25, 0, len(idx))
    hi = np.clip(np.arange(len(idx)) + 26, 0, len(idx))
    open_frac[idx] = (c[hi] - c[lo]) / (hi - lo)[:, None]


def score(open_rule, noise, fp):
    rng = np.random.default_rng([0, round(fp * 1e6)])
    rg_n = rg | (rng.random(rg.shape) < fp) if noise != "none" else rg
    rt_noise = rng.random((nregions, nregs)) < fp
    if noise == "rg both ways":
        rg_n = np.where(rg, rng.random(rg.shape) >= fp, rg_n)
    pr = np.zeros((len(cells), ngenes, ngenes), dtype=np.float32)
    for k, i in enumerate(cells):
        rt = (rg.astype(np.int32) @ (geff[i] > 0).astype(np.int32)) > 0
        if noise == "rg+rt":
            rt = rt | rt_noise
        if open_rule == "atac>0":
            op = is_open[i] > 0
        elif open_rule == "all":
            op = np.ones(nregions, bool)
        else:
            op = open_frac[i] >= float(open_rule.split()[1])
        p = np.zeros((ngenes, ngenes), bool)
        p[:, regulators] = (rg_n[op].T.astype(np.int32) @ rt[op].astype(np.int32)) > 0
        pr[k] = p | p.T
    p, t = pr[:, upper[0], upper[1]] > 0, gt[:, upper[0], upper[1]] != 0
    s = bmk.calc_scores_para(pr, gt, njobs=4)
    return {"open": open_rule, "noise": noise, "fp": fp,
            "open regions": float(np.mean([(is_open[i] > 0).mean() if open_rule == "atac>0" else 1.0 if open_rule == "all"
                                           else (open_frac[i] >= float(open_rule.split()[1])).mean() for i in cells])),
            "precision": (p & t).sum() / max(p.sum(), 1), "recall": (p & t).sum() / t.sum(),
            "AUPRC": s["AUPRC (abs)"].mean(), "EP": s["Early Precision (abs)"].mean()}


rows = []
grid = sys.argv[2] if len(sys.argv) > 2 else "full"
for fp in [0.01, 0.1]:
    for noise in ["none", "rg+rt", "rg", "rg both ways"] if grid == "full" else ["none", "rg+rt", "rg"]:
        for open_rule in ["atac>0", "window 0.1", "window 0.3", "window 0.5", "all"] if grid == "full" else ["atac>0", "all"]:
            rows.append(score(open_rule, noise, fp))
            print(rows[-1], flush=True)

print(pd.DataFrame(rows).round(3).to_string(index=False))
