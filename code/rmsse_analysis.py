"""
rmsse_analysis.py -- RMSSE sensitivity analysis (the M5 competition's official metric).
MAE-based measures reward the per-series MEDIAN, which is zero on intermittent series and
so favours zero-forecasters over mean-rate estimators (Croston/SBA, Tweedie GBM). RMSSE is
squared-error based and rewards the conditional MEAN, the inventory-relevant functional:
  RMSSE_i = OOS_RMSE_i / sqrt( mean_t (y_t - y_{t-1})^2 )   over the training window.
Scopes: (a) six core methods, full eligible set; (b) eight methods (incl. NHITS/DeepAR),
neural-eligible subset (requires *_neural.parquet with *_oos_rmse columns).
Also runs MCB/Nemenyi on RMSSE ranks. Output: results/rmsse.json
"""
import os, json
import numpy as np, pandas as pd
import lib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, RES = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'results')
Q05 = {2: 2.772, 3: 3.314, 4: 3.633, 5: 3.858, 6: 4.030, 7: 4.170, 8: 4.286,
       9: 4.387, 10: 4.474, 11: 4.552, 12: 4.622, 13: 4.685,
       14: 4.743}   # studentized range, alpha=.05, df=inf

CORE = [('naive', 'Naive'), ('sma', 'SMA'), ('ses', 'SES'),
        ('croston', 'Croston'), ('sba', 'SBA'), ('tsb', 'TSB'),
        ('adida', 'ADIDA'), ('mapa', 'MAPA'),
        ('lgbm', 'LightGBM (global)')]

def naive_scale2(Y, fa, split):
    """in-sample mean SQUARED one-step naive error over the training window."""
    n, _ = Y.shape
    s2 = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        tr = Y[i, fa[i]:split]
        tr = tr[~np.isnan(tr)]
        if len(tr) >= 2:
            d = np.diff(tr)
            s2[i] = float(np.mean(d ** 2))
    return s2

def mcb(M, labels):
    ranks = M.rank(axis=1, method='average')
    rbar = ranks.mean(axis=0).values
    N, K = M.shape
    cd = Q05[K] / np.sqrt(2) * np.sqrt(K * (K + 1) / (6.0 * N))
    best = float(rbar.min())
    return {'N': int(N), 'critical_distance': round(float(cd), 3),
            'mean_ranks': {l: round(float(r), 3) for l, r in zip(labels, rbar)},
            'sig_worse_than_best': {l: bool(r - best > cd) for l, r in zip(labels, rbar)}}

SPLIT = {'m5': 26, 'or2': 14}
out = {}
for ds in ['m5', 'or2']:
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    split = Y.shape[1] - SPLIT[ds]
    s2 = pd.Series(naive_scale2(Y, fa, split), index=uids, name='scale2')

    c = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))
    l = pd.read_parquet(os.path.join(RES, f'{ds}_lgbm.parquet'))
    df = c.merge(l, on='unique_id', how='left').merge(s2, left_on='unique_id', right_index=True)
    df = df[np.isfinite(df['scale']) & (df['scale'] > 0) & (df['train_nnz'] >= 2)
            & np.isfinite(df['scale2']) & (df['scale2'] > 0)]
    rt = np.sqrt(df['scale2'].values)
    labels6 = [lab for _, lab in CORE]
    R6c = pd.DataFrame({lab: df[f'{k}_oos_rmse'].values / rt for k, lab in CORE})
    R6c['class'] = df['class'].values
    R6c = R6c.replace([np.inf, -np.inf], np.nan).dropna(subset=labels6)
    R6 = R6c[labels6]
    res = {'core6_fullset': {
        'mean_RMSSE': {m: round(float(R6[m].mean()), 3) for m in labels6},
        'median_RMSSE': {m: round(float(R6[m].median()), 3) for m in labels6},
        **{'mcb': mcb(R6, labels6)}}}
    byc = {}
    for cl in ['Smooth', 'Intermittent', 'Erratic', 'Lumpy']:
        sub6 = R6c.loc[R6c['class'] == cl, labels6]
        if len(sub6):
            byc[cl] = {'n': int(len(sub6)), **{m: round(float(sub6[m].mean()), 3) for m in labels6}}
    res['core6_by_class'] = byc

    npq = os.path.join(RES, f'{ds}_neural.parquet')
    nd = pd.read_parquet(npq)
    if 'nhits_oos_rmse' in nd.columns:
        sub = df.merge(nd[['unique_id', 'nhits_oos_rmse', 'deepar_oos_rmse']], on='unique_id', how='inner')
        sub = sub[sub['nhits_oos_rmse'].notna()]
        rt8 = np.sqrt(sub['scale2'].values)
        cols = list(CORE) + [('nhits', 'NHITS'), ('deepar', 'DeepAR')]
        R8 = pd.DataFrame({lab: sub[f'{k}_oos_rmse'].values / rt8 for k, lab in cols}).replace(
            [np.inf, -np.inf], np.nan).dropna()
        res['all8_subset'] = {
            'mean_RMSSE': {m: round(float(R8[m].mean()), 3) for m in R8.columns},
            'median_RMSSE': {m: round(float(R8[m].median()), 3) for m in R8.columns},
            'mcb': mcb(R8, list(R8.columns))}
    else:
        res['all8_subset'] = None
        print(f'[{ds}] neural parquet lacks RMSE columns yet -- core6 only')
    out[ds] = res
    a = res['core6_fullset']
    print(f"[{ds}] core6 mean RMSSE: " + '  '.join(f"{m}={v:.3f}" for m, v in
          sorted(a['mean_RMSSE'].items(), key=lambda x: x[1])))
    print(f"[{ds}] core6 MCB ranks (N={a['mcb']['N']}, CD={a['mcb']['critical_distance']}): "
          + '  '.join(f"{m}={v}" for m, v in sorted(a['mcb']['mean_ranks'].items(), key=lambda x: x[1])))

with open(os.path.join(RES, 'rmsse.json'), 'w') as f:
    json.dump(out, f, indent=2)
print('saved results/rmsse.json')
