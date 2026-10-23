# Simulate one paired scRNA-seq + scATAC-seq dataset with scMultiSim, following paper Note 1.8.
#
# Settings decoded from upstream's dataset names, simulated_8000_20_10_100_{fp}_{seed}_0_4:
#   8000 cells, 20 changing edges, 10 cells per step, 100 steps, weight.mean 0, weight.sd 4.
#   GRN_params_100 with default options gives the paper's 110 genes and 330 regions.
# The tree and number of CIFs follow scMultiSim's own dynamic-GRN vignette.
#
# Noise (fp) only affects the prior, so one simulation per seed serves both noise levels.
#
# Usage (from the repo root): Rscript ablation/pipeline/1_simulate.R <seed> <out_dir> [num_cells]

suppressPackageStartupMessages(library(scMultiSim))

args <- commandArgs(trailingOnly = TRUE)
seed <- as.integer(args[1])
out_dir <- args[2]
num_cells <- if (length(args) >= 3) as.integer(args[3]) else 8000L
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

data(GRN_params_100)
set.seed(seed)

options <- list(
  rand.seed = seed,
  GRN = GRN_params_100,
  num.cells = num_cells,
  num.cifs = 20,
  tree = Phyla1(),
  diff.cif.fraction = 0.8,
  do.velocity = FALSE,
  dynamic.GRN = list(
    seed = seed,
    num.changing.edges = 20,
    cell.per.step = 10,
    num.steps = 100,
    weight.mean = 0,
    weight.sd = 4
  )
)

res <- sim_true_counts(options)

# scMultiSim renames GRN genes to 1..n: GRN matrix rows are genes in count-matrix order,
# and its column names are the regulators' gene indices.
n_genes <- nrow(res$counts)
stopifnot(nrow(res$.grn$geff) == n_genes)

write_tsv <- function(x, name, ...) {
  write.table(x, file.path(out_dir, name), sep = "\t", quote = FALSE, ...)
}

# Expression and accessibility before technical noise ("true" counts, as upstream uses)
write_tsv(res$counts, "counts_rna_true.tsv", col.names = NA)
write_tsv(res$atacseq_data, "counts_atac_true.tsv", col.names = NA)
write_tsv(res$cell_meta, "meta_cells.tsv", row.names = FALSE)

# Cross-modality matrices: region x gene (columns in gene order) and scMultiSim's own region x TF
write_tsv(res$region_to_gene, "region_to_gene.tsv", row.names = FALSE, col.names = FALSE)
write_tsv(res$region_to_tf, "region_to_tf.tsv", row.names = FALSE, col.names = FALSE)

# Regulators as 1-based gene indices, in the column order of region_to_tf and the GRN matrices
regulators <- as.integer(colnames(res$.grn$geff))
stopifnot(!anyNA(regulators), all(regulators >= 1 & regulators <= n_genes))
write_tsv(data.frame(regulator = regulators), "regulators.tsv", row.names = FALSE)

# Cell-specific ground-truth GRNs as a long table: cell, target, regulator (1-based gene indices), weight
edges <- do.call(rbind, lapply(seq_along(res$cell_specific_grn), function(i) {
  m <- res$cell_specific_grn[[i]]
  stopifnot(nrow(m) == n_genes)
  nz <- which(m != 0, arr.ind = TRUE)
  data.frame(
    cell = i,
    target = nz[, 1],
    regulator = as.integer(colnames(m)[nz[, 2]]),
    weight = m[nz]
  )
}))
stopifnot(!anyNA(edges))
write_tsv(edges, "grn_edges.tsv", row.names = FALSE)

cat("Simulated", ncol(res$counts), "cells,", nrow(res$counts), "genes,",
    nrow(res$region_to_gene), "regions into", out_dir, "\n")
