"""
29_gap_ci.py -- uncertainty for the zero-shot minus trained gaps of Section 5.9.

Referee point this answers: the data-sufficiency test in Table 10 was reported as four
point estimates with no interval, which is not enough to support a falsification. This
script attaches a paired 95% interval to each gap and records whether it excludes zero.

The gap in each demand class is a PAIRED per-series difference between the best trained
method and the best zero-shot method, where "best" is the tier minimum of mean MASE on
the same series. That selection is itself post hoc, so the script also reports a
pre-registered alternative in which the tier representative is fixed in advance (NHITS
for trained, Chronos-Bolt-Small for zero-shot) and no minimum is taken.

Output: results/gap_ci.json
"""
import os, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')

CLASSICAL = [('naive_mase', 'Naive'), ('sma_mase', 'SMA'), ('ses_mase', 'SES'),
             ('croston_mase', 'Croston'), ('sba_mase', 'SBA'), ('tsb_mase', 'TSB'),
             ('adida_mase', 'ADIDA'), ('mapa_mase', 'MAPA')]
TRAINED = [('lgbm_mase', 'LightGBM'), ('nhits_mase', 'NHITS'), ('deepar_mase', 'DeepAR')]
ZEROSHOT = [('chronos_bolt_small_mase', 'Chronos-Bolt-Small'),
            ('chronos_bolt_base_mase', 'Chronos-Bolt-Base'),
            ('timesfm_200m_mase', 'TimesFM-200M')]
SIMPLE = [('naive_mase', 'Naive'), ('sma_mase', 'SMA'), ('ses_mase', 'SES')]
SPARSE = ['Intermittent', 'Lumpy']
FIXED_TRAINED, FIXED_ZERO = 'nhits_mase', 'chronos_bolt_small_mase'


def load(ds):
    df = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))
    for extra in (f'{ds}_lgbm.parquet', f'{ds}_neural.parquet',
                  f'{ds}_foundation.parquet', f'{ds}_timesfm.parquet'):
        p = os.path.join(RES, extra)
        if not os.path.exists(p):
            continue
        e = pd.read_parquet(p)
        cols = ['unique_id'] + [c for c in e.columns
                                if c not in df.columns and c not in ('scale', 'class')]
        df = df.merge(e[cols], on='unique_id', how='left')
    return df


def paired(a, b, B=4000, seed=7):
    """Paired difference a - b with a normal and a bootstrap 95% interval."""
    d = (a - b).astype(float)
    n = len(d)
    m = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(n))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    boot = d.values[idx].mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {'n': int(n), 'gap': round(m, 4), 'se': round(se, 4),
            't': round(m / se, 2) if se > 0 else None,
            'ci_normal': [round(m - 1.96 * se, 4), round(m + 1.96 * se, 4)],
            'ci_bootstrap': [round(float(lo), 4), round(float(hi), 4)],
            'excludes_zero': bool(lo > 0 or hi < 0)}


out = {}
for ds in ('m5', 'or2'):
    df = load(ds)
    present = [(c, n) for c, n in CLASSICAL + TRAINED + ZEROSHOT if c in df.columns]
    elig = np.isfinite(df['scale']) & (df['scale'] > 0) & (df['train_nnz'] >= 2)
    for c, _ in present:
        elig &= np.isfinite(df[c])
    d = df[elig]
    out[ds] = {'n_common': int(len(d))}
    for cl in SPARSE:
        sub = d[d['class'] == cl]
        if not len(sub):
            continue
        bt = min((float(sub[c].mean()), n, c) for c, n in TRAINED if c in d.columns)
        bz = min((float(sub[c].mean()), n, c) for c, n in ZEROSHOT if c in d.columns)
        bs = min((float(sub[c].mean()), n, c) for c, n in SIMPLE if c in d.columns)
        rec = {'class_n': int(len(sub)),
               'best_simple': {'method': bs[1], 'mase': round(bs[0], 3)},
               'best_trained': {'method': bt[1], 'mase': round(bt[0], 3)},
               'best_zeroshot': {'method': bz[1], 'mase': round(bz[0], 3)},
               'selected_min': paired(sub[bz[2]], sub[bt[2]])}
        if FIXED_TRAINED in sub.columns and FIXED_ZERO in sub.columns:
            rec['prereg_fixed'] = dict(
                paired(sub[FIXED_ZERO], sub[FIXED_TRAINED]),
                trained='NHITS', zeroshot='Chronos-Bolt-Small')
        out[ds][cl] = rec
        s = rec['selected_min']
        print(f"[{ds}] {cl:<13} n={s['n']:>5}  {bz[1]} minus {bt[1]}  "
              f"gap={s['gap']:+.4f}  95% CI [{s['ci_bootstrap'][0]:+.4f}, "
              f"{s['ci_bootstrap'][1]:+.4f}]  "
              f"{'excludes 0' if s['excludes_zero'] else 'INCLUDES 0'}")

with open(os.path.join(RES, 'gap_ci.json'), 'w') as f:
    json.dump(out, f, indent=2)
print('\nsaved results/gap_ci.json')
