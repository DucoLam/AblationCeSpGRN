# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib"]
# ///
"""
Step-by-step diagram for research.md: what the authors' simulate_scmultisim.R does for one cell, on a toy
network (2 TFs, 4 genes), and where it goes wrong. Schematic, not drawn from data.

Usage (from the repo root): uv run ablation/plots/authors_steps.py [output dir]
"""
import os
import sys
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

out_dir = sys.argv[1] if len(sys.argv) > 1 else "ablation/figures"
TRUE, NOISE, GREY, LINE = "#2a78d6", "#eb6834", "#a9a8a1", "#d5d4ce"
INK, MUTED, SURFACE, BOX = "#0b0b0b", "#52514e", "#fcfcfb", "#f1f0ec"

TFS = {"A": (1.0, 2.0), "B": (3.0, 2.0)}
GENES = {"g1": (0.4, 0.5), "g2": (1.6, 0.5), "g3": (2.4, 0.5), "g4": (3.6, 0.5)}
EDGES = [("A", "g1"), ("A", "g2"), ("B", "g3"), ("B", "g4")]
CLOSED = {"g2", "g4"}

# per step: title, edges as (tf, gene, style), whether the open/closed regions are shown, caption
STEPS = [
    ("1  Simulate a cell", [(t, g, "true") for t, g in EDGES], False,
     "The simulator gives each cell a true network. The cell's RNA is generated from all of its edges."),
    ("2  Look at the chromatin", [(t, g, "true") for t, g in EDGES], True,
     "In each cell most regions are closed (80%). Here the regions of g2 and g4 are closed."),
    ("3  Rewrite the ground truth", [(t, g, "gone" if g in CLOSED else "true") for t, g in EDGES], True,
     "Every true edge behind a closed region is deleted. What is left is saved as the ground truth."),
    ("4  Build the prior", [("A", "g1", "true"), ("B", "g3", "true"), ("A", "g3", "noise")], True,
     "The prior is that same set of edges, plus a few random ones as noise. CeSpGRN gets this as input."),
]
PROBLEMS = [
    (2, "The RNA still follows the deleted edges",
     "A method that finds A → g2 in the RNA is right about the cell, but is scored as wrong."),
    (3, "The prior is made from the answer",
     "It contains every edge of the ground truth, always. Only the noise separates the two."),
]
CONCLUSION = ("Result: a method that hands back its prior finds every true edge without looking at the RNA, "
              "and a method that reads the RNA correctly is marked wrong for the deleted edges.")

fig = plt.figure(figsize=(15, 7.6), facecolor=SURFACE)
W = 0.225
for k, (title, edges, show_regions, caption) in enumerate(STEPS):
    ax = fig.add_axes([0.02 + k * 0.245, 0.515, W, 0.36])
    ax.set_xlim(-0.2, 4.2)
    ax.set_ylim(-0.3, 2.4)
    ax.set_aspect("equal")
    ax.axis("off")
    for tf, gene, style in edges:
        (x0, y0), (x1, y1) = TFS[tf], GENES[gene]
        props = {"true": dict(color=TRUE, lw=2.6), "noise": dict(color=NOISE, lw=2.6),
                 "gone": dict(color=GREY, lw=1.6, linestyle=(0, (3, 3)))}[style]
        ax.add_patch(FancyArrowPatch((x0, y0 - 0.27), (x1, y1 + 0.27), arrowstyle="-|>", mutation_scale=14,
                                     shrinkA=0, shrinkB=0, zorder=1, **props))
        if style == "gone":
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, "✕", ha="center", va="center", fontsize=13, color=INK,
                    zorder=3, bbox=dict(boxstyle="circle,pad=0.08", facecolor=SURFACE, edgecolor="none"))
    for name, (x, y) in TFS.items():
        ax.add_patch(FancyBboxPatch((x - 0.25, y - 0.25), 0.5, 0.5, boxstyle="round,pad=0,rounding_size=0.08",
                                    facecolor=INK, edgecolor="none", zorder=2))
        ax.text(x, y, f"TF {name}", ha="center", va="center", color="white", fontsize=9, fontweight="bold", zorder=3)
    for name, (x, y) in GENES.items():
        closed = show_regions and name in CLOSED
        ax.add_patch(Circle((x, y), 0.27, facecolor=SURFACE, edgecolor=GREY if closed else INK, lw=1.6, zorder=2))
        ax.text(x, y, name, ha="center", va="center", fontsize=10, color=MUTED if closed else INK, zorder=3)
        if show_regions:
            ax.text(x, y - 0.5, "closed" if closed else "open", ha="center", va="center", fontsize=9,
                    color=MUTED if closed else INK, fontweight="normal" if closed else "bold")
    fig.text(0.02 + k * 0.245, 0.885, title, fontsize=13.5, fontweight="bold", color=INK)
    fig.text(0.02 + k * 0.245, 0.475, textwrap.fill(caption, 38), fontsize=10.5, color=MUTED, va="top", linespacing=1.35)
    if k < len(STEPS) - 1:
        fig.patches.append(FancyArrowPatch((0.02 + k * 0.245 + W + 0.002, 0.68), (0.02 + (k + 1) * 0.245 - 0.004, 0.68),
                                           transform=fig.transFigure, arrowstyle="-|>", mutation_scale=16, color=GREY, lw=1.4))

fig.text(0.02, 0.305, "Why this is a problem", fontsize=13.5, fontweight="bold", color=INK)
for k, heading, text in PROBLEMS:
    x = 0.02 + k * 0.245
    fig.patches.append(FancyBboxPatch((x - 0.008, 0.135), W + 0.008, 0.145, transform=fig.transFigure,
                                      boxstyle="round,pad=0,rounding_size=0.008", facecolor=BOX, edgecolor="none"))
    fig.text(x + 0.002, 0.262, heading, fontsize=11, fontweight="bold", color=INK, va="top")
    fig.text(x + 0.002, 0.232, textwrap.fill(text, 40), fontsize=10.5, color=INK, va="top", linespacing=1.35)
fig.text(0.02, 0.262, textwrap.fill("Steps 3 and 4 use the same rule. The ground truth and the prior are built "
                                    "from the same edges, and the paper describes only step 4.", 62),
         fontsize=10.5, color=INK, va="top", linespacing=1.35)
fig.patches.append(FancyBboxPatch((0.012, 0.03), 0.976, 0.075, transform=fig.transFigure,
                                  boxstyle="round,pad=0,rounding_size=0.008", facecolor=INK, edgecolor="none"))
fig.text(0.5, 0.0675, textwrap.fill(CONCLUSION, 150), fontsize=11, color="white", ha="center", va="center", linespacing=1.35)

# legend
for i, (color, label, style) in enumerate([(TRUE, "True edge", "-"), (GREY, "True edge, deleted from the ground truth", (0, (3, 3))),
                                           (NOISE, "False edge added as noise", "-")]):
    x = 0.44 + [0, 0.10, 0.34][i]
    fig.lines.append(plt.Line2D([x, x + 0.025], [0.955, 0.955], transform=fig.transFigure, color=color, lw=2.6, linestyle=style))
    fig.text(x + 0.031, 0.955, label, fontsize=10.5, color=INK, va="center")
fig.text(0.02, 0.945, "What the benchmark script does, for one cell", fontsize=16, fontweight="bold", color=INK)

os.makedirs(out_dir, exist_ok=True)
fig.savefig(os.path.join(out_dir, "authors_steps.png"), dpi=160, facecolor=SURFACE)
print("wrote authors_steps.png")
