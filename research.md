# Does CeSpGRN learn from RNA, or copy its prior?

CeSpGRN infers a gene regulatory network (GRN) for every single cell from RNA data. With scATAC-seq it also gets a **prior**: per cell, the set of TF → gene edges that the cell's open chromatin allows. On the paper's simulated benchmark this prior lifts accuracy (AUPRC) from about 0 to 0.76.

We ask where that gain comes from: does CeSpGRN learn the network from the RNA, or does it mostly hand back the prior it was given?

Paper: Zhang et al., *Bioinformatics* 42(6), btag324 (2026). Code: [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN) `v1.0.0`. The detailed log, with dates, job IDs and code references, is in [`journal.md`](journal.md).

## What we found so far

1. **The prior is a hard filter, not only a penalty.** The paper describes a soft penalty (weight β) on edges outside the prior. The code also sets every edge outside the prior to zero after solving, so CeSpGRN can only ever report edges the prior allows.
2. **The paper's β experiment cannot separate penalty from filter.** In the code, "without β" means "without any prior", and any β above zero switches the filter on. That explains why accuracy barely moves when β goes from 0.01 to 100.
3. **The simulated prior is built from the true network.** The simulator links a TF to a chromatin region only if that TF truly regulates a gene next to the region. The prior therefore contains the answer; chromatin only decides which of those edges are closed in each cell.
4. **The authors scored the prior on its own, but did not report it.** Their evaluation code computes it; it is missing from the paper and supplement.
5. **The benchmark cannot be rebuilt from what is published.** The code that builds the priors and adds noise is not public. We rebuilt it (see [Setup](#setup)); our datasets match the paper's sizes.
6. **The AUPRC used in the paper flatters tied scores.** It draws a straight line from the start of the curve to the first real point, so a plain yes/no prediction scores roughly (1 + precision) / 2. Priors, and CeSpGRN after the filter, are full of ties. We keep this metric for now so our numbers compare with the paper's.
7. **In our rebuild, noise makes the prior larger, not just worse.** See the prior quality table below. How the paper injects noise is not specified, so results at high noise depend heavily on that choice.
8. **On the full benchmark, CeSpGRN does not beat the prior it is given.** But our prior is much weaker than the paper's, so we do not yet reach the paper's scores. See [Results](#results).

## Results

**Reproduction of the paper's main figure** (Fig. 2b): 8000 cells, mean over cells, range over 3 seeds.

| Noise | | AUPRC | Early precision |
|---|---|---|---|
| 0.01 | CeSpGRN with ATAC prior | 0.33 – 0.37 | 0.45 – 0.53 |
| | ATAC prior alone | 0.37 – 0.42 | 0.45 – 0.53 |
| 0.1 | CeSpGRN with ATAC prior | 0.25 – 0.28 | 0.27 – 0.29 |
| | ATAC prior alone | 0.50 – 0.54 | 0.25 – 0.26 |
| either | CeSpGRN without prior | 0.02 – 0.03 | 0.02 – 0.06 |
| 0.01 | *Paper: CeSpGRN with ATAC prior* | *0.76* | *0.69* |
| 0.1 | *Paper: CeSpGRN with ATAC prior* | *0.41* | *0.39* |

At low noise CeSpGRN adds nothing to its prior: its top edges are exactly as accurate as the prior's, and its AUPRC is lower. At high noise, where the prior is mostly wrong, the RNA helps a little with ranking (early precision +0.01 to +0.03). Without the prior CeSpGRN is close to random, as in the paper.

**Why we stay below the paper.** Our prior is much weaker than the authors' must be, for two reasons. Scored on its own (seed 0, 8000 cells):

| How the prior is built | Regions open per cell | Precision | Recall | AUPRC | Early precision |
|---|---|---|---|---|---|
| Ours (simulator defaults, noise 0.01) | 20% | 0.45 | 0.26 | 0.37 | 0.45 |
| Simulator defaults, no noise | 20% | 0.72 | 0.22 | 0.48 | 0.72 |
| More open chromatin, no noise | 50% | 0.73 | 0.58 | 0.66 | 0.73 |
| Much more open chromatin, no noise | 80% | 0.75 | 0.70 | 0.73 | 0.75 |
| *Paper: CeSpGRN (not its prior), noise 0.01* | | | | *0.76* | *0.69* |

- **Our noise is far too strong.** We add each missing region–gene link with probability equal to the noise level. There are only 147 real links among 36,300 possible ones, so noise 0.01 already adds about 360 false links. The paper calls the noise level an "error rate", which more likely means a share of the real links.
- **The simulator's default leaves most chromatin closed.** By default 80% of the simulated ATAC values are zero, so only 20% of regions are open in a cell and the prior misses most true edges. The paper does not say which value it used. Other choices (smoothing openness over neighbouring cells, counting repressing edges) change little.

With little noise and more open chromatin, the prior alone scores about what the paper reports for CeSpGRN. We have asked the authors for their exact settings.

**Rebuilt prior.** We now count noise as a share of the real region–gene links that is wrong, and simulate with more open chromatin. A small test (400 cells, one seed, noise 0.01) lands close to the paper, and CeSpGRN again does not beat its prior:

| | AUPRC | Early precision |
|---|---|---|
| CeSpGRN with rebuilt ATAC prior | 0.74 | 0.81 |
| Rebuilt ATAC prior alone | 0.77 | 0.81 |
| *Paper: CeSpGRN with ATAC prior* | *0.76* | *0.69* |

**Single settings tell a different story than the average.** The paper averages CeSpGRN over 16 settings (4 bandwidths × 4 sparsity levels λ). Scored one by one on the same small test, no single setting beats the prior's AUPRC (best 0.71 vs 0.77). But at larger bandwidths and moderate λ, CeSpGRN's top edges are clearly more accurate than the prior's: early precision 0.87 to 0.93, against 0.81. So within the prior, the RNA does help pick out the true edges, and the paper's averaging hides that. This is from 400 cells and one seed; the full-size runs now score every setting too.

**Full size on the rebuilt prior** (8000 cells, one seed, noise 0.01) confirms it:

| | AUPRC | Early precision |
|---|---|---|
| CeSpGRN with rebuilt ATAC prior | 0.66 | 0.74 |
| Rebuilt ATAC prior alone | 0.72 | 0.74 |
| CeSpGRN without prior | 0.02 | 0.01 |
| *Paper: CeSpGRN with ATAC prior* | *0.76* | *0.69* |

CeSpGRN again scores below its prior on AUPRC and the same on early precision. The run with the default chromatin setting is still going.

**First look at experiments 3 and 5** (small test on the old prior; will be redone on the rebuilt one):

- **Shuffled RNA changes nothing.** With each gene's expression shuffled across cells, so the RNA carries no regulatory signal, CeSpGRN scores the same as with the real RNA (AUPRC 0.37 vs 0.35).
- **A random prior makes it collapse** to near zero (0.03), even with the same number of allowed edges.
- **One prior shared by all cells does slightly better** than the per-cell prior (0.37 vs 0.35), so the cell-specific part of the ATAC data does not help here either.

**Quality of our prior** (range over 3 seeds):

| Noise | Precision | Recall | Share of all edges it allows |
|---|---|---|---|
| 0.01 | 0.45 – 0.53 | 0.24 – 0.30 | 1.1 – 1.5% |
| 0.1 | 0.25 – 0.26 | 0.74 – 0.82 | 7.1 – 7.8% |

More noise lets through about 5 times more edges, which catches about 3 times more true edges at half the precision.

## Plan

After experiment 1, everything runs on one dataset: the rebuilt prior with more open chromatin (seed 0, noise 0.01). We chose it because it comes closest to the paper; the default-chromatin version is kept as a check. We add seeds only if a result is borderline. Experiments 3 and 5 share one GPU job; the rest reuse experiment 1's saved results and run on CPU.

| # | Experiment | Compute | Status |
|---|---|---|---|
| 1 | Reproduce Fig. 2b: 3 seeds, noise 0.01 and 0.1, 8000 cells | GPU | done |
| 1b | Repeat experiment 1 on the rebuilt prior: seed 0, noise 0.01, default and more open chromatin | GPU | main dataset done; default running |
| 2 | Score the ATAC prior alone, without RNA | CPU | done |
| 3 | Remove the RNA signal: run CeSpGRN on shuffled RNA | GPU | queued |
| 4 | Test the soft penalty and the hard filter separately (2 × 2) | CPU | planned |
| 5 | Give CeSpGRN worse priors: a random prior of the same density, one prior shared by all cells, and noise 0.3 | GPU | queued |
| 6 | Score only edges inside the prior, to see what the RNA adds | CPU | planned |
| 7 | Give plain correlation the same prior and filter | CPU | planned |
| 8 | Rescore everything with standard AUPRC | CPU | planned |

Dropped for now: the β sweep (the paper's Fig. S4a already shows it is flat), and GENIE3 as a second baseline (only if experiment 7 is unclear).

## Setup

- **Data.** Simulated with scMultiSim using the settings encoded in the authors' dataset names, giving the paper's 110 genes and 330 regions. Where the paper is silent we chose: the simulator's example tree and 20 cell identity factors; noise adds false links to the prior only, flipping each missing link with probability equal to the noise level; a region counts as open when it has any ATAC reads.
- **Method and scoring.** The authors' own CeSpGRN code, settings ensemble and metrics.
- **Code.** Everything we wrote is in [`ablation/`](ablation/README.md).

## Changes to upstream code

- **Compatibility fixes** for functions removed from PyTorch, scikit-learn and NumPy.
- **A speed fix.** As published, the solver takes a matrix square root for one cell at a time, which would take days per dataset at 8000 cells. We compute them for all cells at once. On the small test dataset the scores are identical.

Neither change affects the results. Two helper modules the authors' scripts import were never published; we wrote our own in `ablation/lib/`. Details in [`journal.md`](journal.md#changes-to-upstream-code).
