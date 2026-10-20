# AblationCeSpGRN

Ablation benchmark of CeSpGRN, a method for inferring cell-specific gene regulatory networks.

## Background

CeSpGRN: Zhang, Han, Song & Zhang, *Inferring cell-specific gene regulatory networks from single cell multi-omics and spatial data*, bioRxiv 2022.03.03.482887 (v3, 2023). Code: https://github.com/PeterZZQ/CeSpGRN

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

The environment is defined in `pixi.toml` and pinned in `pixi.lock`. Commit both.

**Locally:** `pixi install`, then `pixi run python ...`.

**On DAIC:** pixi is not installed there, so jobs run inside an Apptainer image (`container_pixi.def`) that holds the locked environment. Code is not baked in; it is mounted at run time, so only dependency changes need a rebuild.

```bash
# from the repo root, on DAIC
sbatch slurm/build_container.sh                 # builds ablation-cespgrn.sif (rerun after pixi.toml/pixi.lock change)
sbatch slurm/run.sh python path/to/script.py    # runs any command in the container
```

**Changing dependencies:** edit `pixi.toml`, then refresh the lock with the same pixi version as the image:

```bash
pixi update --no-install                                                                         # local pixi
podman run --rm -v "$PWD":/app -w /app ghcr.io/prefix-dev/pixi:0.40.3 pixi update --no-install  # or via podman/docker
apptainer exec docker://ghcr.io/prefix-dev/pixi:0.40.3 pixi update --no-install                # or on DAIC
```

## Usage

TODO

## Results

TODO
