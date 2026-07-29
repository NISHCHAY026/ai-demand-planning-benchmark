"""
10_neural_baselines.py <m5|or2>  -- deep-learning forecasters (NHITS, an efficient
N-BEATS-family model, and DeepAR) trained as GLOBAL models with neuralforecast, under
the *same* one-step rolling-origin protocol as the classical/LightGBM benchmark
(cross_validation: h=1, step_size=1, refit=False -> train once, forecast each test
week from actual history up to that origin). CPU-only friendly. Models are fit
sequentially to keep peak memory low.

Output: results/<ds>_neural.parquet (per-series MASE for NHITS & DeepAR)
        results/<ds>_neural_summary.json
"""
import os, sys, json, warnings, traceback
# pin BLAS/torch threads BEFORE importing numpy/torch -- avoids a CPU-dataloader segfault on Windows
for _v in ['OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENBLAS_NUM_THREADS']:
    os.environ[_v] = '1'
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
os.environ['NIXTLA_ID_AS_COL'] = '1'
try: sys.stdout.reconfigure(line_buffering=True)
except Exception: pass
import logging
for nm in ['lightning.pytorch','pytorch_lightning','lightning']:
    logging.getLogger(nm).setLevel(logging.ERROR)

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
SPLIT = {'m5': 26, 'or2': 14}
INPUT = {'m5': 52, 'or2': 26}
STEPS = int(os.environ.get('STEPS', '500'))
BASE = pd.Timestamp('2010-01-03')                # weekly anchor (Sunday)

def run_model(make_model, name, nf_df, n_windows, freq):
    from neuralforecast import NeuralForecast
    nf = NeuralForecast(models=[make_model()], freq=freq)
    cv = nf.cross_validation(df=nf_df, n_windows=n_windows, step_size=1, refit=False)
    if 'unique_id' not in cv.columns:
        cv = cv.reset_index()
    pcol = name if name in cv.columns else (f'{name}-median' if f'{name}-median' in cv.columns else None)
    cv[pcol] = cv[pcol].clip(lower=0)
    g = cv.assign(ae=(cv[pcol] - cv['y']).abs(), se=(cv[pcol] - cv['y']) ** 2).groupby('unique_id')
    out = pd.DataFrame({f'{name.lower()}_oos_mae': g['ae'].mean(),
                        f'{name.lower()}_oos_rmse': g['se'].mean().pow(0.5)}).reset_index()
    del nf, cv
    return out

def main(ds):
    import torch; torch.set_num_threads(1)
    from neuralforecast.models import NHITS, DeepAR
    H, IN = SPLIT[ds], INPUT[ds]
    panel = pd.read_parquet(fr'{DATA}\{ds}_weekly.parquet')[['unique_id','week_idx','y']].copy()
    panel['ds'] = BASE + pd.to_timedelta(panel['week_idx'].astype(int) * 7, unit='D')
    panel['y'] = panel['y'].astype('float32')
    panel = panel.sort_values(['unique_id','ds']).reset_index(drop=True)
    # neural-eligible subset: enough history for input window + all H one-step origins
    lens = panel.groupby('unique_id').size()
    keep = lens[lens >= IN + H].index
    nf_df = panel[panel['unique_id'].isin(keep)][['unique_id','ds','y']].reset_index(drop=True)
    print(f'[{ds}] total series={panel.unique_id.nunique()} | neural-eligible (len>={IN+H})='
          f'{nf_df.unique_id.nunique()} rows={len(nf_df)} steps={STEPS} test_weeks={H}', flush=True)

    common = dict(h=1, input_size=IN, scaler_type='standard', max_steps=STEPS,
                  val_check_steps=STEPS, enable_progress_bar=False, logger=False,
                  accelerator='cpu', start_padding_enabled=False, batch_size=256)
    print(f'[{ds}] fitting NHITS...', flush=True)
    nhits = run_model(lambda: NHITS(**common), 'NHITS', nf_df, H, 'W-SUN')
    print(f'[{ds}] NHITS done. fitting DeepAR...', flush=True)
    deepar = run_model(lambda: DeepAR(**common), 'DeepAR', nf_df, H, 'W-SUN')
    print(f'[{ds}] DeepAR done.', flush=True)

    scale = pd.read_parquet(fr'{RES}\{ds}_classical.parquet')[['unique_id','scale','class']]
    per = scale.merge(nhits, on='unique_id', how='left').merge(deepar, on='unique_id', how='left')
    per['nhits_mase']  = per['nhits_oos_mae']  / per['scale']
    per['deepar_mase'] = per['deepar_oos_mae'] / per['scale']
    for c in ['nhits_mase','deepar_mase']:
        per.loc[~np.isfinite(per[c]), c] = np.nan
    per.to_parquet(fr'{RES}\{ds}_neural.parquet', index=False)

    # apples-to-apples: all methods' mean/median MASE on the SAME neural-eligible subset
    cl_df = pd.read_parquet(fr'{RES}\{ds}_classical.parquet')[['unique_id','naive_mase','sma_mase','ses_mase','croston_mase','sba_mase']]
    lg_df = pd.read_parquet(fr'{RES}\{ds}_lgbm.parquet')[['unique_id','lgbm_mase']]
    elig = per[per['nhits_mase'].notna()]      # same neural-eligible series for every method
    comp = elig[['unique_id','nhits_mase','deepar_mase']].merge(cl_df, on='unique_id').merge(lg_df, on='unique_id')
    def mm(col):
        v = comp[col].replace([np.inf,-np.inf], np.nan)
        return [round(float(np.nanmean(v)),3), round(float(np.nanmedian(v)),3)]
    subset_cmp = {k: mm(c) for k,c in [('Naive','naive_mase'),('SMA','sma_mase'),('SES','ses_mase'),
                  ('Croston','croston_mase'),('SBA','sba_mase'),('LightGBM','lgbm_mase'),
                  ('NHITS','nhits_mase'),('DeepAR','deepar_mase')]}
    summ = {'dataset': ds, 'steps': STEPS, 'n_scored': int(per['nhits_mase'].notna().sum()),
            'NHITS_mean_MASE': round(float(np.nanmean(per['nhits_mase'])),3),
            'NHITS_median_MASE': round(float(np.nanmedian(per['nhits_mase'])),3),
            'DeepAR_mean_MASE': round(float(np.nanmean(per['deepar_mase'])),3),
            'DeepAR_median_MASE': round(float(np.nanmedian(per['deepar_mase'])),3),
            'subset_n': int(len(comp)),
            'subset_comparison_mean_median': subset_cmp, 'by_class': {}}
    for cl in ['Smooth','Intermittent','Erratic','Lumpy']:
        sub = per[per['class']==cl]
        if len(sub):
            summ['by_class'][cl] = {'n': int(len(sub)),
                'NHITS': round(float(np.nanmean(sub['nhits_mase'])),3),
                'DeepAR': round(float(np.nanmean(sub['deepar_mase'])),3)}
    with open(fr'{RES}\{ds}_neural_summary.json','w') as f: json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2), flush=True)
    print(f'[{ds}] saved {ds}_neural.parquet + summary', flush=True)

if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'or2'
    try:
        main(ds)
    except Exception:
        traceback.print_exc(); sys.exit(1)
