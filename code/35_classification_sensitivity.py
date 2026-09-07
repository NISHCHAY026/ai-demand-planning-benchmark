"""
35_classification_sensitivity.py -- what the full-span SBC convention does to the by-class
results, recorded as an artefact so the comparison in Section 5.4 can be regenerated.

02_classify.py classifies on the training window so that class membership cannot depend on
the hold-out. The paper reports what the usual full-span convention would have produced
instead. That counterfactual is not a by-product of any other script, so without this it
would be a set of numbers a reader has to take on trust.

For each panel it recomputes both labellings, reports how many series move, the by-class
mean MASE of tuned exponential smoothing under each, and for the classes the paper singles
out, the profile of the series that move in or out.

Output: results/classification_sensitivity.json
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA, RES = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'results')
sys.path.insert(0, HERE)
import lib

SPLIT = {'m5': 26, 'or2': 14}
CLASSES = ['Smooth', 'Intermittent', 'Erratic', 'Lumpy']
HIGHLIGHT = {'or2': 'Intermittent', 'm5': 'Lumpy'}      # the two cells Section 5.4 quotes


def profile(g):
    return {'n': int(len(g)),
            'mean_SES_MASE': round(float(g['ses_mase'].mean()), 3),
            'mean_train_active_weeks': round(float(g['train_nnz'].mean()), 1),
            'mean_oos_weekly_demand': round(float(g['oos_mean'].mean()), 3)}


def main():
    out = {}
    for ds in ('m5', 'or2'):
        panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
        Y, uids, fa = lib.build_matrix(panel)
        split = Y.shape[1] - SPLIT[ds]
        train = lib.classify(Y[:, :split].copy(), fa)['class'].values
        full = lib.classify(Y, fa)['class'].values

        d = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))
        lab = pd.DataFrame({'unique_id': uids, 'cls_train': train, 'cls_full': full})
        d = d.merge(lab, on='unique_id')
        d = d[np.isfinite(d['scale']) & (d['scale'] > 0) & (d['train_nnz'] >= 2)]

        rec = {'n_eligible': int(len(d)),
               'pct_series_changing_class': round(100 * float((d.cls_train != d.cls_full).mean()), 2),
               'by_class_SES_mean_MASE': {}}
        for cl in CLASSES:
            a, b = d[d.cls_train == cl], d[d.cls_full == cl]
            rec['by_class_SES_mean_MASE'][cl] = {
                'training_window': {'n': int(len(a)),
                                    'SES': round(float(a.ses_mase.mean()), 3) if len(a) else None},
                'full_span': {'n': int(len(b)),
                              'SES': round(float(b.ses_mase.mean()), 3) if len(b) else None}}
        cl = HIGHLIGHT[ds]
        rec['movers'] = {
            'class': cl,
            'stayed': profile(d[(d.cls_train == cl) & (d.cls_full == cl)]),
            'moved_in_under_training_window': profile(d[(d.cls_train == cl) & (d.cls_full != cl)]),
            'moved_out': profile(d[(d.cls_train != cl) & (d.cls_full == cl)])}
        out[ds] = rec
        print(f'[{ds}] {rec["pct_series_changing_class"]}% of {rec["n_eligible"]:,} eligible series '
              f'change class under the full-span convention')
        for c in CLASSES:
            v = rec['by_class_SES_mean_MASE'][c]
            print(f'    {c:13s} SES  training-window {v["training_window"]["SES"]}'
                  f' (n={v["training_window"]["n"]:,})   full-span {v["full_span"]["SES"]}'
                  f' (n={v["full_span"]["n"]:,})')
        m = rec['movers']
        print(f'    movers into {cl}: n={m["moved_in_under_training_window"]["n"]}, '
              f'SES MASE {m["moved_in_under_training_window"]["mean_SES_MASE"]} vs '
              f'{m["stayed"]["mean_SES_MASE"]} for those already there')

    with open(os.path.join(RES, 'classification_sensitivity.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print('\nsaved results/classification_sensitivity.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
