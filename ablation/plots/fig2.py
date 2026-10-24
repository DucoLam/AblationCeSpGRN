# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "numpy", "matplotlib", "seaborn>=0.13"]
# ///
"""
Our versions of the paper's simulated-benchmark figures, drawn with upstream's own plotting code
(test/scripts_scmultisim/eval_scores_new.py: barplots for Fig. 2b, boxplots for Fig. S3c), so they
look the same. We add the ATAC prior on its own next to CeSpGRN; we don't run the other methods.

    fig2b_reproduction.png  Fig. 2b: 3 seeds x noise 0.01 / 0.1, our first (per-entry noise) prior
    figS3c_beta.png         Fig. S3c: CeSpGRN with and without the prior (β = 0), same datasets
    fig2b_rebuilt.png       Fig. 2b on the rebuilt prior (links noise), seed 0, noise 0.01,
                            default (atac.p_zero 0.8) and more open chromatin (0.2)

Reads <results>/<dataset>/{beta_1_atac,beta_0}/scores.csv (copied from DAIC; the container has no seaborn).
Usage (from the repo root): uv run ablation/plots/fig2.py [results dir] [output dir]
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

results = sys.argv[1] if len(sys.argv) > 1 else "ablation/results/scmultisim"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "ablation/figures"
os.makedirs(out_dir, exist_ok=True)


def load(dataset, run, **columns):
    scores = pd.read_csv(os.path.join(results, dataset, run, "scores.csv"), index_col=0)
    return scores.assign(**columns)


def bars(scores, order, hue, legend_title, path, title="Inference accuracy (scATAC-seq)"):
    # upstream eval_scores_new.py, "scores with scATAC-seq data" (Fig. 2b)
    sns.set_theme(font_scale=1.7)
    plt.rcParams["font.size"] = 17
    fig = plt.figure(figsize=(15, 7))
    ax = fig.subplots(nrows=1, ncols=2)
    error_bar = "sd"
    bar1 = sns.barplot(scores, x="model", y="AUPRC (abs)", hue=hue, ax=ax[0], order=order, palette="Set2",
                       estimator=np.mean, errorbar=error_bar, capsize=0.1,
                       err_kws={"color": "blue", "linewidth": 2, "linestyle": "--"})
    bar2 = sns.barplot(scores, x="model", y="Early Precision (abs)", hue=hue, ax=ax[1], order=order, palette="Set2",
                       estimator=np.mean, errorbar=error_bar, capsize=0.1,
                       err_kws={"color": "blue", "linewidth": 2, "linestyle": "--"})
    for i in bar1.containers:
        bar1.bar_label(i, fmt="%.3f")
    for i in bar2.containers:
        bar2.bar_label(i, fmt="%.3f")

    _ = ax[0].set_xticks(ax[0].get_xticks(), ax[0].get_xticklabels(), rotation=45, fontsize=20)
    _ = ax[1].set_xticks(ax[1].get_xticks(), ax[1].get_xticklabels(), rotation=45, fontsize=20)
    ax[0].get_legend().remove()
    ax[0].set_xlabel(None)
    ax[0].set_ylabel("AUPRC", fontsize=20)
    ax[1].set_xlabel(None)
    ax[1].set_ylabel("Eprec", fontsize=20)
    ax[1].legend(loc="upper left", prop={"size": 20}, frameon=False, ncol=1, bbox_to_anchor=(1.04, 1),
                 markerscale=6, title=legend_title, title_fontsize=20)
    fig.suptitle(title, fontsize=26)
    plt.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)


# Fig. 2b: 3 seeds x 2 noise levels, first prior
first = pd.concat([load(f"simulated_8000_20_10_100_{fp}_{seed}_0_4", "beta_1_atac", fp=fp)
                   for fp in [0.01, 0.1] for seed in [0, 1, 2]], ignore_index=True)
bars(first, ["CeSpGRN (ATAC)", "Prior (ATAC)"], "fp", "Noise level", os.path.join(out_dir, "fig2b_reproduction.png"))

# Fig. S3c: β ablation, upstream's boxplot
beta = pd.concat([load(f"simulated_8000_20_10_100_{fp}_{seed}_0_4", run, fp=fp)
                  for fp in [0.01, 0.1] for seed in [0, 1, 2] for run in ["beta_0", "beta_1_atac"]], ignore_index=True)
beta = beta[beta["model"].isin(["CeSpGRN (w/o beta)", "CeSpGRN (ATAC)"])].replace({"model": {"CeSpGRN (ATAC)": "CeSpGRN"}})
sns.set_theme(font_scale=1.2)
fig = plt.figure(figsize=(15, 7))
ax = fig.subplots(nrows=1, ncols=2)
sns.boxplot(beta, x="model", y="AUPRC (abs)", hue="fp", ax=ax[0], width=0.5, palette="Set2")
sns.boxplot(beta, x="model", y="Early Precision (abs)", hue="fp", ax=ax[1], width=0.5, palette="Set2")
_ = ax[0].set_xticks(ax[0].get_xticks(), ax[0].get_xticklabels(), rotation=45, fontsize=20)
_ = ax[1].set_xticks(ax[1].get_xticks(), ax[1].get_xticklabels(), rotation=45, fontsize=20)
ax[0].get_legend().remove()
ax[0].set_xlabel(None)
ax[0].set_ylabel("AUPRC", fontsize=20)
ax[1].set_xlabel(None)
ax[1].set_ylabel("Eprec", fontsize=20)
ax[1].legend(loc="upper left", prop={"size": 20}, frameon=False, ncol=1, bbox_to_anchor=(1.04, 1),
             markerscale=6, title="Noise level", title_fontsize=20)
plt.tight_layout()
fig.savefig(os.path.join(out_dir, "figS3c_beta.png"), bbox_inches="tight", dpi=150)
plt.close(fig)

# Fig. 2b on the rebuilt prior: seed 0, noise 0.01, two chromatin settings
rebuilt = pd.concat([load(f"simulated_8000_20_10_100_0.01_0_0_4{suffix}", "beta_1_atac", chromatin=label)
                     for suffix, label in [("_links", "default (0.8)"), ("_pz0.2_links", "more open (0.2)")]],
                    ignore_index=True)
bars(rebuilt, ["CeSpGRN (ATAC)", "Prior (ATAC)"], "chromatin", "atac.p_zero", os.path.join(out_dir, "fig2b_rebuilt.png"),
     title="Inference accuracy (scATAC-seq), rebuilt prior, noise 0.01")
print("wrote", sorted(os.listdir(out_dir)))
