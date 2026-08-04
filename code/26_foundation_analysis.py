"""
26_foundation_analysis.py -- bring the zero-shot foundation models into the main
comparison, and test the data-sufficiency hypothesis directly.

The paper argues that machine-learning forecasters fail on the sparse tail because
each series carries too little history to learn from. That explanation makes a
prediction: a model pretrained on a large external corpus, applied zero-shot with no
per-series fitting at all, should not suffer the same limitation. Chronos-Bolt and
TimesFM are exactly that, so running them on the same series under the same protocol
turns the explanation into something falsifiable.

Reads the existing *_foundation.parquet and *_timesfm.parquet runs, merges them with
the classical, gradient-boosted and neural results on the common subset, and writes
results/{ds}_foundation_table.csv plus results/foundation_summary.json.
"""
import os, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')

CLASSICAL = [('naive_mase', 'Naive'), ('sma_mase', 'SMA'), ('ses_mase', 'SES'),
             ('croston_mase', 'Croston'), ('sba_mase', 'SBA')]
TRAINED = [('lgbm_mase', 'LightGBM'), ('nhits_mase', 'NHITS'), ('deepar_mase', 'DeepAR')]
ZEROSHOT = [('chronos_bolt_small_mase', 'Chronos-Bolt-Small'),
            ('chronos_bolt_base_mase', 'Chronos-Bolt-Base'),
            ('timesfm_200m_mase', 'TimesFM-200M')]
CLASSES = ['Smooth', 'Erratic', 'Intermittent', 'Lumpy']
SPARSE = ['Intermittent', 'Lumpy']

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

summary = {}
for ds in ('m5', 'or2'):
    df = load(ds)
    present = [(c, n) for c, n in CLASSICAL + TRAINED + ZEROSHOT if c in df.columns]
    # common subset: eligible, and scored by every method present
    elig = np.isfinite(df['scale']) & (df['scale'] > 0) & (df['train_nnz'] >= 2)
    for c, _ in present:
        elig &= np.isfinite(df[c])
    d = df[elig]
    print(f'\n[{ds}] common subset n={len(d):,}  methods={len(present)}')

    rows = []
    for c, name in present:
        tier = ('classical' if (c, name) in CLASSICAL
                else 'trained' if (c, name) in TRAINED else 'zero-shot')
        r = {'method': name, 'tier': tier, 'overall': round(float(d[c].mean()), 3)}
        for cl in CLASSES:
            sub = d[d['class'] == cl]
            r[cl] = round(float(sub[c].mean()), 3) if len(sub) else np.nan
        rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, f'{ds}_foundation_table.csv'), index=False)
    print(t.to_string(index=False))

    # ---- the actual test -------------------------------------------------
    # On the sparse classes, does the best zero-shot model beat the best trained
    # model? If per-series data volume were the binding constraint, it should.
    out = {'n': int(len(d)), 'class_n': {cl: int((d['class'] == cl).sum()) for cl in CLASSES}}
    for cl in CLASSES:
        sub = d[d['class'] == cl]
        if not len(sub):
            continue
        best = {}
        for tier, group in (('classical', CLASSICAL), ('trained', TRAINED), ('zero-shot', ZEROSHOT)):
            cand = [(float(sub[c].mean()), n) for c, n in group if c in d.columns]
            if cand:
                v, n = min(cand)
                best[tier] = {'method': n, 'mase': round(v, 3)}
        if 'trained' in best and 'zero-shot' in best:
            best['zeroshot_beats_trained'] = bool(best['zero-shot']['mase'] < best['trained']['mase'])
            best['gap'] = round(best['zero-shot']['mase'] - best['trained']['mase'], 3)
        out[cl] = best
    summary[ds] = out

    print(f'\n  data-sufficiency test on the sparse classes ({", ".join(SPARSE)}):')
    for cl in SPARSE:
        b = out.get(cl, {})
        if 'zeroshot_beats_trained' in b:
            verdict = 'YES' if b['zeroshot_beats_trained'] else 'NO'
            print(f"    {cl:<13} best zero-shot {b['zero-shot']['method']} {b['zero-shot']['mase']:.3f}"
                  f"  vs best trained {b['trained']['method']} {b['trained']['mase']:.3f}"
                  f"   beats trained: {verdict} (gap {b['gap']:+.3f})")

with open(os.path.join(RES, 'foundation_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print('\nsaved results/foundation_summary.json and the two *_foundation_table.csv')
