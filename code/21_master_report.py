"""
21_master_report.py  -- assemble the FINAL cross-method comparison from every model's
per-series parquet (classical, LightGBM, neural, Chronos, TimesFM). Restricts to the
series scored by ALL available methods (true apples-to-apples) and reports mean/median
MASE overall and by demand regime. Run with the MAIN python (needs pandas/pyarrow).

Outputs: results/master_comparison.json  and  results/master_tables.md
"""
import os, json, numpy as np, pandas as pd

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
DATASETS = ['m5', 'or2']
DSNAME = {'m5': 'M5 (Walmart)', 'or2': 'Online Retail II'}

# (file, [(col_in_file, canonical_method_name)])
SOURCES = [
    ('{ds}_classical.parquet', [('naive_mase', 'Naive'), ('sma_mase', 'SMA'),
                                ('ses_mase', 'SES'), ('croston_mase', 'Croston'),
                                ('sba_mase', 'SBA')]),
    ('{ds}_lgbm.parquet', [('lgbm_mase', 'LightGBM')]),
    ('{ds}_neural.parquet', [('nhits_mase', 'NHITS'), ('deepar_mase', 'DeepAR')]),
    ('{ds}_foundation.parquet', [('chronos_bolt_small_mase', 'Chronos-Bolt-Small (48M)'),
                                 ('chronos_bolt_base_mase', 'Chronos-Bolt-Base (205M)')]),
    ('{ds}_timesfm.parquet', [('timesfm_200m_mase', 'TimesFM-200M')]),
]
ORDER = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'LightGBM', 'NHITS', 'DeepAR',
         'Chronos-Bolt-Small (48M)', 'Chronos-Bolt-Base (205M)', 'TimesFM-200M']
REGIMES = ['Smooth', 'Erratic', 'Intermittent', 'Lumpy']


def assemble(ds):
    base = None
    present = []
    for fpat, cols in SOURCES:
        path = os.path.join(RES, fpat.format(ds=ds))
        if not os.path.exists(path):
            continue
        df = pd.read_parquet(path)
        keep = ['unique_id'] + [c for c, _ in cols if c in df.columns]
        if 'class' in df.columns and (base is None or 'class' not in base.columns):
            keep.append('class')
        sub = df[keep].rename(columns={c: name for c, name in cols if c in df.columns})
        present += [name for c, name in cols if c in df.columns]
        base = sub if base is None else base.merge(sub, on='unique_id', how='inner')
    methods = [m for m in ORDER if m in present]
    base = base.replace([np.inf, -np.inf], np.nan)
    common = base.dropna(subset=methods)
    return common, methods


def main():
    master = {}
    md = ['# Master cross-method comparison (real runs)\n',
          'One-step rolling-origin out-of-sample MASE; identical series across all methods '
          '(scored by every available method). Lower is better; **bold** = best in column.\n']
    for ds in DATASETS:
        try:
            common, methods = assemble(ds)
        except Exception as e:
            md.append(f'\n_{ds}: not available ({e})_\n'); continue
        n = len(common)
        overall = {m: [round(float(common[m].mean()), 3), round(float(common[m].median()), 3)]
                   for m in methods}
        byreg = {}
        for r in REGIMES:
            sub = common[common['class'] == r]
            if len(sub):
                byreg[r] = {'n': int(len(sub)),
                            **{m: round(float(sub[m].mean()), 3) for m in methods}}
        master[ds] = {'n_common': n, 'overall_mean_median': overall, 'by_regime': byreg}

    # overall table
    md.append('\n## Overall: mean (median) MASE\n')
    cols_present = [ds for ds in DATASETS if ds in master]
    md.append('| Method | ' + ' | '.join(f'{DSNAME[ds]} (n={master[ds]["n_common"]})'
                                          for ds in cols_present) + ' |')
    md.append('|' + '---|' * (1 + len(cols_present)))
    # best per dataset (by mean)
    best = {ds: min(master[ds]['overall_mean_median'].items(), key=lambda kv: kv[1][0])[0]
            for ds in cols_present}
    allm = [m for m in ORDER if any(m in master[ds]['overall_mean_median'] for ds in cols_present)]
    for m in allm:
        cells = []
        for ds in cols_present:
            o = master[ds]['overall_mean_median'].get(m)
            if o is None:
                cells.append('—')
            else:
                s = f'{o[0]:.3f} ({o[1]:.3f})'
                cells.append(f'**{s}**' if best[ds] == m else s)
        md.append(f'| {m} | ' + ' | '.join(cells) + ' |')

    # by-regime tables
    for ds in cols_present:
        md.append(f'\n## {DSNAME[ds]}: mean MASE by regime\n')
        regs = [r for r in REGIMES if r in master[ds]['by_regime']]
        md.append('| Method | ' + ' | '.join(f'{r} (n={master[ds]["by_regime"][r]["n"]})'
                                              for r in regs) + ' |')
        md.append('|' + '---|' * (1 + len(regs)))
        for m in allm:
            if not any(m in master[ds]['by_regime'][r] for r in regs):
                continue
            cells = []
            for r in regs:
                v = master[ds]['by_regime'][r].get(m)
                cells.append(f'{v:.3f}' if v is not None else '—')
            md.append(f'| {m} | ' + ' | '.join(cells) + ' |')

    text = '\n'.join(md)
    print(text)
    with open(os.path.join(RES, 'master_comparison.json'), 'w') as f:
        json.dump(master, f, indent=2)
    with open(os.path.join(RES, 'master_tables.md'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    print('\n[written results/master_comparison.json + master_tables.md]')


if __name__ == '__main__':
    main()
