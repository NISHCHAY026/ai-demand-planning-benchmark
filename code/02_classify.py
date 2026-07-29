"""
02_classify.py -- SBC demand classification + demand fingerprint for both panels.
Outputs per-dataset:  <ds>_classification.parquet  and prints a fingerprint summary
that is also written to results/<ds>_fingerprint.json
"""
import os, json, numpy as np, pandas as pd
import lib

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results'); os.makedirs(RES, exist_ok=True)

for ds in ['m5', 'or2']:
    panel = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    cls = lib.classify(Y, fa)
    cls.insert(0, 'unique_id', uids)
    cls.to_parquet(fr'{DATA}\{ds}_classification.parquet', index=False)

    # fingerprint
    total_cells = (~np.isnan(Y)).sum()
    zero_cells  = ((Y == 0)).sum()
    classifiable = cls['n_nonzero'] >= 2
    dist = cls.loc[classifiable, 'class'].value_counts(normalize=True).mul(100).round(1).to_dict()
    fp = {
        'dataset': ds,
        'n_series': int(n),
        'n_weeks': int(T),
        'panel_cells': int(total_cells),
        'pct_zero_weeks': round(100 * zero_cells / total_cells, 1),
        'median_active_weeks': float(np.median(cls['n_nonzero'])),
        'median_ADI': round(float(cls.loc[np.isfinite(cls['ADI']), 'ADI'].median()), 2),
        'median_CV2': round(float(cls['CV2'].median()), 2),
        'n_classifiable': int(classifiable.sum()),
        'class_dist_pct': dist,
        'pct_intermittent_or_lumpy': round(dist.get('Intermittent', 0) + dist.get('Lumpy', 0), 1),
        'pct_smooth': dist.get('Smooth', 0),
    }
    with open(fr'{RES}\{ds}_fingerprint.json', 'w') as f:
        json.dump(fp, f, indent=2)
    print(f'\n===== {ds.upper()} demand fingerprint =====')
    for k, v in fp.items():
        print(f'  {k}: {v}')
