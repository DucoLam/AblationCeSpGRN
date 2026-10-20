"""
Parallel covariance estimation. Upstream's scMultiSim scripts import this module, but it was
never published. est_cov_para follows the commented-out version in g_admm.py and runs the same
per-cell loop as g_admm.est_cov, split over processes.
"""
import numpy as np
import torch
from multiprocessing import get_context

from g_admm import weighted_kendall_tau, isPSD, find_clostest_PSD


def _est_cov(setting):
    # K_rows holds only this chunk's rows of K_trun, to keep the copy per process small
    X, K_rows, weighted_kt = setting
    torch.set_num_threads(1)
    X = torch.FloatTensor(X)
    ngenes = X.shape[1]
    empir_cov = torch.zeros(K_rows.shape[0], ngenes, ngenes)

    for t_idx in range(K_rows.shape[0]):
        weight = torch.FloatTensor(K_rows[t_idx, :])
        if not weighted_kt:
            weight = (weight > 0)
        for i in range(ngenes):
            for j in range(i, ngenes):
                if i != j:
                    kt = weighted_kendall_tau(X[(weight > 0), i].squeeze(), X[(weight > 0), j].squeeze(), weight[weight > 0])
                    empir_cov[t_idx, i, j] = torch.sin(np.pi / 2 * kt)
                else:
                    empir_cov[t_idx, i, j] = 1

        empir_cov[t_idx] = empir_cov[t_idx] + empir_cov[t_idx].T - torch.diag(torch.diag(empir_cov[t_idx]))
        Flag, min_eig = isPSD(empir_cov[t_idx])
        if not Flag:
            empir_cov[t_idx] = find_clostest_PSD(empir_cov[t_idx])
            Flag, min_eig = isPSD(empir_cov[t_idx])
            assert Flag

    return empir_cov.numpy()


def est_cov_para(X, K_trun, weighted_kt=True, njobs=1):
    """Cell-specific covariance from (weighted) Kendall's tau, as g_admm.est_cov, over njobs processes."""
    ntimes = X.shape[0]
    bounds = np.linspace(0, ntimes, njobs + 1).astype(int)
    settings = [(X, K_trun[t1:t2], weighted_kt) for t1, t2 in zip(bounds[:-1], bounds[1:]) if t2 > t1]
    print("calculating covariance matrices")
    with get_context("spawn").Pool(njobs) as pool:
        empir_cov = pool.map(_est_cov, settings)
    return np.concatenate(empir_cov, axis=0)


def est_cov_ggm_para(X, K_trun, njobs=1):
    raise NotImplementedError("GGM covariance (paper Fig. S3a) is not reconstructed yet")
