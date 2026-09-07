import os, numpy as np, pandas as pd
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

for ds in ['m5', 'or2']:
    panel = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    spans = np.array([int(np.sum(~np.isnan(Y[i, fa[i]:]))) for i in range(n)])
    # non-zero rate over active span
    nzrate = []
    for i in range(n):
        s = Y[i, fa[i]:]; s = s[~np.isnan(s)]
        nzrate.append((s > 0).mean() if len(s) else np.nan)
    nzrate = np.array(nzrate)
    cls = pd.read_parquet(fr'{DATA}\{ds}_classification.parquet')
    dist = cls['class'].value_counts(normalize=True).mul(100).round(1).to_dict()
    print(f'\n==== {ds.upper()} ====')
    print(f'series n           = {n}')
    print(f'T (weeks in panel) = {T}')
    print(f'active span weeks  : median={np.median(spans):.0f} mean={spans.mean():.1f} '
          f'min={spans.min()} max={spans.max()}')
    print(f'non-zero rate      : median={np.nanmedian(nzrate)*100:.1f}%  mean={np.nanmean(nzrate)*100:.1f}%')
    print(f'mean ADI={cls["ADI"].replace([np.inf],np.nan).mean():.2f}  mean CV2={cls["CV2"].mean():.2f}')
    print(f'regime %           : {dist}')
    print(f'intermittent+lumpy = {dist.get("Intermittent",0)+dist.get("Lumpy",0):.1f}%')
