"""
27_managerial_table.py -- build the method-selection guidance table from the results,
not from intuition.

For every panel and demand class it reports the best method under mean MASE and the
best under Percentage-Best, because on this data those two disagree and the
disagreement is the point. Mean MASE rewards estimating the demand rate;
Percentage-Best counts how often a method wins outright, which on sparse series
favours anything that forecasts zero. A practitioner picking a method needs to know
which of those matches the decision they are making.

Writes results/{ds}_managerial.csv and results/managerial_summary.json
"""
import os, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')
CLASSES = ['Smooth', 'Erratic', 'Intermittent', 'Lumpy']

TIER = {'Naive': 'simple', 'SMA': 'simple', 'SES': 'simple',
        'Croston': 'intermittent-specialist', 'SBA': 'intermittent-specialist',
        'LightGBM': 'trained ML', 'LightGBM (AI)': 'trained ML',
        'NHITS': 'trained deep', 'DeepAR': 'trained deep',
        'Chronos-Bolt-Small': 'zero-shot', 'Chronos-Bolt-Base': 'zero-shot',
        'TimesFM-200M': 'zero-shot'}

out = {}
for ds, label in (('m5', 'M5 (dense)'), ('or2', 'Online Retail II (sparse)')):
    acc = pd.read_csv(os.path.join(RES, f'{ds}_foundation_table.csv'))
    pb = pd.read_csv(os.path.join(RES, f'{ds}_by_class_pb.csv')).set_index('class')
    pbcols = [c for c in pb.columns if c != 'n']

    rows = []
    for cl in CLASSES:
        if cl not in acc.columns or cl not in pb.index:
            continue
        col = acc[['method', 'tier', cl]].dropna().sort_values(cl)
        best_acc, best_acc_v = col.iloc[0]['method'], float(col.iloc[0][cl])
        runner, runner_v = col.iloc[1]['method'], float(col.iloc[1][cl])
        # best simple method, for the "is the complexity worth it" margin
        simple = col[col['method'].isin(['Naive', 'SMA', 'SES'])]
        best_simple, best_simple_v = simple.iloc[0]['method'], float(simple.iloc[0][cl])
        pbrow = pb.loc[cl, pbcols].astype(float)
        best_pb, best_pb_v = pbrow.idxmax(), float(pbrow.max())
        rows.append({
            'class': cl,
            'n': int(pb.loc[cl, 'n']),
            'best_by_mean_MASE': best_acc,
            'mean_MASE': round(best_acc_v, 3),
            'runner_up': runner,
            'runner_up_MASE': round(runner_v, 3),
            'best_simple': best_simple,
            'best_simple_MASE': round(best_simple_v, 3),
            'gain_over_simple_pct': round((best_simple_v - best_acc_v) / best_simple_v * 100, 1),
            'best_by_PercentageBest': best_pb,
            'PB_pct': round(best_pb_v, 1),
            'metrics_agree': TIER.get(best_acc, '?') == TIER.get(best_pb, '?'),
            'beats_naive_on_MASE': bool(best_acc_v < float(col[col['method'] == 'Naive'][cl].iloc[0])),
        })
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(RES, f'{ds}_managerial.csv'), index=False)
    out[ds] = {'label': label, 'rows': rows}
    print(f'\n=== {label} ===')
    print(t.to_string(index=False))

with open(os.path.join(RES, 'managerial_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)

print('\n=== where the two metrics disagree ===')
for ds in out:
    for r in out[ds]['rows']:
        if not r['metrics_agree']:
            print(f"  {out[ds]['label']:<26} {r['class']:<13} "
                  f"mean MASE favours {r['best_by_mean_MASE']}, "
                  f"Percentage-Best favours {r['best_by_PercentageBest']} ({r['PB_pct']}%)")
print('\nsaved results/*_managerial.csv and results/managerial_summary.json')
