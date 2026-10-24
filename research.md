# Does CeSpGRN learn from RNA, or copy its prior?

CeSpGRN infers a gene regulatory network (GRN) for every single cell from RNA data. With scATAC-seq it also gets a **prior**: per cell, the set of TF → gene edges that the cell's open chromatin allows. On the paper's simulated benchmark this prior lifts accuracy (AUPRC) from about 0 to 0.76.

We ask where that gain comes from: does CeSpGRN learn the network from the RNA, or does it mostly hand back the prior it was given?

Paper: Zhang et al., *Bioinformatics* 42(6), btag324 (2026). Code: [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN) `v1.0.0`. The detailed log, with dates, job IDs and code references, is in [`journal.md`](journal.md).

## How CeSpGRN works, in short

- **Input:** gene expression (RNA) for every cell, and per cell a **prior**: the TF → gene links that the cell's open chromatin (ATAC) allows.
- **Method:** for each cell, CeSpGRN estimates a network from the RNA of that cell and its neighbours (cells with similar expression). A penalty with weight β pushes it away from edges outside the prior.
- **A step the paper doesn't mention:** after solving, the code sets every edge outside the prior to zero. So the output can only contain edges the prior allows.
- **Output:** the average of 16 runs (4 neighbourhood bandwidths × 4 sparsity levels), one network per cell.

**How we score**, per cell against the true network, then averaged over cells:
- **AUPRC:** overall accuracy of the edge ranking. 1 is perfect, random is about 0.02 here. We use the paper's own version, which rewards tied scores (see finding 6).
- **Early precision:** of the top edges (as many as there are true edges), the share that is true.

## Main result

**CeSpGRN does not beat the prior it is given.** On our rebuild of the paper's benchmark, the ATAC prior on its own scores at least as well as CeSpGRN with that prior. Drawn with the authors' own plotting code (Fig. 2b), with the prior added next to CeSpGRN:

![Fig. 2b on the rebuilt prior](ablation/figures/fig2b_rebuilt.png)

| 8000 cells, noise 0.01 | AUPRC | Early precision |
|---|---|---|
| CeSpGRN with ATAC prior | 0.66 | 0.74 |
| ATAC prior alone | 0.72 | 0.74 |
| CeSpGRN without prior | 0.02 | 0.01 |
| *Paper: CeSpGRN with ATAC prior* | *0.76* | *0.69* |

This is the setting closest to the paper (more open chromatin, see [Setup](#setup)). With the simulator's default chromatin, which gives a weaker prior, the picture is the same: CeSpGRN 0.47 / 0.71, the prior alone 0.47 / 0.71. Without the prior CeSpGRN is close to random, as in the paper. So far this is one seed at noise 0.01.

## What else we found

1. **The prior is a hard filter, not only a penalty.** The paper describes a soft penalty (weight β) on edges outside the prior. The code also sets every edge outside the prior to zero after solving, so CeSpGRN can only ever report edges the prior allows.
2. **The paper's β experiment cannot separate penalty from filter.** In the code, "without β" means "without any prior", and any β above zero switches the filter on. That explains why accuracy barely moves when β goes from 0.01 to 100.
3. **The simulated prior is built from the true network.** The simulator links a TF to a chromatin region only if that TF truly regulates a gene next to the region. The prior therefore contains the answer; chromatin only decides which of those edges are closed in each cell.
4. **The authors scored the prior on its own, but did not report it.** Their evaluation code computes it; it is missing from the paper and supplement.
5. **The benchmark cannot be rebuilt from what is published.** The code that builds the priors and adds noise is not public, and two unstated choices change the prior's quality a lot: how noise is added and how much chromatin is open. We have asked the authors for their settings.
6. **The AUPRC used in the paper flatters tied scores.** It draws a straight line from the start of the curve to the first real point, so a plain yes/no prediction scores roughly (1 + precision) / 2. Priors, and CeSpGRN after the filter, are full of ties. We keep this metric for now so our numbers compare with the paper's.
7. **Single settings may tell a different story than the average.** The paper averages CeSpGRN over 16 settings (4 bandwidths × 4 sparsity levels λ). In a small test (400 cells), no single setting beats the prior's AUPRC, but some rank the prior's edges better: early precision up to 0.93 against the prior's 0.81. So within the prior, the RNA may help pick out the true edges, and averaging hides it. The full-size runs now score every setting to check this.

## Plan

Everything runs on one dataset: 8000 cells, seed 0, noise 0.01, more open chromatin. We add seeds only if a result is borderline. Experiments 3 and 5 share one GPU job; the rest reuse experiment 1's saved results and run on CPU.

| # | Experiment | Compute | Status |
|---|---|---|---|
| 1 | Reproduce Fig. 2b on our rebuilt benchmark | GPU | done |
| 2 | Score the ATAC prior alone, without RNA | CPU | done |
| 3 | Remove the RNA signal: run CeSpGRN on shuffled RNA | GPU | queued |
| 4 | Test the soft penalty and the hard filter separately (2 × 2) | CPU | planned |
| 5 | Give CeSpGRN worse priors: a random prior of the same density, one prior shared by all cells, and noise 0.3 | GPU | queued |
| 6 | Score only edges inside the prior, to see what the RNA adds | CPU | planned |
| 7 | Give plain correlation the same prior and filter | CPU | planned |
| 8 | Rescore everything with standard AUPRC | CPU | planned |

Dropped for now: the β sweep (the paper's Fig. S4a already shows it is flat), GENIE3 as a second baseline (only if experiment 7 is unclear), and noise 0.1.

## Setup

- **Data.** Simulated with scMultiSim using the settings encoded in the authors' dataset names, giving the paper's 110 genes and 330 regions. Where the paper is silent we chose: the simulator's example tree and 20 cell identity factors; a region counts as open when it has any ATAC reads; noise moves a share of the real region–gene links to wrong pairs (the paper calls it an "error rate" of that association).
- **More open chromatin.** By default the simulator makes 80% of ATAC values zero, which leaves most true edges outside the prior. We use 20% zeros, because that gives a prior as strong as the paper's scores imply. We picked it to match the paper, so the default is kept as a check.
- **A first rebuild** used the simulator's defaults and added noise to every empty entry, which at 0.01 already tripled the region–gene links. Its prior was much weaker (AUPRC 0.37) but gave the same conclusion. Details in [`journal.md`](journal.md).
- **Method and scoring.** The authors' own CeSpGRN code, settings and metrics; see the table below.
- **Code.** Everything we wrote is in [`ablation/`](ablation/README.md).

### How we run CeSpGRN

Exactly the settings of the authors' code and of supplement Note 1.4:

| Setting | Supplement / paper | Authors' script | Ours |
|---|---|---|---|
| Bandwidth σ | 0.01, 0.1, 1, 10 | same | same |
| Sparsity λ | 0.01, 0.05, 0.1, 0.5 | same | same |
| Prior weight β | 1 | 1 | 1 (and 0 for the no-prior run) |
| Neighbourhood size Ni | 100 | 100 | 100 |
| k-NN graph | smallest k > 5 that connects the graph | same | same code |
| Final network | average over all 16 σ × λ | same | same |
| Covariance | neighbourhood-weighted Kendall's τ | module never published | rebuilt from their commented-out code, weighted |
| Solver settings | not stated | α 2, ρ 1.7, 100 iterations, batches of 512 | same |
| Normalisation | not stated | library size + log1p, PCA with 20 components | same |

Where we differ, and why it is safe:

- **The hard cut** is in the code but not in the paper. We follow the code, because that is what produced their numbers.
- **Two speed changes** (see [Changes to upstream code](#changes-to-upstream-code)) give identical scores to four decimals.
- **The two missing modules** (`cov`, `bmk`) are rebuilt from the paper and the authors' commented-out code.
- **The data and the prior** are rebuilt, because the code that made them is not published (see above).

## Changes to upstream code

- **Compatibility fixes** for functions removed from PyTorch, scikit-learn and NumPy.
- **A speed fix.** As published, the solver takes a matrix square root for one cell at a time, which would take days per dataset at 8000 cells. We compute them for all cells at once. On the small test dataset the scores are identical.

Neither change affects the results. Two helper modules the authors' scripts import were never published; we wrote our own in `ablation/lib/`. Details in [`journal.md`](journal.md#changes-to-upstream-code).
