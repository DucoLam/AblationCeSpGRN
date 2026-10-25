# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///
"""
Cell-by-cell comparisons quoted in research.md ("higher in x% of cells"): for two networks scored on
the same cells, the mean and SD of the per-cell difference and the share of cells where the first
scores higher. Cells share data through the neighbourhood kernel, so these are not independent samples
and no p-values are given.

Reads the per-cell CSVs copied from DAIC. Usage (from the repo root):
    uv run ablation/tools/paired_differences.py [results dir]
"""
import os
import sys

import pandas as pd

results = sys.argv[1] if len(sys.argv) > 1 else "ablation/results/scmultisim"
main = os.path.join(results, "simulated_8000_20_10_100_0.01_0_0_4_pz0.2_links", "cpu")
shuffled = os.path.join(results, "followup_seed0_pz0.2_links", "shuffledRNA", "cpu")


def scores(path, model):
    df = pd.read_csv(path, index_col=0)
    return df[df["model"] == model].dropna(subset=["AUPRC (abs)"]).set_index("time")


networks = {
    "CeSpGRN": (os.path.join(main, "exp8_scores.csv"), "CeSpGRN (ATAC)"),
    "Prior alone": (os.path.join(main, "exp8_scores.csv"), "Prior (ATAC)"),
    "Shuffled RNA": (os.path.join(shuffled, "exp8_scores.csv"), "CeSpGRN (ATAC)"),
    "Plain correlation + cut": (os.path.join(main, "exp7_scores.csv"), "Correlation + cut"),
    "Per-cell correlation + cut": (os.path.join(main, "exp7_scores.csv"), "Kernel correlation + cut"),
    "Cut only": (os.path.join(main, "exp4_scores.csv"), "Cut only"),
    "Penalty only": (os.path.join(main, "exp4_scores.csv"), "Penalty only"),
    "Neither": (os.path.join(main, "exp4_scores.csv"), "Neither (beta 0)"),
}
loaded = {name: scores(*src) for name, src in networks.items()}
pairs = [("CeSpGRN", "Prior alone"), ("CeSpGRN", "Shuffled RNA"), ("Shuffled RNA", "Prior alone"),
         ("Plain correlation + cut", "CeSpGRN"), ("Per-cell correlation + cut", "CeSpGRN"),
         ("CeSpGRN", "Cut only"), ("Penalty only", "Neither")]
rows = []
for a, b in pairs:
    for metric in ["AUPRC (standard)", "AUPRC (abs)", "Early Precision (abs)"]:
        d = (loaded[a][metric] - loaded[b][metric]).dropna()
        rows.append({"comparison": f"{a} - {b}", "metric": metric, "cells": len(d), "mean": d.mean(),
                     "sd": d.std(), "share higher": (d > 0).mean(), "share tied": (d == 0).mean()})
print(pd.DataFrame(rows).round(4).to_string(index=False))
