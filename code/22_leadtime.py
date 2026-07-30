"""
22_leadtime.py -- lead-time sensitivity for the classical forecasters.

Motivation. Croston and SBA estimate a demand RATE (mean size over mean interval) whose
intended use is lead-time demand, not a one-step point forecast. Teunter and Duncan (2009)
report that per-period error measures are inappropriate for intermittent demand and that
under service-level and stock-holding evaluation Croston-type methods beat the moving
average and simple exponential smoothing. This script re-scores the five classical methods
on cumulative L-week demand so the paper can state how much of its one-step ranking is a
property of the horizon.

All five methods have a flat forecast function (a level or a rate), so the cumulative
L-step forecast from origin t is L * f_(t+1). The gradient-boosted and neural models are
one-step models and cannot be extended without recursive simulation, so they are excluded;
the question here is specifically the Croston family against the other classical methods.

Writes results/{ds}_leadtime.csv
"""
import os
import numpy as np, pandas as pd
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data')
RES = os.path.join(ROOT, 'results')

SPLIT = {'m5': 26, 'or2': 14}
LEADS = {'m5': [1, 2, 4, 8, 13, 26], 'or2': [1, 2, 4, 7, 14]}
ORDER = ['Naive', 'SMA', 'SES', 'Croston', 'SBA']


def build(ds):
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    T = Y.shape[1]
    split = T - SPLIT[ds]
    cl = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet')).set_index('unique_id').reindex(uids)

    def per_series(fn, params):
        """Run a vectorised forecaster once per distinct selected parameter."""
        F = np.full_like(Y, np.nan)
        pv = params.to_numpy()
        for p in np.unique(pv[~pd.isna(pv)]):
            m = pv == p
            F[m] = fn(p)[m]
        return F

    F = {
        'Naive':   lib.f_naive(Y, fa),
        'SMA':     per_series(lambda k: lib.f_sma(Y, fa, int(k)), cl['sma_sel_param']),
        'SES':     per_series(lambda a: lib.f_ses(Y, fa, float(a), split), cl['ses_sel_param']),
        'Croston': per_series(lambda a: lib.f_croston(Y, fa, float(a), split, sba=False), cl['croston_sel_param']),
        'SBA':     per_series(lambda a: lib.f_croston(Y, fa, float(a), split, sba=True), cl['sba_sel_param']),
    }
    return Y, fa, split, T, F, cl['train_nnz'].to_numpy()


def leadtime(Y, fa, split, T, F, L):
    """Mean absolute error on cumulative L-week demand across rolling test-window origins,
    scaled per series by the in-sample MAE of a naive forecast of L-block cumulative demand.
    Only fully observed blocks are scored."""
    n = Y.shape[0]
    valid = ~np.isnan(Y)
    cs = np.cumsum(np.where(valid, np.nan_to_num(Y, nan=0.0), 0.0), axis=1)
    cn = np.cumsum(valid.astype(int), axis=1)
    den = np.zeros(n)
    acc = {k: np.zeros(n) for k in F}
    for t in range(split - 1, T - L):
        a = cs[:, t + L] - cs[:, t]
        c = cn[:, t + L] - cn[:, t]
        ok = c == L
        den += ok
        for k, Fm in F.items():
            acc[k] += np.where(ok, np.nan_to_num(np.abs(Fm[:, t + 1] * L - a), nan=0.0), 0.0)
    # in-sample scale: naive forecast of L-block cumulative demand, training window only
    sc = np.full(n, np.nan)
    for i in range(n):
        s = Y[i, fa[i]:split]
        s = s[~np.isnan(s)]
        if len(s) >= 2 * L:
            b = np.convolve(s, np.ones(L), mode='valid')
            dd = np.abs(np.diff(b))
            if len(dd):
                sc[i] = dd.mean()
    out = {}
    for k in F:
        mae = np.where(den > 0, acc[k] / np.maximum(den, 1), np.nan)
        out[k] = mae / sc
    return out, sc, den


for ds in ('m5', 'or2'):
    print(f'\n[{ds}] building one-step forecasts from stored per-series parameters...')
    Y, fa, split, T, F, tnnz = build(ds)

    # sanity: L=1 must reproduce the published one-step mean MASE
    sc1 = lib.naive_scale(Y, fa, split)
    te = np.arange(split, T)
    e1 = np.isfinite(sc1) & (sc1 > 0) & (tnnz >= 2)
    print(f'  sanity, one-step mean MASE (n={int(e1.sum())}):')
    for k in ORDER:
        mae, _ = lib.mae_over(F[k], Y, te)
        print(f'    {k:<9}{np.nanmean((mae / sc1)[e1]):.3f}')

    rows = []
    for L in LEADS[ds]:
        res, sc, den = leadtime(Y, fa, split, T, F, L)
        e = np.isfinite(sc) & (sc > 0) & (den > 0) & (tnnz >= 2)
        for k in F:
            e &= np.isfinite(res[k])
        row = {'lead_weeks': L, 'n': int(e.sum()), 'origins': int(max(1, T - L - (split - 1)))}
        for k in ORDER:
            row[k] = round(float(np.mean(res[k][e])), 3)
        rank = sorted(ORDER, key=lambda k: row[k])
        row['best'] = rank[0]
        row['Croston_rank'] = rank.index('Croston') + 1
        row['SBA_rank'] = rank.index('SBA') + 1
        for k in ('SES', 'Croston', 'SBA'):
            row[f'{k}_over_Naive'] = round(row[k] / row['Naive'], 3)
        rows.append(row)
        print(f"  L={L:>2}  n={row['n']:>6}  origins={row['origins']:>2}  "
              + '  '.join(f'{k}={row[k]:.3f}' for k in ORDER)
              + f"   best={row['best']}  Croston {row['Croston_rank']}/5")

    df = pd.DataFrame(rows)
    out = os.path.join(RES, f'{ds}_leadtime.csv')
    df.to_csv(out, index=False)
    print(f'  saved {out}')

print('\nNote: absolute values are not comparable across lead times, because the scaling')
print('denominator is recomputed at each L. Compare rankings within a row, and the')
print('*_over_Naive columns across rows.')
