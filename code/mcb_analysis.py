"""
mcb_analysis.py -- Multiple-Comparisons-with-the-Best (MCB) / Nemenyi analysis in the
M-competition style (Koning, Franses, Hibon & Stekler, 2005 IJF): methods are ranked per
series by out-of-sample MASE; mean ranks are compared against a critical distance at the
5% level. Two scopes:
  (a) the six core methods on the full eligible set (Table 3 scope)  -> Table 7
  (b) all eight methods (incl. NHITS/DeepAR) on the neural-eligible subset (Table 6 scope)
      -> fig7_mcb.png
Outputs: results/mcb.json, results/figures/fig7_mcb.png
"""
import os, re, json
import numpy as np, pandas as pd
import matplotlib as mpl; mpl.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results'); FIG = os.path.join(RES, 'figures')

# studentized-range upper-5% quantiles, df = infinity (standard tables)
Q05 = {2: 2.772, 3: 3.314, 4: 3.633, 5: 3.858, 6: 4.030, 7: 4.170, 8: 4.286,
       9: 4.387, 10: 4.474, 11: 4.552, 12: 4.622, 13: 4.685, 14: 4.743}

CORE = [('naive_mase', 'Naive'), ('sma_mase', 'SMA'), ('ses_mase', 'SES'),
        ('croston_mase', 'Croston'), ('sba_mase', 'SBA'), ('tsb_mase', 'TSB'),
        ('adida_mase', 'ADIDA'), ('mapa_mase', 'MAPA'),
        ('lgbm_mase', 'LightGBM (global)')]
NEUR = [('nhits_mase', 'NHITS'), ('deepar_mase', 'DeepAR')]

def load(ds, subset):
    c = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))
    l = pd.read_parquet(os.path.join(RES, f'{ds}_lgbm.parquet'))
    df = c.merge(l, on='unique_id', how='left')
    df = df[np.isfinite(df['scale']) & (df['scale'] > 0) & (df['train_nnz'] >= 2)]
    cols = list(CORE)
    if subset:
        n = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))[['unique_id', 'nhits_mase', 'deepar_mase']]
        df = df.merge(n, on='unique_id', how='inner')
        df = df[df['nhits_mase'].notna()]
        cols = list(CORE) + list(NEUR)
    M = df[[c0 for c0, _ in cols]].astype(float)
    M = M.replace([np.inf, -np.inf], np.nan)
    keep = M.notna().all(axis=1)
    ids = df.loc[keep, 'unique_id'].astype(str).values
    return M[keep], [lab for _, lab in cols], ids


def product_key(ds, ids):
    """Collapse an M5 store-SKU id to its product. 'FOODS_1_001_CA_1' -> 'FOODS_1_001'.
    Online Retail II has a single seller and no store dimension, so its ids are already
    products and clustering is a no-op there."""
    if ds != 'm5':
        return ids
    return np.array([re.sub(r'_(CA|TX|WI)_\d+$', '', u) for u in ids])


def mcb_clustered(M, labels, ids, ds):
    """Nemenyi treats the N series as independent blocks. On M5 they are not: the panel is
    3,049 products observed in 10 stores each, and the same product in ten stores is closer to
    one observation than to ten. We average each method's per-series rank within a product and
    run the test on the product means, so N is the number of independent products. This can
    only widen the critical distance; it is reported as a robustness check on Section 5.10
    rather than as the headline, because the store-level series are genuinely distinct
    forecasting problems even when their demand is correlated."""
    ranks = M.rank(axis=1, method='average')
    ranks = ranks.assign(_p=product_key(ds, ids))
    rp = ranks.groupby('_p').mean()
    rbar = rp.mean(axis=0).values
    N, K = rp.shape
    cd = Q05[K] / np.sqrt(2) * np.sqrt(K * (K + 1) / (6.0 * N))
    best = float(rbar.min())
    return {'N_clusters': int(N), 'K': K, 'critical_distance': round(float(cd), 3),
            'mean_ranks': {lab: round(float(r), 3) for lab, r in zip(labels, rbar)},
            'sig_worse_than_best': {lab: bool(r - best > cd) for lab, r in zip(labels, rbar)}}

def mcb(M, labels):
    ranks = M.rank(axis=1, method='average')
    rbar = ranks.mean(axis=0).values
    N, K = M.shape
    cd = Q05[K] / np.sqrt(2) * np.sqrt(K * (K + 1) / (6.0 * N))   # Nemenyi critical distance
    best = float(rbar.min())
    out = {'N': int(N), 'K': K, 'critical_distance': round(float(cd), 3),
           'mean_ranks': {lab: round(float(r), 3) for lab, r in zip(labels, rbar)},
           'sig_worse_than_best': {lab: bool(r - best > cd) for lab, r in zip(labels, rbar)}}
    return out

res = {}
for ds in ['m5', 'or2']:
    M6, lab6, id6 = load(ds, subset=False)
    M8, lab8, id8 = load(ds, subset=True)
    res[ds] = {'core6_fullset': mcb(M6, lab6), 'all8_subset': mcb(M8, lab8),
               'core6_product_clustered': mcb_clustered(M6, lab6, id6, ds),
               'all8_product_clustered': mcb_clustered(M8, lab8, id8, ds)}
    a = res[ds]['core6_fullset']
    print(f"[{ds}] core6 N={a['N']} CD={a['critical_distance']}  ranks="
          + ' '.join(f"{k}:{v}" for k, v in sorted(a['mean_ranks'].items(), key=lambda x: x[1])))
    b = res[ds]['all8_subset']
    print(f"[{ds}] all8  N={b['N']} CD={b['critical_distance']}  ranks="
          + ' '.join(f"{k}:{v}" for k, v in sorted(b['mean_ranks'].items(), key=lambda x: x[1])))
    for tag in ('core6_product_clustered', 'all8_product_clustered'):
        c = res[ds][tag]
        print(f"[{ds}] {tag:26s} N_clusters={c['N_clusters']:>6,} CD={c['critical_distance']}"
              + ("  (no store dimension; identical to unclustered)" if ds != 'm5' else ""))

with open(os.path.join(RES, 'mcb.json'), 'w') as f:
    json.dump(res, f, indent=2)

# ---------------- figure: MCB plots, 8 methods on the neural-eligible subset ----------------
mpl.rcParams.update({'font.family': 'serif', 'font.size': 10, 'savefig.dpi': 300, 'savefig.bbox': 'tight'})
DSNAME = {'m5': 'M5 (Walmart, weekly)', 'or2': 'Online Retail II (weekly)'}
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for j, ds in enumerate(['m5', 'or2']):
    d = res[ds]['all8_subset']
    items = sorted(d['mean_ranks'].items(), key=lambda x: x[1])
    labs = [k for k, _ in items]; vals = np.array([v for _, v in items])
    cd = d['critical_distance']; best = vals.min()
    ax = axes[j]
    y = np.arange(len(labs))[::-1]
    for yi, v, lab in zip(y, vals, labs):
        sig = v - best > cd
        col = '#1E2761' if not sig else '#9AA0A6'
        ax.errorbar(v, yi, xerr=cd / 2, fmt='o', color=col, ecolor=col, capsize=3, ms=5, lw=1.6)
    ax.axvline(best + cd / 2 + 0, color='#C0392B', ls='--', lw=1)
    # Anchor at the bottom of the axes. Placed near the top it runs past the axes
    # edge and collides with the panel title.
    ax.text(best + cd / 2, -0.35, ' best + CD/2', color='#C0392B', fontsize=7.5,
            va='bottom', ha='left')
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=9)
    ax.set_xlabel('mean MASE rank (lower = better)  ±CD/2')
    ax.set_title(f"{DSNAME[ds]}: n={d['N']:,}, CD={cd:.3f}", fontsize=10)
# the method count is read from the data: the 'all8' key is a legacy name and the subset has
# carried eleven methods since the pretrained models were added, so a hard-coded 8 in the
# figure title contradicted the caption in the manuscript
_k = res['m5']['all8_subset']['K']
fig.suptitle(f'Figure 7.  MCB/Nemenyi analysis on the neural-eligible subset ({_k} methods). Navy intervals are '
             'statistically indistinguishable from the best method at the 5% level; grey are significantly worse.',
             fontsize=9.5, y=1.03)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'fig7_mcb.png')); plt.close(fig)
print('saved results/mcb.json + figures/fig7_mcb.png')
