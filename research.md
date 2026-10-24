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

**Why we stay below the paper.** Our prior is much weaker than the authors' must be. Scoring variants of it on one dataset (seed 0, noise 0.01) shows why:

| Prior variant | Precision | Recall | AUPRC | Early precision |
|---|---|---|---|---|
| Ours | 0.45 | 0.26 | 0.37 | 0.45 |
| Also use negative edges | 0.46 | 0.31 | 0.39 | 0.45 |
| Treat every region as open | 0.42 | 0.80 | 0.61 | 0.42 |
| Both of the above | 0.41 | 0.92 | 0.67 | 0.41 |
| Both, and no noise | 0.71 | 0.91 | 0.81 | 0.71 |

- **Which regions count as open is the main cause.** We call a region open in a cell when it has any ATAC reads. That is only 20% of regions per cell, and it drops three quarters of the true edges. The paper does not say how it decides openness.
- **Our noise is too strong.** Even at 0.01 it halves the share of true edges in the prior's links. We add false links between regions and genes and between regions and TFs, but the paper's Fig. 2 caption describes noise only on the regions–genes side. This also explains why, unlike in the paper, our prior gets *better* on AUPRC at noise 0.1.
- **Negative edges matter little.** The simulator only links a TF to a region when it activates the gene. Repressions, 23% of true edges, can never enter the prior.

A clean prior on its own (last row) already scores about what the paper reports for CeSpGRN.

**Quality of our prior** (range over 3 seeds):

| Noise | Precision | Recall | Share of all edges it allows |
|---|---|---|---|
| 0.01 | 0.45 – 0.53 | 0.24 – 0.30 | 1.1 – 1.5% |
| 0.1 | 0.25 – 0.26 | 0.74 – 0.82 | 7.1 – 7.8% |

More noise lets through about 5 times more edges, which catches about 3 times more true edges at half the precision.

## Plan

After experiment 1, everything runs on one dataset (seed 0, noise 0.01). We add seeds only if a result is borderline. Experiments 3 and 5 share one GPU job; the rest reuse experiment 1's saved results and run on CPU.

| # | Experiment | Compute | Status |
|---|---|---|---|
| 1 | Reproduce Fig. 2b: 3 seeds, noise 0.01 and 0.1, 8000 cells | GPU | done |
| 2 | Score the ATAC prior alone, without RNA | CPU | done |
| 3 | Remove the RNA signal: run CeSpGRN on shuffled RNA | GPU | planned |
| 4 | Test the soft penalty and the hard filter separately (2 × 2) | CPU | planned |
| 5 | Give CeSpGRN worse priors: a random prior of the same density, one prior shared by all cells, and noise 0.3 | GPU | planned |
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
