# AblationCeSpGRN

Ablation benchmark of CeSpGRN, a method for inferring cell-specific gene regulatory networks.

> **Update (2026-10-20)**
> - This repo is now a fork of [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN). Upstream code is unchanged so far; `git diff upstream/master...main` shows everything we changed.
> - DAIC setup in place: pixi environment with PyTorch (CUDA 12.9) in an Apptainer image, SLURM scripts for building and running.
> - GPU queue on old DAIC is slow: most GPU nodes are drained for the move to the new DAIC environment (mid-October / early November).
> - Next: ablation list, simulated data (8000 cells, 110 genes), and the run scripts.

## Background

CeSpGRN: Zhang, Han, Song & Zhang, *Inferring cell-specific gene regulatory networks from single cell multi-omics and spatial data*, bioRxiv 2022.03.03.482887 (v3, 2023). Code: https://github.com/PeterZZQ/CeSpGRN

CeSpGRN infers one GRN per cell, assuming that GRNs change smoothly along a trajectory or across space. For each cell *i* it estimates a precision matrix Θᵢ (genes × genes) by solving, with ADMM (paper Eq. 2):

```
Θᵢ = argmin  − Σ_{j ∈ Nᵢ} Kᵢⱼ · ℓ_Θᵢ(Xⱼ)  +  λ‖Θᵢ‖₁  +  β‖Mᵢ ⊙ Θᵢ‖²_F
```

| Term | What it does | Hyperparameter |
|---|---|---|
| Kernel weight Kᵢⱼ | Borrows data from similar cells: Gaussian kernel on geodesic distance in a kNN graph of PCA space (or spatial distance) | bandwidth σ, neighbourhood size \|Nᵢ\| |
| Likelihood ℓ | Gaussian copula graphical model; covariance from a weighted Kendall's τ that masks zero (dropout) entries | — |
| Sparsity λ‖Θᵢ‖₁ | Keeps only strong edges | λ |
| Prior β‖Mᵢ ⊙ Θᵢ‖² | Penalises edges outside a prior GRN (from scATAC-seq or TF lists); Mᵢ = 1 − G_prior | β |

The output Θᵢ is turned into partial correlations Gᵢ(m,n) = −Θᵢ(m,n) / √(Θᵢ(m,m) Θᵢ(n,n)) as edge strengths.

### Upstream code

The original upstream README is kept as [README.upstream.md](README.upstream.md).

| Path | Contents |
|---|---|
| `src/g_admm.py` | Covariance estimation (`est_cov`, weighted Kendall's τ) and the ADMM solvers: `G_admm_minibatch` (no prior) and `G_admm_mask` (with prior) |
| `src/kernel.py` | Kernel construction (`calc_kernel_neigh` and variants) |
| `src/bmk_beeline.py` | Evaluation metrics, including AUPRC (`compute_auc`) |
| `src/torch_sqrtm.py` | Matrix square root in PyTorch |
| `demo.py` | End-to-end example |
| `test/scripts_scmultisim/` | Upstream's simulated-data experiments, including a hyperparameter sweep (`test_scmultisim_hyperparams.py`) |
| `data/` | Upstream's example datasets |

## Values
As noted from the Additional Supplementary Materials:
seeds = {0,1,2}
noise = {0.01, 0.1}
#cells = 8000
#genes = 110

Metrics (AUPRC and Early Precision) are as noted in [Pratapa et al., 2020]

## Ablations

TODO

## Setup

Everything runs on DAIC. The environment (Python, PyTorch with CUDA) is defined in `pixi.toml`, pinned in `pixi.lock`, and baked into an Apptainer image (`container_pixi.def`). Code is not baked in; it is mounted at run time, so only dependency changes need a rebuild.

```bash
# from the repo root, on DAIC
sbatch slurm/build_container.sh                             # builds ablation-cespgrn.sif (rerun after pixi.toml/pixi.lock change)
sbatch -J my-run slurm/run.sh python path/to/script.py      # runs any command in the container
sbatch -J my-run --gres=gpu:1 slurm/run.sh python ...       # same, on a GPU
```

Logs go to `slurm/logs/<date>/<time>_<job name>_<job id>.log`.

**Changing dependencies:** edit `pixi.toml`, refresh the lock with the same pixi version as the image, commit both, then rebuild:

```bash
apptainer exec docker://ghcr.io/prefix-dev/pixi:0.40.3 pixi update --no-install    # on DAIC
podman run --rm -v "$PWD":/app -w /app ghcr.io/prefix-dev/pixi:0.40.3 pixi update --no-install    # or locally with podman/docker
```

## Usage

TODO

## Results

TODO
