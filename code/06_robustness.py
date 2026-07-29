"""
06_robustness.py -- stability of the method ranking across alternative hold-out
horizons. Re-runs the classical forecasters AND the global LightGBM model at three
test-window lengths per dataset and records mean OOS MASE per method.

Output: results/<ds>_robustness.csv
"""
import os, sys, numpy as np, pandas as pd, lib

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
DATASETS = [d for d in sys.argv[1:] if d in ('m5', 'or2')] or ['m5', 'or2']
HORIZONS = {'m5': [13, 26, 39], 'or2': [8, 14, 20]}
VAL = {'m5': 8, 'or2': 6}
SES_A = [0.05, 0.1, 0.2, 0.3, 0.4]; CRO_A = [0.01, 0.05, 0.1, 0.2, 0.3]; SMA_K = [2, 3, 4]

def _mean_mase(mae, scale, elig):
    m = np.where(elig, mae / np.where((scale > 0) & np.isfinite(scale), scale, np.nan), np.nan)
    m[~np.isfinite(m)] = np.nan
    return float(np.nanmean(m))

def eligibility(Y, fa, split, scale):
    """Same per-split filter as the primary analysis (03/05): finite positive scale AND at
    least two non-zero training weeks — so the primary-split row of Table 5 matches Table 3."""
    n, T = Y.shape
    col = np.arange(T)[None, :]
    active = (col >= fa[:, None]) & (col < split)
    train_nnz = ((np.nan_to_num(Y, nan=0.0) > 0) & active).sum(axis=1)
    return np.isfinite(scale) & (scale > 0) & (train_nnz >= 2)

def classical_mase(Y, fa, split, scale, elig):
    tr, te = lib.col_slices(Y, split)
    out = {}
    Fn = lib.f_naive(Y, fa)
    out['Naive'] = _mean_mase(lib.mae_over(Fn, Y, te)[0], scale, elig)
    for name, builder, grid in [
        ('SMA',     lambda p: lib.f_sma(Y, fa, p), SMA_K),
        ('SES',     lambda p: lib.f_ses(Y, fa, p, split), SES_A),
        ('Croston', lambda p: lib.f_croston(Y, fa, p, split, sba=False), CRO_A),
        ('SBA',     lambda p: lib.f_croston(Y, fa, p, split, sba=True), CRO_A)]:
        tmae = []; xmae = []
        for p in grid:
            F = builder(p)
            tmae.append(lib.mae_over(F, Y, tr)[0]); xmae.append(lib.mae_over(F, Y, te)[0])
        tmae = np.column_stack(tmae); xmae = np.column_stack(xmae)
        sel = np.nanargmin(np.where(np.isnan(tmae), np.inf, tmae), axis=1)
        sel_mae = xmae[np.arange(len(sel)), sel]
        out[name] = _mean_mase(sel_mae, scale, elig)
    return out

for ds in DATASETS:
    panel  = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')
    static = pd.read_parquet(fr'{DATA}\{ds}_static.parquet')
    Y, uids, fa = lib.build_matrix(panel)
    T = Y.shape[1]
    dfml, feats, cats = lib.add_ml_features(panel, static, ds)   # features computed once
    uid_to_scale = None
    rows = []
    PRIMARY = {'m5': 26, 'or2': 14}
    for H in HORIZONS[ds]:
        split = T - H
        scale = lib.naive_scale(Y, fa, split)
        elig = eligibility(Y, fa, split, scale)
        sc = pd.Series(scale, index=uids)
        el = pd.Series(elig, index=uids)
        row = {'test_weeks': H, **classical_mase(Y, fa, split, scale, elig)}
        # LightGBM, same eligibility filter. At the PRIMARY split, score the saved
        # 04_lgbm_global predictions so this row matches Table 3 by construction
        # (retraining here would differ by bagging RNG only).
        if H == PRIMARY[ds]:
            lg = pd.read_parquet(fr'{RES}\{ds}_lgbm.parquet').set_index('unique_id')['lgbm_mase']
            mase = lg.reindex(uids)
            mase = mase[el.values & np.isfinite(mase.values)]
        else:
            te, _ = lib.fit_predict_lgbm(dfml, feats, cats, split, VAL[ds])
            te['ae'] = (te['pred'] - te['y']).abs()
            mae = te.groupby('unique_id', observed=True)['ae'].mean()
            mase = (mae / sc.reindex(mae.index)).replace([np.inf, -np.inf], np.nan)
            mase = mase[el.reindex(mase.index).fillna(False)]
        row['LightGBM'] = float(np.nanmean(mase.values))
        row['LightGBM_median'] = float(np.nanmedian(mase.values))
        rows.append(row)
        print(f'[{ds}] H={H:>3}  ' + '  '.join(f'{k}={v:.3f}' for k, v in row.items() if k != 'test_weeks'))
    pd.DataFrame(rows).to_csv(fr'{RES}\{ds}_robustness.csv', index=False)
    print(f'  saved {ds}_robustness.csv')
