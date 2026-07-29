"""
05_aggregate.py -- assemble manuscript tables from per-series results:
  (a) overall OOS accuracy + Percentage-Best, all six methods
  (b) the in-sample vs out-of-sample inversion (classical methods)
  (c) accuracy by SBC demand class
  (d) Percentage-Best by out-of-sample demand-volume band
Writes CSV/JSON into results/ and prints a digest.
"""
import os, json, numpy as np, pandas as pd

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
CLASSICAL = ['naive', 'sma', 'ses', 'croston', 'sba']
ALL6 = CLASSICAL + ['lgbm']
LABEL = {'naive':'Naive','sma':'SMA','ses':'SES','croston':'Croston','sba':'SBA','lgbm':'LightGBM (AI)'}

def load(ds):
    c = pd.read_parquet(fr'{RES}\{ds}_classical.parquet')
    l = pd.read_parquet(fr'{RES}\{ds}_lgbm.parquet')
    df = c.merge(l, on='unique_id', how='left')
    elig = np.isfinite(df['scale']) & (df['scale'] > 0) & (df['train_nnz'] >= 2)
    df = df[elig].copy()
    return df

def pb(df, methods, col='_oos_mae'):
    """Percentage-Best with fractional tie-splitting: each of the k methods tied at the
    minimum error receives 1/k of that series' win. On sparse series many methods forecast
    exactly zero and tie; assigning ties by column order would overstate the first method,
    so ties are shared. Shares still sum to 100%."""
    M = np.column_stack([df[f'{m}{col}'].values for m in methods])
    valid = ~np.isnan(M).all(axis=1)
    Mv = np.where(np.isnan(M[valid]), np.inf, M[valid])
    mins = Mv.min(axis=1, keepdims=True)
    tied = Mv <= mins + 1e-12
    w = tied / tied.sum(axis=1, keepdims=True)
    share = 100.0 * w.mean(axis=0)
    return {methods[i]: round(float(share[i]), 1) for i in range(len(methods))}

digest = {}
for ds in ['m5', 'or2']:
    df = load(ds)
    n = len(df)
    # (a) overall
    rows = []
    pb_all = pb(df, ALL6, '_oos_mae')
    for m in ALL6:
        mase = df[f'{m}_mase']
        rows.append(dict(method=LABEL[m],
            mean_MASE=round(float(np.nanmean(mase)), 3),
            median_MASE=round(float(np.nanmedian(mase)), 3),
            mean_RMSE=round(float(np.nanmean(df[f'{m}_oos_rmse'])), 3),
            PB_pct=pb_all[m],
            mean_bias=round(float(np.nanmean(df[f'{m}_oos_bias'])), 3),
            pct_over=round(float(np.nanmean(df[f'{m}_oos_bias'] > 0) * 100), 1)))
    overall = pd.DataFrame(rows)
    overall.to_csv(fr'{RES}\{ds}_overall.csv', index=False)

    # (b) in-sample vs OOS inversion (classical only; the "dashboard" view)
    pb_in  = pb(df, CLASSICAL, '_insample_mae')
    pb_out = pb(df, CLASSICAL, '_oos_mae')
    mean_in  = {m: round(float(np.nanmean(df[f'{m}_insample_mae'])), 3) for m in CLASSICAL}
    mean_mase= {m: round(float(np.nanmean(df[f'{m}_mase'])), 3) for m in CLASSICAL}
    inv = pd.DataFrame({'method': [LABEL[m] for m in CLASSICAL],
                        'insample_fit_MAE': [mean_in[m] for m in CLASSICAL],
                        'insample_PB_pct': [pb_in[m] for m in CLASSICAL],
                        'oos_mean_MASE':   [mean_mase[m] for m in CLASSICAL],
                        'oos_PB_pct':      [pb_out[m] for m in CLASSICAL]})
    inv.to_csv(fr'{RES}\{ds}_inversion.csv', index=False)
    insample_winner = max(pb_in, key=pb_in.get)
    oos_winner      = min(mean_mase, key=mean_mase.get)

    # (c) by SBC class
    byc = []
    for cl in ['Smooth','Intermittent','Erratic','Lumpy']:
        sub = df[df['class'] == cl]
        if len(sub) == 0: continue
        row = {'class': cl, 'n': len(sub)}
        for m in ALL6:
            row[f'{LABEL[m]}'] = round(float(np.nanmean(sub[f'{m}_mase'])), 3)
        byc.append(row)
    pd.DataFrame(byc).to_csv(fr'{RES}\{ds}_by_class.csv', index=False)
    # PB by class
    byc_pb = []
    for cl in ['Smooth','Intermittent','Erratic','Lumpy']:
        sub = df[df['class'] == cl]
        if len(sub) == 0: continue
        p = pb(sub, ALL6, '_oos_mae'); p = {'class': cl, 'n': len(sub), **{LABEL[m]: p[m] for m in ALL6}}
        byc_pb.append(p)
    pd.DataFrame(byc_pb).to_csv(fr'{RES}\{ds}_by_class_pb.csv', index=False)

    # (d) PB by OOS demand-volume decile
    df['vol_band'] = pd.qcut(df['oos_mean'].rank(method='first'), 10, labels=False)
    band_rows = []
    for b in range(10):
        sub = df[df['vol_band'] == b]
        p = pb(sub, ALL6, '_oos_mae')
        band_rows.append({'decile': b+1, 'mean_oos_demand': round(float(sub['oos_mean'].mean()),3),
                          **{LABEL[m]: p[m] for m in ALL6}})
    pd.DataFrame(band_rows).to_csv(fr'{RES}\{ds}_by_volume.csv', index=False)

    digest[ds] = dict(n_eligible=n,
                      overall=overall.to_dict('records'),
                      insample_winner=LABEL[insample_winner], insample_PB=pb_in,
                      oos_winner=LABEL[oos_winner], oos_mean_MASE=mean_mase,
                      oos_PB_classical=pb_out)
    print(f'\n===== {ds.upper()}  (n eligible={n:,}) =====')
    print(overall.to_string(index=False))
    print(f'  IN-SAMPLE PB: {{{", ".join(f"{LABEL[m]}:{pb_in[m]}" for m in CLASSICAL)}}}  -> winner {LABEL[insample_winner]}')
    print(f'  OOS  PB(cls): {{{", ".join(f"{LABEL[m]}:{pb_out[m]}" for m in CLASSICAL)}}}')
    print(f'  OOS mean MASE winner: {LABEL[oos_winner]}')

with open(fr'{RES}\digest.json', 'w') as f:
    json.dump(digest, f, indent=2)
print('\nSaved all aggregate tables + digest.json')
