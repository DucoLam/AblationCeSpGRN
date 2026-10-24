"""Why is our ATAC prior's recall low? Score prior variants on seed 0 (every 8th cell, noise 0.01)."""
import sys

import numpy as np
import pandas as pd

sys.path[:0] = ["src", "ablation/lib"]
import bmk

raw = "ablation/data/scMultiSim/raw/cells8000_seed0/"
counts = pd.read_csv(raw + "counts_rna_true.tsv", sep="\t", index_col=0).T.values
atac = pd.read_csv(raw + "counts_atac_true.tsv", sep="\t", index_col=0).T.values
rg = pd.read_csv(raw + "region_to_gene.tsv", sep="\t", header=None).values > 0
regulators = pd.read_csv(raw + "regulators.tsv", sep="\t")["regulator"].values - 1
edges = pd.read_csv(raw + "grn_edges.tsv", sep="\t")

ncells, ngenes = counts.shape
nregions, nregs = rg.shape[0], len(regulators)
reg_col = {g: k for k, g in enumerate(regulators)}
geff = np.zeros((ncells, ngenes, nregs), dtype=np.float32)
geff[edges["cell"].values - 1, edges["target"].values - 1,
     [reg_col[r] for r in edges["regulator"].values - 1]] = edges["weight"].values

cells = np.arange(0, ncells, 8)
gt = np.zeros((len(cells), ngenes, ngenes), dtype=np.float32)
gt[:, :, regulators] = geff[cells]
gt = gt + gt.transpose(0, 2, 1)

w = edges["weight"].values
print(f"true edges: {len(w)} (cell, edge) pairs, {np.mean(w < 0):.2f} negative")
print(f"regions open per cell: {np.mean(atac > 0):.2f} of {nregions}")
print(f"genes with any linked region: {rg.any(0).mean():.2f}")

rng = np.random.default_rng([0, 10000])
rg_noisy = rg | (rng.random(rg.shape) < 0.01)
rt_noise = rng.random((nregions, nregs)) < 0.01
upper = np.triu_indices(ngenes, k=1)


def prior_for(sign, open_rule, noise):
    out = np.zeros((len(cells), ngenes, ngenes), dtype=np.float32)
    for k, i in enumerate(cells):
        reg = geff[i] > 0 if sign == "positive" else geff[i] != 0
        rt = (rg.astype(np.int32) @ reg.astype(np.int32)) > 0
        rgn = rg_noisy if noise else rg
        if noise:
            rt = rt | rt_noise
        op = atac[i] > 0 if open_rule == "atac>0" else np.ones(nregions, bool)
        p = np.zeros((ngenes, ngenes), bool)
        p[:, regulators] = (rgn[op].T.astype(np.int32) @ rt[op].astype(np.int32)) > 0
        out[k] = p | p.T
    return out


rows = []
for name, args in [
    ("ours: positive edges, open = ATAC > 0, noise 0.01", ("positive", "atac>0", True)),
    ("both signs", ("any", "atac>0", True)),
    ("every region open", ("positive", "all", True)),
    ("both signs, every region open", ("any", "all", True)),
    ("both signs, every region open, no noise", ("any", "all", False)),
]:
    pr = prior_for(*args)
    p, t = pr[:, upper[0], upper[1]] > 0, gt[:, upper[0], upper[1]] != 0
    s = bmk.calc_scores_para(pr, gt, njobs=4)
    rows.append({"prior": name, "precision": (p & t).sum() / p.sum(), "recall": (p & t).sum() / t.sum(),
                 "AUPRC": s["AUPRC (abs)"].mean(), "EP": s["Early Precision (abs)"].mean()})
    print(rows[-1], flush=True)

print(pd.DataFrame(rows).round(3).to_string(index=False))
