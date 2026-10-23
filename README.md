# AblationCeSpGRN

Ablation study of CeSpGRN, a method for inferring cell-specific gene regulatory networks. We test whether its accuracy gain with scATAC-seq comes from the method or from the ATAC prior it is given.

- **[`research.md`](research.md):** the question, what we found, results and plan.
- **[`journal.md`](journal.md):** the working log: every finding with dates, job IDs and code references.
- **[`ablation/`](ablation/README.md):** all of our code, what runs in which order, and how to run it on DAIC.
- **Everything else** is upstream [PeterZZQ/CeSpGRN](https://github.com/PeterZZQ/CeSpGRN), forked at `v1.0.0`; its README is [`README.upstream.md`](README.upstream.md). `git diff upstream/master -- src test demo.py` shows the few fixes we made to it.

## CeSpGRN in short

Zhang, Z., Han, J., Song, L., & Zhang, X. (2026). CeSpGRN: inferring cell-specific gene regulatory networks from single-cell multi-omics and spatial data. *Bioinformatics*, 42(6), btag324. https://doi.org/10.1093/bioinformatics/btag324 (preprint: [bioRxiv 2022.03.03.482887](https://doi.org/10.1101/2022.03.03.482887))

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

| Path | Contents |
|---|---|
| `src/g_admm.py` | Covariance estimation (`est_cov`, weighted Kendall's τ) and the ADMM solvers: `G_admm_minibatch` (no prior) and `G_admm_mask` (with prior) |
| `src/kernel.py` | Kernel construction (`calc_kernel_neigh` and variants) |
| `src/bmk_beeline.py` | Evaluation metrics: AUPRC (`compute_auc_abs`) and early precision (`compute_eprec_abs`) |
| `src/torch_sqrtm.py` | Matrix square root in PyTorch |
| `demo.py` | End-to-end example |
| `test/scripts_scmultisim/` | Upstream's simulated-data experiments; they need data and modules that were never published |
| `data/` | Upstream's example datasets |
