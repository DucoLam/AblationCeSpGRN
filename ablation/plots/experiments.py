# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "numpy", "matplotlib", "seaborn>=0.13"]
# ///
"""
Figures for the CPU experiments (6_cpu_experiments.py), in the same style as upstream's Fig. 2b
(seaborn barplots, Set2, mean over cells with SD error bars, value labels).

    exp4_penalty_vs_cut.png   experiment 4: penalty and cut switched on and off separately
    exp6_inside_prior.png     experiment 6: ranking of the edges inside the prior vs a random order
    exp8_standard_auprc.png   experiment 8: the paper's AUPRC next to standard AUPRC
    exp5_worse_priors.png     experiment 5: CeSpGRN and its prior alone, for the real and three worse priors

Reads <results>/<dataset>/cpu/exp<N>_scores.csv and, for experiment 5,
<results>/followup_seed0_pz0.2_links/priors/cpu_<prior>/exp8_scores.csv (copied from DAIC).
Usage (from the repo root): uv run ablation/plots/experiments.py [results dir] [output dir]
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

results = sys.argv[1] if len(sys.argv) > 1 else "ablation/results/scmultisim"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "ablation/figures"
MAIN = "simulated_8000_20_10_100_0.01_0_0_4_pz0.2_links"
DEFAULT = "simulated_8000_20_10_100_0.01_0_0_4_links"
METRICS = {"AUPRC (abs)": "Paper's AUPRC", "AUPRC (standard)": "Standard AUPRC"}


def load(dataset, exp):
    return pd.read_csv(os.path.join(results, dataset, "cpu", f"exp{exp}_scores.csv"), index_col=0)


def by_metric(scores, names):
    scores = scores[scores["model"].isin(names)].replace({"model": names})
    long = scores.melt(id_vars="model", value_vars=list(METRICS), var_name="metric", value_name="score")
    return long.replace({"metric": METRICS})


def barplot(ax, data, x, y, hue, order):
    # upstream eval_scores_new.py style
    bars = sns.barplot(data, x=x, y=y, hue=hue, ax=ax, order=order, palette="Set2", estimator=np.mean,
                       errorbar="sd", capsize=0.1, err_kws={"color": "blue", "linewidth": 2, "linestyle": "--"})
    for c in bars.containers:
        bars.bar_label(c, fmt="%.3f")
    ax.set_xlabel(None)
    ax.set_xticks(ax.get_xticks(), ax.get_xticklabels(), rotation=30, ha="right", fontsize=17)


def finish(fig, ax, title, path, legend_title=None):
    if ax.get_legend() is not None:
        ax.legend(loc="upper left", prop={"size": 16}, frameon=False, bbox_to_anchor=(1.02, 1), title=legend_title, title_fontsize=16)
    fig.suptitle(title, fontsize=22)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


sns.set_theme(font_scale=1.5)
os.makedirs(out_dir, exist_ok=True)

# Experiment 4
names = {"Neither (beta 0)": "Neither", "Penalty only": "Penalty only", "Cut only": "Cut only",
         "Penalty + cut (paper)": "Penalty + cut"}
fig, ax = plt.subplots(figsize=(12, 6.5))
barplot(ax, by_metric(load(MAIN, 4), names), "model", "score", "metric", list(names.values()))
ax.set_ylabel("Score")
finish(fig, ax, "Penalty or cut: which one does the work?", os.path.join(out_dir, "exp4_penalty_vs_cut.png"))

# Experiment 6
scores = load(MAIN, 6)
base = scores[scores["model"] == "CeSpGRN (paper)"].assign(**{"model": "Random order", "AUPRC inside prior": lambda d: d["Share true inside prior (baseline)"]})
names = {"CeSpGRN (paper)": "CeSpGRN", "RNA only (beta 0)": "CeSpGRN without prior", "Random order": "Random order"}
data = pd.concat([scores, base])
data = data[data["model"].isin(names)].replace({"model": names})
fig, ax = plt.subplots(figsize=(10, 6.5))
barplot(ax, data, "model", "AUPRC inside prior", None, list(names.values()))
ax.set_ylabel("Standard AUPRC, inside the prior")
ax.set_ylim(0, 1.0)
finish(fig, ax, "Ordering the edges the prior allows", os.path.join(out_dir, "exp6_inside_prior.png"))

# Experiment 8
names = {"CeSpGRN (ATAC)": "CeSpGRN", "Prior (ATAC)": "Prior alone"}
fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), sharey=True)
for ax, (dataset, label) in zip(axes, [(MAIN, "More open chromatin (main)"), (DEFAULT, "Default chromatin")]):
    barplot(ax, by_metric(load(dataset, 8), names), "model", "score", "metric", list(names.values()))
    ax.set_title(label, fontsize=17)
    ax.set_ylabel("Score")
axes[0].get_legend().remove()
finish(fig, axes[1], "The paper's AUPRC vs standard AUPRC", os.path.join(out_dir, "exp8_standard_auprc.png"))

# Experiment 5
priors = {"atac": "Real per cell", "noise0.3": "Noisier (0.3)", "shared": "Shared by all cells", "random": "Random"}
frames = []
for prior, label in priors.items():
    scores = load(MAIN, 8) if prior == "atac" else pd.read_csv(
        os.path.join(results, "followup_seed0_pz0.2_links", "priors", f"cpu_{prior}", "exp8_scores.csv"), index_col=0)
    network = {f"CeSpGRN ({prior.upper()})": "CeSpGRN", f"Prior ({prior.upper()})": "Prior alone"}
    frames.append(scores[scores["model"].isin(network)].replace({"model": network}).assign(prior=label))
data = pd.concat(frames, ignore_index=True)
fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), sharey=True)
for ax, (metric, label) in zip(axes, METRICS.items()):
    barplot(ax, data, "prior", metric, "model", list(priors.values()))
    ax.set_title(label, fontsize=17)
    ax.set_ylabel("Score")
axes[0].get_legend().remove()
finish(fig, axes[1], "CeSpGRN follows whatever prior it gets", os.path.join(out_dir, "exp5_worse_priors.png"))
print("wrote", sorted(f for f in os.listdir(out_dir) if f.startswith("exp")))
