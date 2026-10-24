# Does CeSpGRN learn from RNA, or copy its prior?

CeSpGRN infers a gene regulatory network (GRN) for every single cell from RNA data. With scATAC-seq it also gets a **prior**: per cell, the set of TF → gene edges that the cell's open chromatin allows. On the paper's simulated benchmark this prior lifts accuracy (AUPRC) from about 0 to 0.76.

We ask where that gain comes from: does CeSpGRN learn the network from the RNA, or does it mostly hand back the prior it was given?

Paper: Zhang et al., *Bioinformatics* 42(6), btag324 (2026). Code: [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN) `v1.0.0`. The detailed log, with dates, job IDs and code references, is in [`journal.md`](journal.md).

## Main result

**CeSpGRN's accuracy comes from the ATAC prior and a hard cut on edges outside it, not from the RNA.** Take the prior away and CeSpGRN is close to random. Keep only the cut and drop CeSpGRN's use of the prior in its equation, and the score barely moves. Within the prior, the RNA adds a small gain in ordering the edges, and CeSpGRN without the prior gives the same gain.

The experiments below show each step. All numbers are 8000 cells, one seed, noise 0.01, unless stated otherwise.

## How CeSpGRN works, in short

- **Input:** gene expression (RNA) for every cell, and per cell a **prior**: the TF → gene links that the cell's open chromatin (ATAC) allows.
- **Method:** for each cell, CeSpGRN estimates a network from the RNA of that cell and its neighbours (cells with similar expression). A penalty with weight β pushes it away from edges outside the prior.
- **A step the paper doesn't mention:** after solving, the code sets every edge outside the prior to zero. So the output can only contain edges the prior allows. We call this **the cut**.
- **Output:** the average of 16 runs (4 neighbourhood bandwidths × 4 sparsity levels), one network per cell.

**How we score**, per cell against the true network, then averaged over cells:
- **AUPRC:** overall accuracy of the edge ranking. 1 is perfect; random is about 0.02 here.
  - **The paper's AUPRC** draws a straight line from the start of the curve to the first real point. That rewards tied scores: a plain yes/no prediction gets roughly (1 + precision) / 2. Priors, and CeSpGRN after the cut, are full of ties.
  - **Standard AUPRC** (`average_precision_score`) does not reward ties. We report both.
- **Early precision:** of the top edges (as many as there are true edges), the share that is true.

## The paper's claim

![The paper's Figure 2](ablation/figures/paper_fig2.png)

**Figure 1.** The paper's Fig. 2 (Zhang et al. 2026, p. 6). (a) Accuracy when only TF information is given. (b) Accuracy with scATAC-seq: CeSpGRN (ATAC) reaches AUPRC 0.76 and early precision 0.69 at noise 0.01, far above the other methods. The paper does not show the ATAC prior on its own.

## Experiments

### 1. Reproduce the paper's Fig. 2b · done

We rebuilt the benchmark (the code that made it is not published, see [Setup](#setup)) and ran CeSpGRN exactly as the authors' code does. We land below the paper's score (0.66 vs 0.76), with the same pattern: with the prior CeSpGRN does well, without it CeSpGRN is close to random.

![Fig. 2b redrawn on our rebuild](ablation/figures/fig2b_rebuilt.png)

**Figure 2.** Fig. 2b redrawn with the authors' own plotting code, adding the prior on its own. Bars are the mean over 8000 cells, error bars one standard deviation, paper's AUPRC. Two chromatin settings: the simulator's default (most chromatin closed, a weaker prior) and more open chromatin (our main setting, closest to the paper).

| 8000 cells, noise 0.01 | Paper's AUPRC | Standard AUPRC | Early precision |
|---|---|---|---|
| CeSpGRN with ATAC prior | 0.66 | 0.55 | 0.74 |
| ATAC prior alone | 0.72 | 0.52 | 0.74 |
| CeSpGRN without prior | 0.02 | 0.02 | 0.01 |
| *Paper: CeSpGRN with ATAC prior* | *0.76* | | *0.69* |

### 2. Score the prior on its own · done

The authors' evaluation code scores the prior on its own, but the paper does not report it. In every setting we tried, the prior alone scores about as well as CeSpGRN with that prior (Figure 2): 0.72 vs 0.66 on the paper's AUPRC and 0.74 vs 0.74 on early precision. With the default chromatin both are 0.47.

### 3. Shuffled RNA · running

We shuffle each gene's expression across cells. Each gene keeps its values, but every relation between genes is destroyed, so the RNA carries no regulatory signal. If CeSpGRN with the real prior scores the same on shuffled RNA, the RNA contributes nothing measurable. A small test on our first rebuild pointed that way (0.37 shuffled vs 0.35 real).

### 4. Penalty or cut: which one does the work? · done

CeSpGRN uses the prior twice: as a penalty in its equation (what the paper describes) and as the cut afterwards (what the code also does). We switched them on and off separately. The penalty alone barely changes the network (0.03, near random). The cut alone gives almost the whole score (0.65 of 0.66).

![Experiment 4](ablation/figures/exp4_penalty_vs_cut.png)

**Figure 3.** CeSpGRN with neither, one or both uses of the prior. Mean over 8000 cells, error bars one standard deviation.

### 5. Worse priors · done

We gave CeSpGRN the same RNA with worse priors: a noisier prior (30% of the region–gene links moved to wrong pairs), one prior shared by all cells (the edges allowed in the most cells, as many as a cell allows on average), and a random prior with the same number of edges per cell. CeSpGRN follows its prior every time. With the random prior it collapses to random (0.03), so the same RNA cannot recover the network on its own. With each of the other priors, CeSpGRN stays within about 0.02 of the prior alone on standard AUPRC, just above it, and below it on the paper's AUPRC.

The per-cell prior does help: one prior shared by all cells scores lower (0.38 vs 0.55 standard AUPRC). So the cell-specific ATAC information matters, but it reaches the output through the prior, not through the RNA.

![Experiment 5](ablation/figures/exp5_worse_priors.png)

**Figure 4.** CeSpGRN and its prior alone, for the real per-cell prior and three worse ones. Left the paper's AUPRC, right standard AUPRC. Mean over 8000 cells, error bars one standard deviation.

### 6. Inside the prior: does the RNA order the allowed edges? · done

Among the edges the prior allows, 74% are true. We score only those edges: does CeSpGRN put the true ones first? A little: 0.78 against 0.74 for a random order. CeSpGRN without the prior, ranking the same edges, scores 0.78 as well. So the small gain comes from correlations in the RNA, not from how CeSpGRN uses the prior.

![Experiment 6](ablation/figures/exp6_inside_prior.png)

**Figure 5.** Standard AUPRC counted only over the edges the prior allows. "Random order" is the share of true edges among them, which is what a random ordering scores. Mean over 8000 cells, error bars one standard deviation.

### 7. A simple baseline with the same prior · running

We give plain correlation the same prior and cut: once the correlation over all cells, and once CeSpGRN's own per-cell correlation (its input, before the solver). If these match CeSpGRN, the solver adds nothing. In the small test (400 cells), plain correlation over all cells scored the same as CeSpGRN (0.74 vs 0.74).

### 8. Standard AUPRC · done (experiment 3 still to add)

On the paper's AUPRC the prior alone scores higher than CeSpGRN. With standard AUPRC the order flips: CeSpGRN is slightly ahead (0.55 vs 0.52, and 0.20 vs 0.18 with default chromatin). So "the prior beats CeSpGRN" is partly an effect of the metric. The paper's AUPRC also inflates all scores: with default chromatin it reads 0.47 where standard AUPRC gives 0.20.

![Experiment 8](ablation/figures/exp8_standard_auprc.png)

**Figure 6.** The paper's AUPRC next to standard AUPRC, for CeSpGRN and the prior alone, in both chromatin settings. Mean over 8000 cells, error bars one standard deviation.

Dropped for now: a sweep over β (the paper's Fig. S4a already shows it is flat), GENIE3 as a second baseline (only if experiment 7 is unclear), noise 0.1, and more seeds (only if a result is borderline).

## What else we found

1. **The paper's β experiment cannot separate penalty from cut.** In the code, "without β" means "without any prior", and any β above zero switches the cut on. That explains why accuracy barely moves when β goes from 0.01 to 100 (their Fig. S4a), and experiment 4 confirms it.
2. **The simulated prior is built from the true network.** The simulator links a TF to a chromatin region only if that TF truly regulates a gene next to the region. The prior therefore contains the answer; chromatin only decides which of those edges are closed in each cell. That makes the prior unrealistically informative.
3. **The benchmark cannot be rebuilt from what is published.** The code that builds the priors and adds noise is not public, and two unstated choices change the prior's quality a lot: how noise is added and how much chromatin is open. We have asked the authors for their settings.
4. **Single settings may tell a different story than the average** (400 cells only). In a small test, no single setting beat the prior's AUPRC, but some ordered the prior's edges better: early precision up to 0.93 against the prior's 0.81. Experiment 6 asks the same question at full size for the average and finds only a small gain.

## Setup

- **Data.** Simulated with scMultiSim using the settings encoded in the authors' dataset names, giving the paper's 110 genes and 330 regions. Where the paper is silent we chose: the simulator's example tree and 20 cell identity factors; a region counts as open when it has any ATAC reads; noise moves a share of the real region–gene links to wrong pairs (the paper calls it an "error rate" of that association).
- **More open chromatin.** By default the simulator makes 80% of ATAC values zero, which leaves most true edges outside the prior. We use 20% zeros, because that gives a prior as strong as the paper's scores imply. We picked it to match the paper, so the default is kept as a check.
- **A first rebuild** used the simulator's defaults and added noise to every empty entry, which at 0.01 already tripled the region–gene links. Its prior was much weaker (AUPRC 0.37) but gave the same conclusion. Details in [`journal.md`](journal.md).
- **Method and scoring.** The authors' own CeSpGRN code, settings and metrics; see the table below.
- **Code.** Everything we wrote is in [`ablation/`](ablation/README.md). Figures are drawn by `ablation/plots/`.

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

- **The cut** is in the code but not in the paper. We follow the code, because that is what produced their numbers.
- **Two speed changes** (see [Changes to upstream code](#changes-to-upstream-code)) give identical scores to four decimals.
- **The two missing modules** (`cov`, `bmk`) are rebuilt from the paper and the authors' commented-out code.
- **The data and the prior** are rebuilt, because the code that made them is not published (see above).

## Changes to upstream code

- **Compatibility fixes** for functions removed from PyTorch, scikit-learn and NumPy.
- **A speed fix.** As published, the solver takes a matrix square root for one cell at a time, which would take days per dataset at 8000 cells. We compute them for all cells at once. On the small test dataset the scores are identical.

Neither change affects the results. Two helper modules the authors' scripts import were never published; we wrote our own in `ablation/lib/`. Details in [`journal.md`](journal.md#changes-to-upstream-code).
