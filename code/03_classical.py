"""
03_classical.py -- classical forecasters with per-series parameter selection on the
training window, evaluated both IN-SAMPLE (training fit) and OUT-OF-SAMPLE
(rolling-origin one-step-ahead over the hold-out window). Produces a per-series
results table used for the in-sample/OOS inversion and the by-band analysis.

Output: results/<ds>_classical.parquet
"""
import os, numpy as np, pandas as pd
import lib

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results'); os.makedirs(RES, exist_ok=True)
SPLIT = {'m5': 26, 'or2': 14}          # hold-out window length (weeks)

# Tuning grids live in lib.py so that this script and 06_robustness.py cannot drift apart.
SES_A, CRO_A, SMA_K, ADIDA_K = lib.SES_A, lib.CRO_A, lib.SMA_K, lib.ADIDA_K

def select_lean(build, params, Y, tr, te, scale):
    """Same per-series training-MAE selection as select(), but evaluates one candidate at
    a time and keeps only the running best. Used for the temporal-aggregation methods,
    whose grids are large enough that holding every forecast matrix at once is wasteful."""
    n = Y.shape[0]
    best_tr = np.full(n, np.inf, dtype=np.float32)
    sel = np.full(n, -1, dtype=int)
    keep = {k: np.full(n, np.nan, dtype=np.float32)
            for k in ('insample_mae', 'oos_mae', 'oos_rmse', 'oos_bias')}
    for j, p in enumerate(params):
        F = build(p)
        tmae, _ = lib.mae_over(F, Y, tr)
        xmae, _ = lib.mae_over(F, Y, te)
        xrmse = lib.rmse_over(F, Y, te)
        xbias = lib.bias_over(F, Y, te)
        better = np.isfinite(tmae) & (tmae < best_tr)
        best_tr = np.where(better, tmae, best_tr)
        keep['insample_mae'] = np.where(better, tmae, keep['insample_mae'])
        keep['oos_mae'] = np.where(better, xmae, keep['oos_mae'])
        keep['oos_rmse'] = np.where(better, xrmse, keep['oos_rmse'])
        keep['oos_bias'] = np.where(better, xbias, keep['oos_bias'])
        sel = np.where(better, j, sel)
        del F
    keep['sel_idx'] = sel
    keep['mase'] = keep['oos_mae'] / scale
    return keep


def select(F_list, params, Y, fa, tr, te, scale):
    """Given forecasts for each candidate param, pick per series the param with the
    lowest training-window MAE, then return that param's in-sample & OOS metrics."""
    n = Y.shape[0]
    train_mae = np.full((n, len(params)), np.nan, dtype=np.float32)
    test_mae  = np.full((n, len(params)), np.nan, dtype=np.float32)
    test_rmse = np.full((n, len(params)), np.nan, dtype=np.float32)
    test_bias = np.full((n, len(params)), np.nan, dtype=np.float32)
    for j, F in enumerate(F_list):
        train_mae[:, j], _ = lib.mae_over(F, Y, tr)
        test_mae[:, j], _   = lib.mae_over(F, Y, te)
        test_rmse[:, j]     = lib.rmse_over(F, Y, te)
        test_bias[:, j]     = lib.bias_over(F, Y, te)
    sel = np.nanargmin(np.where(np.isnan(train_mae), np.inf, train_mae), axis=1)
    ar = np.arange(n)
    return dict(sel_param=np.array(params)[sel],
                insample_mae=train_mae[ar, sel],
                oos_mae=test_mae[ar, sel],
                oos_rmse=test_rmse[ar, sel],
                oos_bias=test_bias[ar, sel],
                mase=test_mae[ar, sel] / scale)

for ds in ['m5', 'or2']:
    panel = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    split = T - SPLIT[ds]
    tr, te = lib.col_slices(Y, split)
    scale = lib.naive_scale(Y, fa, split)
    print(f'\n[{ds}] n={n} T={T} split={split} test_weeks={SPLIT[ds]}')

    res = pd.DataFrame({'unique_id': uids})
    cls = pd.read_parquet(fr'{DATA}\{ds}_classification.parquet')
    res = res.merge(cls[['unique_id', 'class', 'n_nonzero', 'ADI', 'CV2']], on='unique_id')
    res['scale'] = scale

    # training-window activity (for eligibility + bands)
    train_nnz = np.array([np.nansum(Y[i, fa[i]:split] > 0) for i in range(n)])
    train_len = np.array([np.sum(~np.isnan(Y[i, :split])) for i in range(n)])
    res['train_nnz'] = train_nnz
    # out-of-sample mean weekly demand (for volume-band analysis)
    res['oos_mean'] = np.nanmean(Y[:, te], axis=1)

    # ---- NAIVE ----
    Fn = lib.f_naive(Y, fa)
    res['naive_insample_mae'], _ = lib.mae_over(Fn, Y, tr)
    res['naive_oos_mae'], _ = lib.mae_over(Fn, Y, te)
    res['naive_oos_rmse'] = lib.rmse_over(Fn, Y, te)
    res['naive_oos_bias'] = lib.bias_over(Fn, Y, te)
    res['naive_mase'] = res['naive_oos_mae'] / res['scale']

    # ---- SMA / SES / CROSTON / SBA (per-series param selection) ----
    # select_lean evaluates one candidate at a time; with eleven-point grids on a 30,490 x 281
    # panel, holding every candidate forecast matrix at once is a needless 400 MB.
    for name, builder, grid, kw in [
        ('sma',     lambda p: lib.f_sma(Y, fa, p),                       SMA_K, {}),
        ('ses',     lambda p: lib.f_ses(Y, fa, p, split),               SES_A, {}),
        ('croston', lambda p: lib.f_croston(Y, fa, p, split, sba=False), CRO_A, {}),
        ('sba',     lambda p: lib.f_croston(Y, fa, p, split, sba=True),  CRO_A, {}),
        ('tsb',     lambda p: lib.f_tsb(Y, fa, p, split),                CRO_A, {}),
    ]:
        d = select_lean(builder, grid, Y, tr, te, scale)
        res[f'{name}_sel_param'] = np.array([grid[i] if i >= 0 else np.nan for i in d['sel_idx']])
        res[f'{name}_insample_mae']  = d['insample_mae']
        res[f'{name}_oos_mae']       = d['oos_mae']
        res[f'{name}_oos_rmse']      = d['oos_rmse']
        res[f'{name}_oos_bias']      = d['oos_bias']
        res[f'{name}_mase']          = d['mase']
        print(f'  {name:8s} mean MASE={np.nanmean(d["mase"]):.3f} '
              f'median MASE={np.nanmedian(d["mase"]):.3f}')

    # ---- ADIDA / MAPA (temporal aggregation) ----
    # ADIDA is tuned over the (bucket, alpha) grid; MAPA combines across buckets by
    # construction, so it is tuned over alpha alone, on the same grid SES gets.
    adida_grid = [(k, a) for k in ADIDA_K for a in SES_A]
    d = select_lean(lambda p: lib.f_adida(Y, fa, p[1], p[0], split),
                    adida_grid, Y, tr, te, scale)
    res['adida_sel_k']     = np.array([adida_grid[i][0] if i >= 0 else np.nan for i in d['sel_idx']])
    res['adida_sel_param'] = np.array([adida_grid[i][1] if i >= 0 else np.nan for i in d['sel_idx']])
    for c in ('insample_mae', 'oos_mae', 'oos_rmse', 'oos_bias', 'mase'):
        res[f'adida_{c}'] = d[c]
    print(f'  adida    mean MASE={np.nanmean(d["mase"]):.3f} '
          f'median MASE={np.nanmedian(d["mase"]):.3f}')

    d = select_lean(lambda a: lib.f_mapa(Y, fa, a, split), SES_A, Y, tr, te, scale)
    res['mapa_sel_param'] = np.array([SES_A[i] if i >= 0 else np.nan for i in d['sel_idx']])
    for c in ('insample_mae', 'oos_mae', 'oos_rmse', 'oos_bias', 'mase'):
        res[f'mapa_{c}'] = d[c]
    print(f'  mapa     mean MASE={np.nanmean(d["mase"]):.3f} '
          f'median MASE={np.nanmedian(d["mase"]):.3f}')

    res.to_parquet(fr'{RES}\{ds}_classical.parquet', index=False)
    print(f'  saved {ds}_classical.parquet  rows={len(res)}')
