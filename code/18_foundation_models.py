"""
18_foundation_models.py <m5|or2> [models]

Zero-shot time-series FOUNDATION MODELS (Chronos-Bolt family) under the *identical*
protocol as 03_classical / 04_lgbm / 10_neural:
  * one-step-ahead ROLLING ORIGIN over the last SPLIT[ds] weeks (h=1, refit=False).
  * scored on the SAME neural-eligible series; MASE uses the SAME in-sample naive
    'scale' from results/<ds>_classical.parquet.
  * point forecast = predictive MEDIAN (0.5 quantile), clipped at 0.

RESUMABLE: this box silently kills long (>~12 min) CPU jobs, so the rolling loop
CHECKPOINTS the forecast matrix to disk after every origin and SELF-LIMITS each run to
FM_MAX_SECONDS (default 480s) before exiting cleanly. Re-run the same command until it
prints "ALL MODELS COMPLETE"; each run resumes where the last left off.

Output: results/<ds>_foundation.parquet, results/<ds>_foundation_summary.json
        results/_ckpt_<ds>_<model>_F.npy  (per-model checkpoint; removed when finalised)
Exit code: 0 = all requested models complete; 3 = more work remains (re-run).
"""
import os, sys, json, time, gc, warnings, traceback
_THREADS = os.environ.get('FM_THREADS', '8')
for _v in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[_v] = _THREADS
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data')
RES = os.path.join(ROOT, 'results')
sys.path.insert(0, HERE)
import lib

SPLIT = {'m5': 26, 'or2': 14}
INPUT = {'m5': 52, 'or2': 26}
CHUNK = int(os.environ.get('FM_CHUNK', '256'))
MAX_SECONDS = int(os.environ.get('FM_MAX_SECONDS', '480'))   # self-limit per run
CHRONOS_MODELS = {
    'chronos_bolt_small': 'amazon/chronos-bolt-small',   # ~48M
    'chronos_bolt_base':  'amazon/chronos-bolt-base',    # ~205M
}


def load_chronos(hf_id):
    import torch
    torch.set_num_threads(int(os.environ.get('FM_THREADS', '8')))
    from chronos import BaseChronosPipeline
    return BaseChronosPipeline.from_pretrained(hf_id, device_map='cpu', dtype=torch.float32)


def chronos_rolling(pipe, Y, fa, elig, split, T, ckpt):
    """Resumable rolling 1-step forecast. Returns (F, complete_bool). Checkpoints F to
    `ckpt` after each origin; self-limits to MAX_SECONDS."""
    import torch
    n = Y.shape[0]
    if os.path.exists(ckpt):
        F = np.load(ckpt)
        if F.shape != (n, T):
            F = np.full((n, T), np.nan, dtype=np.float32)
    else:
        F = np.full((n, T), np.nan, dtype=np.float32)
    origins = list(range(split, T))
    todo = [t for t in origins if np.isnan(F[elig, t]).any()]
    print(f'    origins done={len(origins)-len(todo)}/{len(origins)}  todo={len(todo)}  '
          f'(self-limit {MAX_SECONDS}s)', flush=True)
    t0 = time.time(); fc = 0
    for k, t in enumerate(todo):
        for c0 in range(0, len(elig), CHUNK):
            rows = elig[c0:c0 + CHUNK]
            ctxs = []
            for i in rows:
                h = Y[i, fa[i]:t]; h = h[~np.isnan(h)]
                if h.size == 0:
                    h = np.zeros(1, dtype=np.float32)
                ctxs.append(torch.tensor(h.astype(np.float32)))
            with torch.no_grad():
                q, _m = pipe.predict_quantiles(ctxs, prediction_length=1, quantile_levels=[0.5])
            F[rows, t] = np.clip(q[:, 0, 0].cpu().numpy().astype(np.float32), 0, None)
            fc += len(rows)
            del ctxs, q, _m
        tmp = ckpt + '.tmp.npy'
        np.save(tmp, F); os.replace(tmp, ckpt)     # atomic per-origin checkpoint
        gc.collect()
        el = time.time() - t0
        print(f'    origin {k+1}/{len(todo)} (week {t}) saved  {fc/max(el,1e-9):,.0f} fc/s  '
              f'elapsed {el/60:.1f}m', flush=True)
        if el > MAX_SECONDS and (k + 1) < len(todo):
            print(f'    self-limit reached; exiting to be re-run (resumes at next origin)', flush=True)
            return F, False
    return F, True


def finalize(ds, out, present, split, Y, uids):
    """Write the unified summary from whatever foundation models are complete in `out`."""
    cl = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))[
        ['unique_id', 'naive_mase', 'sma_mase', 'ses_mase', 'croston_mase', 'sba_mase']]
    lg = pd.read_parquet(os.path.join(RES, f'{ds}_lgbm.parquet'))[['unique_id', 'lgbm_mase']]
    neu = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))[
        ['unique_id', 'nhits_mase', 'deepar_mase']]
    fm_cols = [f'{m}_mase' for m in present]
    comp = (out[['unique_id', 'class'] + fm_cols]
            .merge(cl, on='unique_id').merge(lg, on='unique_id').merge(neu, on='unique_id'))
    method_cols = ['naive_mase', 'sma_mase', 'ses_mase', 'croston_mase', 'sba_mase',
                   'lgbm_mase', 'nhits_mase', 'deepar_mase'] + fm_cols
    comp = comp.replace([np.inf, -np.inf], np.nan).dropna(subset=method_cols)
    mm = lambda c: [round(float(np.nanmean(comp[c])), 3), round(float(np.nanmedian(comp[c])), 3)]
    label_map = [('Naive', 'naive_mase'), ('SMA', 'sma_mase'), ('SES', 'ses_mase'),
                 ('Croston', 'croston_mase'), ('SBA', 'sba_mase'), ('LightGBM', 'lgbm_mase'),
                 ('NHITS', 'nhits_mase'), ('DeepAR', 'deepar_mase')] + [(m, f'{m}_mase') for m in present]
    summ = {'dataset': ds, 'models': present, 'chunk': CHUNK, 'test_weeks': SPLIT[ds],
            'input_window': INPUT[ds], 'subset_n_all_methods': int(len(comp)),
            'subset_comparison_mean_median': {k: mm(c) for k, c in label_map},
            'by_class': {}}
    for cln in ['Smooth', 'Erratic', 'Intermittent', 'Lumpy']:
        s = comp[comp['class'] == cln]
        if len(s):
            summ['by_class'][cln] = {'n': int(len(s)),
                                     **{k: round(float(np.nanmean(s[c])), 3) for k, c in label_map}}
    with open(os.path.join(RES, f'{ds}_foundation_summary.json'), 'w') as f:
        json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2), flush=True)


def main(ds, model_labels):
    print(f'[{ds}] foundation benchmark  models={model_labels}  chunk={CHUNK}', flush=True)
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    split = T - SPLIT[ds]
    uid2row = {u: i for i, u in enumerate(uids)}
    neu = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))
    elig_uids = neu.loc[neu['nhits_mase'].notna(), 'unique_id'].values
    elig = np.array([uid2row[u] for u in elig_uids if u in uid2row], dtype=int)
    cl = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))[['unique_id', 'scale', 'class']]
    uid2scale = dict(zip(cl['unique_id'], cl['scale']))
    scale = np.array([uid2scale.get(u, np.nan) for u in uids], dtype=np.float32)
    print(f'[{ds}] n={n} T={T} split={split} eligible={len(elig)}', flush=True)
    _, te = lib.col_slices(Y, split)

    fpath = os.path.join(RES, f'{ds}_foundation.parquet')
    if os.path.exists(fpath):
        out = pd.read_parquet(fpath)
    else:
        out = (pd.DataFrame({'unique_id': uids[elig], 'scale': scale[elig]})
               .merge(cl[['unique_id', 'class']], on='unique_id', how='left'))

    all_complete = True
    for label in model_labels:
        col = f'{label}_mase'
        if col in out.columns and out[col].notna().any():
            print(f'[{ds}] {label} already complete; skipping', flush=True); continue
        ckpt = os.path.join(RES, f'_ckpt_{ds}_{label}_F.npy')
        print(f'[{ds}] loading {label}...', flush=True)
        pipe = load_chronos(CHRONOS_MODELS[label]); print(f'[{ds}] loaded; forecasting...', flush=True)
        F, complete = chronos_rolling(pipe, Y, fa, elig, split, T, ckpt)
        del pipe; gc.collect()
        if not complete:
            print(f'[{ds}] {label} PARTIAL -- re-run to continue', flush=True)
            all_complete = False
            break
        oos_mae, _ = lib.mae_over(F, Y, te)
        mase = oos_mae / scale
        sub = pd.DataFrame({'unique_id': uids, f'{label}_oos_mae': oos_mae, col: mase})
        sub = sub[sub['unique_id'].isin(uids[elig])]
        for c in [f'{label}_oos_mae', col]:
            if c in out.columns:
                out = out.drop(columns=c)
        out = out.merge(sub, on='unique_id', how='left')
        out.loc[~np.isfinite(out[col]), col] = np.nan
        out.to_parquet(fpath, index=False)
        if os.path.exists(ckpt):
            os.remove(ckpt)
        print(f'[{ds}] {label} COMPLETE: mean MASE={np.nanmean(out[col]):.3f} '
              f'median={np.nanmedian(out[col]):.3f}', flush=True)

    present = [m for m in CHRONOS_MODELS if f'{m}_mase' in out.columns and out[f'{m}_mase'].notna().any()]
    if all_complete and all((f'{m}_mase' in out.columns and out[f'{m}_mase'].notna().any())
                            for m in model_labels):
        finalize(ds, out, present, split, Y, uids)
        print(f'[{ds}] ALL MODELS COMPLETE', flush=True)
        return 0
    return 3


if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'or2'
    models = sys.argv[2].split(',') if len(sys.argv) > 2 else ['chronos_bolt_small']
    bad = [m for m in models if m not in CHRONOS_MODELS]
    if bad:
        print('unknown models:', bad); sys.exit(2)
    try:
        sys.exit(main(ds, models))
    except Exception:
        traceback.print_exc(); sys.exit(1)
