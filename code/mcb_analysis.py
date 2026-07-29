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
import os, json
import numpy as np, pandas as pd
import matplotlib as mpl; mpl.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results'); FIG = os.path.join(RES, 'figures')

# studentized-range upper-5% quantiles, df = infinity (standard tables)
Q05 = {6: 4.030, 8: 4.286}

CORE = [('naive_mase', 'Naive'), ('sma_mase', 'SMA'), ('ses_mase', 'SES'),
        ('croston_mase', 'Croston'), ('sba_mase', 'SBA'), ('lgbm_mase', 'LightGBM (AI)')]
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
    M = M.replace([np.inf, -np.inf], np.nan).dropna()
    return M, [lab for _, lab in cols]

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
    M6, lab6 = load(ds, subset=False)
    M8, lab8 = load(ds, subset=True)
    res[ds] = {'core6_fullset': mcb(M6, lab6), 'all8_subset': mcb(M8, lab8)}
    a = res[ds]['core6_fullset']
    print(f"[{ds}] core6 N={a['N']} CD={a['critical_distance']}  ranks="
          + ' '.join(f"{k}:{v}" for k, v in sorted(a['mean_ranks'].items(), key=lambda x: x[1])))
    b = res[ds]['all8_subset']
    print(f"[{ds}] all8  N={b['N']} CD={b['critical_distance']}  ranks="
          + ' '.join(f"{k}:{v}" for k, v in sorted(b['mean_ranks'].items(), key=lambda x: x[1])))

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
    ax.text(best + cd / 2, len(labs) - 0.4, ' best + CD/2', color='#C0392B', fontsize=7.5, va='bottom')
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=9)
    ax.set_xlabel('mean MASE rank (lower = better)  ±CD/2')
    ax.set_title(f"{DSNAME[ds]} — n={d['N']:,}, CD={cd:.3f}", fontsize=10)
fig.suptitle('Figure 7.  MCB/Nemenyi analysis on the neural-eligible subset (8 methods). Navy intervals are '
             'statistically indistinguishable from the best method at the 5% level; grey are significantly worse.',
             fontsize=9.5, y=1.03)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 'fig7_mcb.png')); plt.close(fig)
print('saved results/mcb.json + figures/fig7_mcb.png')
