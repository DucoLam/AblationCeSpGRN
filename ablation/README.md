# ablation/

Everything we added to upstream CeSpGRN lives here. Upstream's own code (`../src`, `../test`, `../demo.py`) stays where it was. The few fixes we had to make to it are listed in [`../research.md`](../research.md#changes-to-upstream-code).

All commands run **from the repo root**, so the container sees both upstream's code and ours.

## What runs, in order

The reproduction of the paper's simulated benchmark (Fig. 2b) and its β ablation (Fig. S3c). `slurm/submit_reproduction.sh` submits them as few jobs as possible: one CPU job per seed for steps 1–2 (only if the data is missing), and one GPU job per dataset for steps 3–4 ([`pipeline/run_dataset.sh`](pipeline/run_dataset.sh)).

| Step | Our script | What it does | Upstream code it calls |
|---|---|---|---|
| 1 | [`pipeline/1_simulate.R`](pipeline/1_simulate.R) | Simulates paired RNA + ATAC data and a true GRN per cell with scMultiSim (paper Note 1.8) | none (scMultiSim) |
| 2 | [`pipeline/2_build_dataset.py`](pipeline/2_build_dataset.py) | Builds the ground truth, the per-cell ATAC prior with noise, and the TF prior (paper Section 2.3, Fig. S1) | none (authors' version unpublished) |
| 3 | [`pipeline/3_run_cespgrn.py`](pipeline/3_run_cespgrn.py) | Runs CeSpGRN for every bandwidth σ, sparsity weight λ and β, as upstream's `test_scmultisim.py`; the kernel and covariance are computed once per σ and shared | `kernel.calc_kernel_neigh`, `g_admm.G_admm_mask` (`.train`), `g_admm.construct_weighted_G`; covariance via [`lib/cov.py`](lib/cov.py) → `g_admm.weighted_kendall_tau` |
| 4 | [`pipeline/4_ensemble.py`](pipeline/4_ensemble.py) | Averages the 16 bandwidth × λ runs, cuts every edge outside the prior (as upstream), scores each cell; also scores the priors alone | scoring via [`lib/bmk.py`](lib/bmk.py) → `bmk_beeline.compute_auc_abs`, `compute_eprec_abs` |

[`lib/`](lib) holds our versions of the two modules upstream's scripts import but never published: `cov.py` (covariance, from the commented-out code in `g_admm.py`) and `bmk.py` (per-cell scoring with upstream's metrics).

### Settings

From the paper's [supplementary data](https://academic.oup.com/bioinformatics/article/42/6/btag324/8699592) (Notes 1.4 and 1.8) and upstream's scripts:

| Setting | Values |
|---|---|
| Seeds | 0, 1, 2 |
| Noise (false-positive rate of the region matrices) | 0.01, 0.1 |
| Cells / genes / regions | 8000 / 110 / 330 |
| Bandwidth σ | 0.01, 0.1, 1, 10 |
| Sparsity λ | 0.01, 0.05, 0.1, 0.5 |
| Neighbourhood size \|Nᵢ\| | 100 |
| β | 1 (Fig. 2b), 0 (Fig. S3c) |

Metrics are AUPRC and early precision as in Pratapa et al. (2020)[^pratapa], computed with upstream's `bmk_beeline.py`. Assumptions where the paper is silent are listed in [`../research.md`](../research.md).

[^pratapa]: Pratapa, A., Jalihal, A. P., Law, J. N., Bharadwaj, A., & Murali, T. M. (2020). Benchmarking algorithms for gene regulatory network inference from single-cell transcriptomic data. *Nature Methods*, 17(2), 147–154. https://doi.org/10.1038/s41592-019-0690-6

## Layout

| Path | Contents |
|---|---|
| `pipeline/` | The steps above, numbered in the order they run |
| `lib/` | `cov.py`, `bmk.py` (upstream's missing modules) |
| `slurm/` | `run.sh` (runs a command in the container), `sbatch.sh` (sbatch with a readable log), `build_container.sh`, `submit_reproduction.sh` |
| `pixi.toml`, `pixi.lock`, `container_pixi.def` | The environment and the Apptainer image it is baked into |
| `tools/` | Job monitoring from your Mac: `lazyjobs.py` (terminal UI), `job_dashboard.py` (browser), `askpass.sh` (password helper for lazyslurm) |
| `data/`, `results/`, `slurm/logs/` | Simulated data, outputs and job logs; not in git |

## Running on DAIC

The environment (Python, PyTorch with CUDA, R with scMultiSim) is defined in `pixi.toml`, pinned in `pixi.lock`, and baked into an Apptainer image. Code is not baked in; it is mounted at run time, so only dependency changes need a rebuild.

```bash
# from the repo root, on DAIC
bash ablation/slurm/sbatch.sh ablation/slurm/build_container.sh                     # builds ablation/ablation-cespgrn.sif
bash ablation/slurm/submit_reproduction.sh                                          # the full reproduction (6 GPU jobs, + 3 CPU jobs if data is missing)
NUM_CELLS=400 SEEDS=0 FPS=0.01 GPU=0 QOS=short TIME=01:00:00 CPUS=4 MEM=8G \
  bash ablation/slurm/submit_reproduction.sh                                        # small CPU test run
bash ablation/slurm/sbatch.sh -J my-run ablation/slurm/run.sh python path/to/script.py   # any command in the container
```

Logs: `ablation/slurm/logs/<date>/<time>_<job name>_<job id>.log`, written by SLURM itself so tools like lazyslurm find them.

**Changing dependencies:** edit `ablation/pixi.toml`, refresh the lock with the same pixi version as the image, commit both, then rebuild:

```bash
cd ablation && apptainer exec docker://ghcr.io/prefix-dev/pixi:0.40.3 pixi update --no-install   # on DAIC
```
