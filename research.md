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
7. **In our rebuild, noise makes the prior larger, not just worse.** See the second table below. How the paper injects noise is not specified, so results at high noise depend heavily on that choice.

## Results

**Small test run** (400 cells, one seed, noise 0.01). CeSpGRN does not beat the prior it is given:

| | AUPRC | Early precision |
|---|---|---|
| CeSpGRN with ATAC prior | 0.35 | 0.55 |
| ATAC prior alone | 0.40 | 0.55 |
| CeSpGRN without prior | 0.03 | 0.02 |

Not yet comparable with the paper: it uses 1/20 of the cells, and our prior is weaker than the authors' must be.

**Quality of our prior at full size** (8000 cells, range over 3 seeds):

| Noise | Precision | Recall | Share of all edges it allows |
|---|---|---|---|
| 0.01 | 0.45 – 0.53 | 0.24 – 0.30 | 1.1 – 1.5% |
| 0.1 | 0.25 – 0.26 | 0.74 – 0.82 | 7.1 – 7.8% |

More noise lets through about 5 times more edges, which catches about 3 times more true edges at half the precision.

**Full reproduction of the paper's main figure** (Fig. 2b): queued on the cluster.

## Plan

| # | Experiment | Status |
|---|---|---|
| 1 | Reproduce Fig. 2b: 3 seeds, noise 0.01 and 0.1, 8000 cells | queued |
| 2 | Score the ATAC prior alone, without RNA | part of every run |
| 3 | Remove the RNA signal: shuffled RNA, plain correlation, random weights inside the prior | planned |
| 4 | Test the soft penalty and the hard filter separately, then sweep β | planned |
| 5 | Make the prior gradually worse and compare CeSpGRN's score with the prior's | planned |
| 6 | Score only edges inside the prior, to see what the RNA adds | planned |
| 7 | Give simpler methods (GENIE3, correlation) the same prior and filter | planned |
| 8 | Rescore everything with standard AUPRC | planned |

## Setup

- **Data.** Simulated with scMultiSim using the settings encoded in the authors' dataset names, giving the paper's 110 genes and 330 regions. Where the paper is silent we chose: the simulator's example tree and 20 cell identity factors; noise adds false links to the prior only, flipping each missing link with probability equal to the noise level; a region counts as open when it has any ATAC reads.
- **Method and scoring.** The authors' own CeSpGRN code, settings ensemble and metrics.
- **Code.** Everything we wrote is in [`ablation/`](ablation/README.md).

## Changes to upstream code

Only fixes for functions removed from PyTorch, scikit-learn and NumPy; results are unchanged. Two helper modules the authors' scripts import were never published; we wrote our own in `ablation/lib/`. Details in [`journal.md`](journal.md#changes-to-upstream-code).
