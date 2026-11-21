# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""
Infographic for research.md: how the authors' simulate_scmultisim.R builds the ground truth and the prior.
Edges per cell (gene pairs, mean over cells) on the 400-cell check: seed 0, noise 0.01, scMultiSim 1.0.0 at
8dc531f (journal.md, 2026-11-21). Numbers from graph_gt.npy, masks_atac.npy and raw grn_edges.tsv.

Usage (from the repo root): uv run ablation/plots/authors_ground_truth.py [output dir]
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

out_dir = sys.argv[1] if len(sys.argv) > 1 else "ablation/figures"
FULL, KEPT, PRIOR = 145.0, 33.5, 46.8        # simulator's network, filtered ground truth, prior
OPEN, NOISE, CLOSED = "#2a78d6", "#eb6834", "#d5d4ce"
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

rows = [
    ("The simulator's network", "what the RNA was generated from", [(KEPT, OPEN), (FULL - KEPT, CLOSED)]),
    ("The benchmark's ground truth", "what every method is scored against", [(KEPT, OPEN)]),
    ("The ATAC prior", "what CeSpGRN is given", [(KEPT, OPEN), (PRIOR - KEPT, NOISE)]),
]

fig, ax = plt.subplots(figsize=(12, 4.3), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
height, gap = 0.5, 0.9
for i, (name, sub, segments) in enumerate(rows):
    y = -i
    left = 0.0
    for width, color in segments:
        ax.add_patch(FancyBboxPatch((left + gap / 2, y - height / 2), width - gap, height,
                                    boxstyle="round,pad=0,rounding_size=0.12", mutation_aspect=0.02,
                                    facecolor=color, edgecolor="none"))
        left += width
    ax.text(-3, y + 0.08, name, ha="right", va="center", fontsize=12.5, color=INK, fontweight="bold")
    ax.text(-3, y - 0.2, sub, ha="right", va="center", fontsize=10, color=MUTED)

# the removed edges, as an empty outline in the ground-truth row
ax.add_patch(FancyBboxPatch((KEPT + gap / 2, -1 - height / 2), FULL - KEPT - gap, height,
                            boxstyle="round,pad=0,rounding_size=0.12", mutation_aspect=0.02,
                            facecolor="none", edgecolor="#a9a8a1", linestyle=(0, (4, 3)), linewidth=1.2))

label = dict(va="center", fontsize=11, color=INK)
ax.text(KEPT / 2, 0, "33.5", ha="center", color="white", va="center", fontsize=11, fontweight="bold")
ax.text(KEPT + (FULL - KEPT) / 2, 0, "111.5 edges behind a closed region", ha="center", **label)
ax.text(KEPT / 2, -1, "33.5", ha="center", color="white", va="center", fontsize=11, fontweight="bold")
ax.text(KEPT + (FULL - KEPT) / 2, -1, "removed: counted as false, although still in the RNA", ha="center",
        va="center", fontsize=11, color=MUTED)
ax.text(KEPT / 2, -2, "33.5", ha="center", color="white", va="center", fontsize=11, fontweight="bold")
ax.text(PRIOR + 1.5, -2, "+ 13.3 random edges added as noise (level 0.01)", ha="left", **label)

ax.set_xlim(-64, FULL + 1)
ax.set_ylim(-2.75, 0.5)
ax.axis("off")
ax.legend(handles=[Patch(color=OPEN, label="True edge through an open region"),
                   Patch(color=CLOSED, label="True edge behind a closed region"),
                   Patch(color=NOISE, label="Edge added as noise")],
          loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=False, fontsize=10.5,
          handlelength=1.2, columnspacing=2.2)
fig.suptitle("The benchmark's ground truth is the prior without its noise", x=0.02, ha="left",
             fontsize=15, fontweight="bold", color=INK)
fig.text(0.02, 0.885, "TF–gene edges per cell, mean over 400 simulated cells, built with the authors' script",
         fontsize=10.5, color=MUTED)
fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.04)
os.makedirs(out_dir, exist_ok=True)
fig.savefig(os.path.join(out_dir, "authors_ground_truth.png"), dpi=170, facecolor=SURFACE)
print("wrote authors_ground_truth.png")
