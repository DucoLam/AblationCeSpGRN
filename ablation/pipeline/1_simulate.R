# Simulate one paired scRNA-seq + scATAC-seq dataset with scMultiSim, following paper Note 1.8.
#
# Settings decoded from upstream's dataset names, simulated_8000_20_10_100_{fp}_{seed}_0_4:
#   8000 cells, 20 changing edges, 10 cells per step, 100 steps, weight.mean 0, weight.sd 4.
#   GRN_params_100 with default options gives the paper's 110 genes and 330 regions.
# The tree and number of CIFs follow scMultiSim's own dynamic-GRN vignette.
#
# Noise (fp) only affects the prior, so one simulation per seed serves both noise levels.
#
# Usage (from the repo root): Rscript ablation/pipeline/1_simulate.R <seed> <out_dir> [num_cells] [atac_p_zero] [profile]
# atac_p_zero is scMultiSim's share of zeros in the ATAC data (default 0.8): it sets how many regions are open.
#
# profile "authors" uses the settings of the authors' own simulate_scmultisim.R (received 2026-11-21) instead of
# our reconstruction: 500 CIFs, intrinsic.noise 0.5, 10 steps of 100 cells per epoch (the dataset name is
# {changing edges}_{steps}_{cells per step}), create.tf.edges = TRUE, and scMultiSim's default atac.p_zero.
# It also writes the authors' "corrected" ground truth (grn_edges_corrected.tsv), computed with their code.
# If ablation/data/rlib_authors exists, scMultiSim is loaded from there (the authors' commit 8dc531f).

args <- commandArgs(trailingOnly = TRUE)
profile <- if (length(args) >= 5) args[5] else "rebuild"
stopifnot(profile %in% c("rebuild", "authors"))
if (profile == "authors" && dir.exists("ablation/data/rlib_authors")) {
  .libPaths(c(normalizePath("ablation/data/rlib_authors"), .libPaths()))
}
suppressPackageStartupMessages(library(scMultiSim))
cat("scMultiSim", as.character(packageVersion("scMultiSim")), "from", find.package("scMultiSim"), "|", R.version.string, "\n")

seed <- as.integer(args[1])
out_dir <- args[2]
num_cells <- if (length(args) >= 3) as.integer(args[3]) else 8000L
atac_p_zero <- if (length(args) >= 4) as.numeric(args[4]) else 0.8
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

data(GRN_params_100)
set.seed(seed)

if (profile == "authors") {
  # the authors' options, verbatim (their list2() call), with 20 changing edges, 10 steps, 100 cells per step
  options <- list(
    rand.seed = seed,
    GRN = GRN_params_100,
    num.cells = num_cells,
    num.cifs = 500,
    tree = Phyla1(),
    diff.cif.fraction = 0.8,
    do.velocity = FALSE,
    dynamic.GRN = list(
      num.steps = 10,
      cell.per.step = 100,
      num.changing.edges = 20,
      create.tf.edges = TRUE,
      weight.mean = 0,
      weight.sd = 4
    ),
    intrinsic.noise = 0.5
  )
} else {
  options <- list(
    rand.seed = seed,
    GRN = GRN_params_100,
    num.cells = num_cells,
    num.cifs = 20,
    tree = Phyla1(),
    diff.cif.fraction = 0.8,
    do.velocity = FALSE,
    atac.p_zero = atac_p_zero,
    dynamic.GRN = list(
      seed = seed,
      num.changing.edges = 20,
      cell.per.step = 10,
      num.steps = 100,
      weight.mean = 0,
      weight.sd = 4
    )
  )
}

res <- sim_true_counts(options)

# scMultiSim renames GRN genes to 1..n: GRN matrix rows are genes in count-matrix order,
# and its column names are the regulators' gene indices.
n_genes <- nrow(res$counts)
grn1 <- res$cell_specific_grn[[1]]
stopifnot(nrow(grn1) == n_genes)

write_tsv <- function(x, name, ...) {
  write.table(x, file.path(out_dir, name), sep = "\t", quote = FALSE, ...)
}

# Expression and accessibility before technical noise ("true" counts, as upstream uses)
write_tsv(res$counts, "counts_rna_true.tsv", col.names = NA)
write_tsv(res$atacseq_data, "counts_atac_true.tsv", col.names = NA)
write_tsv(res$cell_meta, "meta_cells.tsv", row.names = FALSE)

# Cross-modality matrices: region x gene (columns in gene order) and scMultiSim's own region x TF
write_tsv(res$region_to_gene, "region_to_gene.tsv", row.names = FALSE, col.names = FALSE)
if (!is.null(res$region_to_tf)) write_tsv(res$region_to_tf, "region_to_tf.tsv", row.names = FALSE, col.names = FALSE)

# Regulators as 1-based gene indices, in the column order of region_to_tf and the GRN matrices
regulators <- as.integer(colnames(grn1))
stopifnot(!anyNA(regulators), all(regulators >= 1 & regulators <= n_genes))
write_tsv(data.frame(regulator = regulators), "regulators.tsv", row.names = FALSE)

# Cell-specific ground-truth GRNs as a long table: cell, target, regulator (1-based gene indices), weight
edge_table <- function(grns) {
  edges <- do.call(rbind, lapply(seq_along(grns), function(i) {
    m <- grns[[i]]
    stopifnot(nrow(m) == n_genes, identical(colnames(m), colnames(grn1)))
    nz <- which(m != 0, arr.ind = TRUE)
    data.frame(
      cell = rep(i, nrow(nz)),
      target = nz[, 1],
      regulator = as.integer(colnames(m)[nz[, 2]]),
      weight = m[nz]
    )
  }))
  stopifnot(!anyNA(edges))
  edges
}
write_tsv(edge_table(res$cell_specific_grn), "grn_edges.tsv", row.names = FALSE)

if (profile == "authors") {
  # The authors' ground truth: only the edges reachable through an open region are kept.
  # This loop is their code (simulate_scmultisim.R), without the noise and prior lines;
  # 2_build_dataset.py --noise authors recomputes it and checks that both agree.
  counts.atac.true <- (res$atacseq_data > 0)
  corrected <- lapply(seq_len(num_cells), function(cell) {
    region_to_tf <- (res$region_to_gene %*% res$cell_specific_grn[[cell]] > 0)
    region_accessible <- counts.atac.true[, cell]
    dim(region_accessible) <- c(length(region_accessible), 1)
    region_to_tf.accessible <- region_accessible[, rep(1, dim(region_to_tf)[2])] * region_to_tf
    grn.mask <- (t(res$region_to_gene) %*% region_to_tf.accessible > 0)
    out <- grn.mask * res$cell_specific_grn[[cell]]
    colnames(out) <- colnames(grn1)
    out
  })
  write_tsv(edge_table(corrected), "grn_edges_corrected.tsv", row.names = FALSE)
}

cat("Simulated", ncol(res$counts), "cells,", nrow(res$counts), "genes,",
    nrow(res$region_to_gene), "regions into", out_dir, "\n")
