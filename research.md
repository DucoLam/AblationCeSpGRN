# Research journal

**Question:** does CeSpGRN's accuracy gain with scATAC-seq come from the method, or from the ATAC prior it is given? We suspect that on the paper's simulated benchmark the inferred GRN mostly reproduces the prior.

This file records the plan and each finding with how we got it. Newest entries go at the bottom of the journal.

Paper: Zhang et al., *Bioinformatics* 42(6), btag324 (2026). Supplement: `btag324_supplementary_data.pdf`. Upstream code: [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN) at `2fb222f` (= tag `v1.0.0`, the Zenodo release).

## Plan

| # | Experiment | Status |
|---|---|---|
| 1 | Reproduce Fig. 2b (3 seeds × noise 0.01/0.1, 8000 cells) with upstream's method and scoring | running |
| 2 | Score the ATAC prior alone, no RNA | in every run |
| 3 | Take away the RNA signal: shuffled RNA, correlation stand-in, random weights inside the prior | planned |
| 4 | Separate the soft β penalty from the hard cut (2 × 2, then a β sweep) | planned |
| 5 | Make the prior worse step by step; plot CeSpGRN's score against the prior's | planned |
| 6 | Score only inside the prior (what the RNA adds beyond it) | planned |
| 7 | Give baselines (GENIE3, correlation) the same per-cell prior and cut | planned |
| 8 | Rescore everything with standard AUPRC (`average_precision_score`) | planned; upstream's AUPRC kept until then |

## Journal

### 2026-10-20 · Upstream cuts every edge outside the prior

**Finding.** The scored GRN can only contain edges the prior allows. After solving, upstream multiplies the result by `(1 − mask)`, setting every edge outside the prior to exactly 0. The paper describes only the soft penalty β‖M ⊙ Θ‖² (Eq. 2).

**How.** Read the code: `src/g_admm.py:654-659` (`G_admm_mask.train`, applied whenever β > 0) and `test/scripts_scmultisim/test_scmultisim.py:222-225` (ensemble step).

### 2026-10-20 · The paper's β ablation measures the cut, not the penalty

**Finding.** With β = 0 upstream loads no mask at all, so "without β" means "no prior". With β > 0 the penalty and the cut always come together. Fig. S3c (AUPRC ≈ 0 without β, 0.76 with) therefore cannot separate them, and the flat β sweep in Fig. S4a (0.01 to 100) is what the cut predicts: β's value only changes the soft part.

**How.** `test_scmultisim.py:165-170` and `test_scmultisim_hyperparams.py` (β sweep with the ATAC mask loaded for every β > 0); supplement Figs. S3c and S4a.

### 2026-10-20 · The authors scored the prior alone but did not report it

**Finding.** Upstream's evaluation computes "Prior (ATAC)", "Prior (ATAC cluster)" and "Prior (TF)" scores. None appear in Fig. 2 or the supplement.

**How.** `test/scripts_scmultisim/eval_scores.py:39-41, 77-94`.

### 2026-10-20 · The benchmark data, prior construction and noise are not published

**Finding.** No code in upstream (current tree, full git history, Zenodo release) or in scMultiSim (all branches) builds the per-cell priors (`grn_prior_{i}.txt`, `region_tf_{i}.txt`) or adds the noise. Upstream's scMultiSim scripts also import `bmk` and `cov`, which never existed in the repo. The paper describes the prior only in words (Section 2.3, Fig. S1); Note 1.8 defines noise as "false positive connections in the cross-modality relationship matrices".

**How.** `git log -S` over upstream history; `git grep` over every scMultiSim branch; Zenodo record 19189926 is the `v1.0.0` tag.

### 2026-10-20 · The simulator builds the region×TF matrix from the true GRN

**Finding.** scMultiSim links a TF to a region only if the TF truly (and positively) regulates a gene behind that region. Before noise, every prior edge therefore comes from the ground truth or from regions shared by several genes. The "ATAC prior" carries the answer key; ATAC itself only decides, per cell, which of those edges are closed.

**How.** scMultiSim `R/8_utils.R` `.regionToTFMatrix` ([permalink](https://github.com/ZhangLabGT/scMultiSim/blob/563c3b542ada289fb4d9789bb1bc944229e78699/R/8_utils.R#L18-L39)), called from `R/1_main.R:204-208`.

### 2026-10-20 · Reconstructed simulation matches the paper's sizes

**Finding.** Upstream's dataset names decode as `simulated_{cells}_{changing edges}_{cells per step}_{steps}_{fp}_{seed}_{weight mean}_{weight sd}`. scMultiSim with `GRN_params_100`, those dynamic-GRN settings and default options gives exactly the paper's 110 genes and 330 regions.

**How.** Names in `test_scmultisim_ggm.py:223`; scMultiSim's dynamic-GRN vignette uses weight mean 0, sd 4; gene and region counts follow from scMultiSim's defaults (`R/1_main.R:527-556`). Our simulator: `simulator/scmultisim/simulate.R`.

Assumptions where the paper is silent: tree `Phyla1()`, 20 CIFs (from the same vignette); region×TF rebuilt per cell from that cell's GRN with scMultiSim's own rule; noise flips each 0 in the region×gene and region×TF copies to 1 with probability fp, for the prior only; a region is open when its ATAC count > 0. See `simulator/scmultisim/build_dataset.py`.

### 2026-10-20 · Test run (400 cells): CeSpGRN does not beat its own prior

**Finding.** On a small test dataset (400 cells, seed 0, noise 0.01), CeSpGRN with the ATAC prior scores no better than the prior alone:

| | AUPRC | Early precision |
|---|---|---|
| CeSpGRN, ATAC prior (β = 1) | 0.354 | 0.552 |
| ATAC prior alone | 0.401 | 0.552 |
| CeSpGRN, no prior (β = 0) | 0.027 | 0.023 |
| TF prior alone | 0.616 | 0.234 |

Our reconstructed prior has precision 0.55 and recall 0.23 against the ground truth, so it is weaker than the authors' must be (their CeSpGRN reaches AUPRC 0.76). Not comparable to the paper yet: 400 cells instead of 8000.

**How.** `slurm/submit_reproduction.sh` with `NUM_CELLS=400 SEEDS=0 FPS=0.01` (jobs 12997127–12997138): upstream's `G_admm_mask` with the 16-setting ensemble and final cut, scored with upstream's `bmk_beeline` metrics (`test/scripts_ablation/run_cespgrn.py`, `ensemble.py`).

### 2026-10-20 · Upstream's AUPRC rewards ties

**Finding.** Upstream computes AUPRC as `auc(recall, precision)`, which interpolates linearly between curve points. For a yes/no prediction this draws a line from (recall 0, precision 1) to its single point, worth roughly (1 + precision) / 2. That's why the crude TF prior scores 0.62. Every output with many tied values (priors, and CeSpGRN after the cut) is flattered. Kept for now so our numbers compare with the paper's; see plan item 8.

**How.** `src/bmk_beeline.py` `_compute_auc`; TF prior result in the test run above.

### 2026-10-23 · Full reproduction submitted

3 seeds × noise 0.01/0.1, 8000 cells, β = 1 (Fig. 2b) and β = 0 (Fig. S3c): 69 jobs, 12999921–12999989 (list in `results/full_run_jobs.txt` on DAIC).

### 2026-10-23 · Our code moved to `ablation/`

All our code now lives in `ablation/`, separate from upstream's; see [`ablation/README.md`](ablation/README.md) for what runs in which order. Paths in the entries above refer to the old layout:

| Before | Now |
|---|---|
| `simulator/scmultisim/simulate.R` | `ablation/pipeline/1_simulate.R` |
| `simulator/scmultisim/build_dataset.py` | `ablation/pipeline/2_build_dataset.py` |
| `test/scripts_ablation/run_cespgrn.py` | `ablation/pipeline/3_run_cespgrn.py` |
| `test/scripts_ablation/ensemble.py` | `ablation/pipeline/4_ensemble.py` |
| `src/bmk.py`, `src/cov.py` | `ablation/lib/` |
| `slurm/`, `tools/`, `pixi.toml`, `pixi.lock`, `container_pixi.def` | `ablation/` |
| `data/scMultiSim/`, `results/` (on DAIC) | `ablation/data/`, `ablation/results/` |

The full run above still uses the old layout on DAIC; DAIC switches over once it has finished.

### 2026-10-23 · Our noise model makes the noisy prior denser, not just worse

**Finding.** In the full-size datasets, raising noise from 0.01 to 0.1 multiplies the number of edges the prior allows by about 5. Recall against the ground truth triples and precision halves:

| Prior vs. ground truth (8000 cells) | Precision | Recall | Edges allowed |
|---|---|---|---|
| noise 0.01, seeds 0 / 1 / 2 | 0.45 / 0.53 / 0.53 | 0.27 / 0.30 / 0.24 | 1.5% / 1.4% / 1.1% |
| noise 0.1, seeds 0 / 1 / 2 | 0.26 / 0.25 / 0.26 | 0.82 / 0.77 / 0.74 | 7.8% / 7.6% / 7.1% |

Flipping 10% of the zeros in the region×gene and region×TF matrices opens many new TF → region → gene paths, and some of them happen to be true edges. So the noise-0.1 results depend strongly on how noise is injected, which the paper does not specify. Upstream's own name for the setting is `fp` (false positives), which fits adding links, but not how many.

**How.** `prior_stats.json` written by `2_build_dataset.py` for each dataset of the full run (build jobs 12999922, 12999933, 12999945, 12999956, 12999968, 12999979).

## Changes to upstream code

Kept minimal, so `git diff upstream/master -- src test demo.py` shows them all.

- `src/g_admm.py`: `torch.eig` → `torch.linalg.eig` / `eigvals`, `torch.cholesky` → `torch.linalg.cholesky` (removed from PyTorch; same results).
- `src/bmk_beeline.py`: `precision_recall_curve(probas_pred=…)` → `y_score=…` and `np.int` → `int` (removed from scikit-learn / NumPy; same results).

Upstream's scripts also import `bmk` and `cov`, which were never published. Our versions live in `ablation/lib/` (not in `src/`): `cov.est_cov_para` follows the commented-out version in `g_admm.py`; `bmk.calc_scores_para` uses upstream's own metrics.
