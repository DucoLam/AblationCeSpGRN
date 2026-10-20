"""
Per-cell scoring. Upstream's scMultiSim scripts import this module, but it was never published.
calc_scores_para scores every cell with upstream's own BEELINE metrics (bmk_beeline.py) and
returns one row per cell, with the column names upstream's plotting code uses.
"""
from multiprocessing import Pool

import numpy as np
import pandas as pd

from bmk_beeline import compute_auc_abs, compute_eprec_abs


def _score_one(pair):
    G_inf, G_gt = pair
    return compute_auc_abs(G_inf, G_gt), compute_eprec_abs(G_inf, G_gt)


def calc_scores_para(thetas_inf, thetas_gt, interval=None, model=None, bandwidth=None,
                     truncate_param=None, lamb=None, beta=None, njobs=1):
    ncells = thetas_gt.shape[0]
    cells = np.arange(0, ncells, interval if interval else 1)
    # an inferred graph of shape (1, g, g) is one population-level GRN, scored against every cell
    infer = (lambda t: thetas_inf[0]) if thetas_inf.shape[0] == 1 else (lambda t: thetas_inf[t])

    with Pool(njobs) as pool:
        scores = pool.map(_score_one, [(infer(t), thetas_gt[t]) for t in cells], chunksize=64)

    return pd.DataFrame({
        "time": cells,
        "model": model,
        "bandwidth": bandwidth,
        "truncate_param": truncate_param,
        "lambda": lamb,
        "beta": beta,
        "AUPRC (abs)": [s[0] for s in scores],
        "Early Precision (abs)": [s[1] for s in scores],
    })
