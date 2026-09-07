"""
04_lgbm_global.py -- a single GLOBAL gradient-boosted model (LightGBM, the method
class that won the M5 competition) trained across all series, as the modern "AI"
forecaster. One-step-ahead evaluation: every lag/rolling feature at test week t uses
only actual demand through t-1, so the comparison with the classical rolling-origin
forecasts is apples-to-apples. Tweedie objective handles the zero-inflated counts.

Output: results/<ds>_lgbm.parquet  (per-series OOS MAE/RMSE/bias/MASE for LightGBM)
        results/<ds>_lgbm_importance.csv
"""
import os, sys, numpy as np, pandas as pd, lightgbm as lgb
import lib

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
SPLIT = {'m5': 26, 'or2': 14}
VAL   = {'m5': 8, 'or2': 6}

# features come from lib.add_ml_features -- the single, leakage-audited source
# (same-week posted price for M5; strictly lagged transacted price for OR2).
DATASETS = [d for d in sys.argv[1:] if d in ('m5', 'or2')] or ['m5', 'or2']
# --leaked regenerates the DISCARDED OR2 specification (same-week transacted price and a
# test-inclusive normaliser) so the counterfactual quoted in Section 5.7 is reproducible.
# It writes to *_leaked artefacts and never overwrites a headline result.
LEAKED = '--leaked' in sys.argv
SUF = '_leaked' if LEAKED else ''
if LEAKED:
    print('*** LEAKED SPECIFICATION -- counterfactual only, not a headline result ***')

for ds in DATASETS:
    panel  = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')
    static = pd.read_parquet(fr'{DATA}\{ds}_static.parquet')
    T = int(panel['week_idx'].max()) + 1
    split = T - SPLIT[ds]; val0 = split - VAL[ds]
    print(f'\n[{ds}] building features... T={T} split={split} val_start={val0}')
    df, feats, cats = lib.add_ml_features(panel, static, ds, leaked=LEAKED)

    tr = df[df['week_idx'] <  val0]
    va = df[(df['week_idx'] >= val0) & (df['week_idx'] < split)]
    te = df[df['week_idx'] >= split].copy()
    print(f'  train rows={len(tr):,} val rows={len(va):,} test rows={len(te):,} feats={len(feats)}')

    dtr = lgb.Dataset(tr[feats], tr['y'], categorical_feature=cats, free_raw_data=False)
    dva = lgb.Dataset(va[feats], va['y'], categorical_feature=cats, reference=dtr, free_raw_data=False)
    params = dict(objective='tweedie', tweedie_variance_power=1.1, metric='mae',
                  learning_rate=0.05, num_leaves=127, min_data_in_leaf=100,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                  max_depth=-1, verbosity=-1, n_jobs=-1)
    model = lgb.train(params, dtr, num_boost_round=2000, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(80), lgb.log_evaluation(0)])
    print(f'  best_iteration={model.best_iteration}')
    te['pred'] = np.clip(model.predict(te[feats], num_iteration=model.best_iteration), 0, None)

    # per-series OOS metrics
    grp = te.groupby('unique_id', observed=True)
    out = pd.DataFrame({'unique_id': list(grp.groups.keys())})
    err  = (te['pred'] - te['y'])
    te['ae'] = err.abs(); te['se'] = err**2; te['e'] = err
    agg = te.groupby('unique_id', observed=True).agg(lgbm_oos_mae=('ae','mean'),
            lgbm_oos_rmse=('se', lambda x: np.sqrt(x.mean())), lgbm_oos_bias=('e','mean'))
    cls = pd.read_parquet(fr'{RES}\{ds}_classical.parquet')[['unique_id','scale']]
    agg = agg.merge(cls, on='unique_id', how='left')
    agg['lgbm_mase'] = agg['lgbm_oos_mae'] / agg['scale']
    agg.drop(columns=['scale']).to_parquet(fr'{RES}\{ds}_lgbm{SUF}.parquet', index=False)
    imp = pd.DataFrame({'feature': feats, 'gain': model.feature_importance('gain')}
                       ).sort_values('gain', ascending=False)
    imp.to_csv(fr'{RES}\{ds}_lgbm_importance{SUF}.csv', index=False)
    print(f'  LightGBM mean MASE={np.nanmean(agg["lgbm_mase"]):.3f} '
          f'median MASE={np.nanmedian(agg["lgbm_mase"]):.3f}')
    print('  top features:', imp.head(6)['feature'].tolist())
