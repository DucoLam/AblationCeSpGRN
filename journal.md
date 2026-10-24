# Journal

**Question:** does CeSpGRN's accuracy gain with scATAC-seq come from the method, or from the ATAC prior it is given? We suspect that on the paper's simulated benchmark the inferred GRN mostly reproduces the prior.

This file is the working log: each finding with how we got it (dates, job IDs, code lines). Newest entries go at the bottom. The short version for readers is [`research.md`](research.md).

Paper: Zhang et al., *Bioinformatics* 42(6), btag324 (2026). Supplement: `btag324_supplementary_data.pdf`. Upstream code: [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN) at `2fb222f` (= tag `v1.0.0`, the Zenodo release).

## Plan

The plan and its status live in [`research.md`](research.md#plan).

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

DAIC now uses this layout too, including for the resubmitted run below.

### 2026-10-23 · Full run resubmitted as one GPU job per dataset

GPU slots are scarce, so the 60 waiting jobs were cancelled (simulate and build had finished) and the run resubmitted as 6 GPU jobs (12999995–13000000), one per dataset, each running all 4 σ × 4 λ for both β and scoring both. Results are unchanged by two shortcuts in `ablation/pipeline/3_run_cespgrn.py`:

- The kernel, covariance and kernel-weighted covariance depend only on σ, so they are computed once per σ and shared by every λ and β. For β = 0 the mask is passed but multiplied by β = 0 in every update, and the cut only runs for β > 0, which is what upstream gets by passing no mask.
- Upstream's `G_admm_mask.train` recomputes the partial correlations of all cells after every batch of 512 cells (16 times at 8000 cells) and keeps only the last; the runner skips the intermediate passes and calls the same `construct_weighted_G` once on the final result.

### 2026-10-23 · Our noise model makes the noisy prior denser, not just worse

**Finding.** In the full-size datasets, raising noise from 0.01 to 0.1 multiplies the number of edges the prior allows by about 5. Recall against the ground truth triples and precision halves:

| Prior vs. ground truth (8000 cells) | Precision | Recall | Edges allowed |
|---|---|---|---|
| noise 0.01, seeds 0 / 1 / 2 | 0.45 / 0.53 / 0.53 | 0.27 / 0.30 / 0.24 | 1.5% / 1.4% / 1.1% |
| noise 0.1, seeds 0 / 1 / 2 | 0.26 / 0.25 / 0.26 | 0.82 / 0.77 / 0.74 | 7.8% / 7.6% / 7.1% |

Flipping 10% of the zeros in the region×gene and region×TF matrices opens many new TF → region → gene paths, and some of them happen to be true edges. So the noise-0.1 results depend strongly on how noise is injected, which the paper does not specify. Upstream's own name for the setting is `fp` (false positives), which fits adding links, but not how many.

**How.** `prior_stats.json` written by `2_build_dataset.py` for each dataset of the full run (build jobs 12999922, 12999933, 12999945, 12999956, 12999968, 12999979).

### 2026-10-23 · Minimal plan for the follow-up experiments

Duco chose the smallest plan that still answers the question. After experiment 1, everything runs on seed 0, noise 0.01; more seeds only if a result is borderline.

- One GPU job, 4 CeSpGRN sets: exp 3 shuffled RNA; exp 5 random prior of the same density, one prior shared by all cells, noise 0.3.
- CPU only, from the reproduction's saved results: exp 2, exp 4 as the 2 × 2 only, exp 6, exp 8, and exp 7 with the correlation stand-in only.
- Dropped: the β sweep (Fig. S4a already shows it is flat), GENIE3 (unless exp 7 is unclear), and the correlation stand-in and random weights from exp 3.

### 2026-10-24 · Upstream's solver is too slow to run as published; batched square root

**Finding.** Upstream's ADMM update computes, in every iteration, a matrix square root per cell with `scipy.linalg.sqrtm`, one matrix at a time on the CPU. At 8000 cells that is about 820,000 calls per CeSpGRN run; one call took 57 ms on the DAIC login node, so one run takes hours and a dataset (32 runs) days, longer than DAIC allows. The first jobs (12999995–12999997) ran at 7% GPU and 935% CPU use and were cancelled after about 75 minutes.

**Change.** The matrix (Yᵀ·Y/4 + I/ρ) is symmetric positive definite, so its square root is unique. `src/g_admm.py` now computes it for all cells of a batch at once from an eigendecomposition in float64 (`batched_sqrtm_spd`), in both solvers.

**How we checked it is equivalent.** On a test matrix the two methods differ by 1.2 × 10⁻¹⁴. Rerunning the 400-cell test dataset end to end (job 13000023) gave identical scores to four decimals (CeSpGRN ATAC 0.3542 / 0.5517, without β 0.0268 / 0.0229) and a largest value-by-value difference of 3.0 × 10⁻⁷ in the ensemble GRNs (values up to 0.47), i.e. 32-bit rounding. A λ run now takes about 33 s at 400 cells on 4 CPUs.

**Resubmitted.** 6 GPU jobs, 13000041–13000046 (`ablation/results/full_run_jobs_v3.txt` on DAIC).

### 2026-10-24 · Full reproduction: CeSpGRN does not beat its prior

**Finding.** At 8000 cells CeSpGRN with the ATAC prior never beats the prior alone on AUPRC. At noise 0.01 its early precision equals the prior's (difference ≤ 0.001); at noise 0.1 it is 0.01–0.03 higher. Mean over the 8000 cells, upstream's AUPRC:

| Noise, seed | CeSpGRN ATAC (AUPRC / EP) | Prior ATAC | Prior TF | CeSpGRN w/o β |
|---|---|---|---|---|
| 0.01, 0 | 0.3321 / 0.4544 | 0.3685 / 0.4534 | 0.6162 / 0.2327 | 0.0250 / 0.0221 |
| 0.01, 1 | 0.3637 / 0.5309 | 0.4208 / 0.5305 | 0.6163 / 0.2335 | 0.0249 / 0.0150 |
| 0.01, 2 | 0.3667 / 0.5343 | 0.3954 / 0.5336 | 0.6160 / 0.2325 | 0.0308 / 0.0577 |
| 0.1, 0 | 0.2719 / 0.2918 | 0.5412 / 0.2604 | 0.6162 / 0.2327 | 0.0250 / 0.0221 |
| 0.1, 1 | 0.2486 / 0.2672 | 0.5155 / 0.2529 | 0.6163 / 0.2335 | 0.0249 / 0.0150 |
| 0.1, 2 | 0.2843 / 0.2920 | 0.5005 / 0.2581 | 0.6160 / 0.2325 | 0.0308 / 0.0577 |

β = 0 scores are identical across noise for the same seed, as expected: noise only changes the prior. The paper reports 0.76 for CeSpGRN with β (Fig. S3c); we stay well below, consistent with our weaker prior.

**How.** Jobs 13000041–13000046 (all COMPLETED, 3:08–3:35 h each). Means of `AUPRC (abs)` and `Early Precision (abs)` per model over the per-cell rows of `ablation/results/scmultisim/<dataset>/{beta_1_atac,beta_0}/scores.csv` on DAIC.

### 2026-10-24 · Why our prior is weaker than the paper's: openness rule and noise

**Finding.** The paper's Fig. 2b gives CeSpGRN (ATAC) AUPRC 0.759 / Eprec 0.692 at noise 0.01 and 0.413 / 0.393 at noise 0.1. We get 0.33–0.37 / 0.45–0.53 and 0.25–0.28 / 0.27–0.29. Prior variants on seed 0, noise 0.01 (every 8th cell, upstream's metrics):

| Prior variant | Precision | Recall | AUPRC | EP |
|---|---|---|---|---|
| ours: positive edges, open = ATAC > 0, noise 0.01 | 0.454 | 0.265 | 0.369 | 0.453 |
| both signs | 0.455 | 0.312 | 0.390 | 0.452 |
| every region open | 0.424 | 0.797 | 0.613 | 0.424 |
| both signs, every region open | 0.412 | 0.924 | 0.669 | 0.413 |
| both signs, every region open, no noise | 0.709 | 0.907 | 0.809 | 0.709 |

- Open = ATAC > 0 (true counts) leaves 20% of the 330 regions open per cell and is the main loss of recall (0.80 → 0.26).
- Noise 0.01 on both region×gene and region×TF cuts precision from 0.71 to 0.41. The Fig. 2 caption defines "noise level" as "the error rate of the association between the chromatin regions and genes", i.e. region×gene only, and possibly in both directions (missing as well as false links). Our stronger noise is also why our prior's AUPRC rises at noise 0.1 while the paper's CeSpGRN drops.
- 23% of true (cell, edge) pairs are negative; `.regionToTFMatrix` never links a repressing TF, but this costs only 0.05 recall.
- 92% of genes have at least one linked region.

**How.** Job 13000189, `ablation/tools/probe_prior_recall.py` on `ablation/data/scMultiSim/raw/cells8000_seed0`; noise drawn as in `2_build_dataset.py`. Paper numbers read from Fig. 2b (main text p. 6).

### 2026-10-24 · The gap is our noise model and scMultiSim's ATAC sparsity, not the openness rule

**Finding.** Two things make our prior weaker than the paper's:

- **Noise per empty entry is huge.** region×gene has 147 links out of 36,300 entries (seed 0), so flipping each 0 with probability 0.01 adds about 360 false links, 2.5 times the real ones. Without noise the prior's precision is 0.72 instead of 0.45. Putting noise on region×gene only (as the Fig. 2 caption reads) instead of on both matrices changes precision by < 0.01 at noise 0.01, because both are swamped.
- **scMultiSim's `atac.p_zero` (default 0.8) sets the open fraction.** Our 20% open regions per cell is exactly that default. Re-simulating seed 0 with lower values:

| `atac.p_zero` | Open | Noise | Precision | Recall | AUPRC | EP |
|---|---|---|---|---|---|---|
| 0.8 (default) | 0.20 | none | 0.721 | 0.216 | 0.478 | 0.719 |
| 0.8 | 0.20 | 0.01 rg+rt (ours) | 0.454 | 0.265 | 0.369 | 0.453 |
| 0.5 | 0.50 | none | 0.729 | 0.576 | 0.656 | 0.728 |
| 0.5 | 0.50 | 0.01 rg+rt | 0.453 | 0.659 | 0.558 | 0.452 |
| 0.2 | 0.80 | none | 0.747 | 0.695 | 0.725 | 0.749 |
| 0.2 | 0.80 | 0.01 rg+rt | 0.469 | 0.781 | 0.627 | 0.470 |

The noise-free prior at `atac.p_zero` 0.2 alone scores 0.725 / 0.749, next to the paper's CeSpGRN (0.759 / 0.692).

Ruled out as main causes: smoothing openness over the 51 neighbouring cells on the same branch (open in ≥ 10/30/50% of them) moves the open fraction only from 0.20 to 0.20–0.21, so openness in scMultiSim is stable along the trajectory, not dropout; "rg both ways" noise (also dropping real links) is within 0.01 of "rg".

**How.** Jobs 13000191 (`ablation/tools/probe_prior_rules.py`, full grid on `raw/cells8000_seed0`) and 13000192 (re-simulation with `1_simulate.R 0 <out> 8000 <atac_p_zero>` into `raw/pzero_check/`, then the short grid). Link counts with awk on `region_to_gene.tsv`.

Asked the authors (Duco emailed the corresponding author, Xiuwei Zhang, on 2026-10-24) for the scMultiSim settings, how openness and region×TF are defined, how noise is applied, and the data or scripts.

### 2026-10-24 · Rebuilt prior: 400-cell test, and experiment 1 resubmitted

**Change.** `2_build_dataset.py --noise links` moves a share fp of the real region×gene links to random empty pairs (1 of 148 at 0.01, 15 at 0.1); region×TF stays noise-free. `submit_reproduction.sh` takes `P_ZERO` (scMultiSim `atac.p_zero`) and `NOISE`; non-default values add `_pz<P_ZERO>` / `_<NOISE>` to directory names. Old datasets rebuild unchanged (default per-entry).

**Test (400 cells, seed 0), AUPRC / EP, mean over cells:**

| Dataset | Prior precision / recall | Prior ATAC | CeSpGRN ATAC | CeSpGRN w/o β |
|---|---|---|---|---|
| old: per-entry noise 0.01 | 0.552 / 0.234 | 0.401 / 0.552 | 0.354 / 0.552 | 0.027 / 0.023 |
| links 0.01 | 0.799 / 0.200 | 0.509 / 0.799 | 0.493 / 0.799 | 0.027 / 0.023 |
| links 0.1 | 0.739 / 0.150 | 0.455 / 0.739 | 0.443 / 0.739 | 0.027 / 0.023 |
| pz0.2, links 0.01 | 0.810 / 0.732 | 0.774 / 0.810 | 0.744 / 0.811 | 0.026 / 0.020 |
| pz0.2, links 0.1 | 0.771 / 0.664 | 0.722 / 0.771 | 0.681 / 0.771 | 0.026 / 0.020 |

With `atac.p_zero` 0.2 and links noise 0.01, CeSpGRN reaches AUPRC 0.744 (paper: 0.759), and again stays at or below its prior. Noise now lowers precision and recall, as in the paper.

**How.** Test jobs 13000227–13000232 (CPU, `NUM_CELLS=400 SEEDS=0 FPS="0.01 0.1" GPU=0`, `P_ZERO` 0.8 and 0.2, `NOISE=links`). Full runs, 8000 cells, seed 0, noise 0.01: prep 13000275 + GPU 13000276 (`_links`), prep 13000277 + GPU 13000278 (`_pz0.2_links`).

### 2026-10-24 · Experiments 3 and 5, code check on the old 400-cell prior: shuffled RNA changes nothing

**Finding (preliminary).** A test of the experiment 3 + 5 code on the old 400-cell dataset (old prior: `atac.p_zero` 0.8, per-entry noise 0.01) already shows the pattern we expect. Not the main result: the rebuilt prior replaces this dataset.

| 400 cells, old prior (AUPRC / EP) | CeSpGRN | Prior alone |
|---|---|---|
| Real ATAC prior (earlier test, jobs 12997127–38) | 0.354 / 0.552 | 0.401 / 0.552 |
| Shuffled RNA, real prior | 0.368 / 0.553 | |
| Random prior, same density per cell | 0.025 / 0.024 | 0.029 / 0.024 |
| One prior shared by all cells, same density | 0.372 / 0.570 | 0.415 / 0.570 |
| Noise 0.3 (per-entry) | 0.240 / 0.240 | 0.616 / 0.234 |

With every gene's expression shuffled across cells, CeSpGRN scores as well as with the real RNA. A random prior of the same density makes it collapse. A prior shared by all cells scores slightly higher than the per-cell one. At per-entry noise 0.3 the prior allows nearly every TF edge, so it scores like the TF prior.

**How.** Job 13000190 (CPU, 1:40 h): `ablation/pipeline/run_followup.sh` on `simulated_400_20_10_100_0.01_0_0_4` (variants from `5_make_variants.py`, seed 0). Scores in `ablation/results/scmultisim/followup_test_400/` on DAIC.

## Changes to upstream code

Kept minimal, so `git diff upstream/master -- src test demo.py` shows them all.

- `src/g_admm.py`: `torch.eig` → `torch.linalg.eig` / `eigvals`, `torch.cholesky` → `torch.linalg.cholesky` (removed from PyTorch; same results).
- `src/bmk_beeline.py`: `precision_recall_curve(probas_pred=…)` → `y_score=…` and `np.int` → `int` (removed from scikit-learn / NumPy; same results).
- `src/g_admm.py`: the ADMM square root, one `scipy.linalg.sqrtm` per cell, → `batched_sqrtm_spd`, one batched eigendecomposition (speed only; same result up to 32-bit rounding, see the 2026-10-24 entry).

Upstream's scripts also import `bmk` and `cov`, which were never published. Our versions live in `ablation/lib/` (not in `src/`): `cov.est_cov_para` follows the commented-out version in `g_admm.py`; `bmk.calc_scores_para` uses upstream's own metrics.
