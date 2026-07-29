"""
20_timesfm.py <m5|or2>  -- Google TimesFM-1.0-200M (PyTorch) under the SAME one-step
rolling-origin protocol, SAME neural-eligible series, SAME in-sample naive MASE
denominator as 18_foundation_models.py. Run with the .venv_tfm interpreter.

point forecast = TimesFM point output at horizon step 1, clipped at 0.
Output: results/<ds>_timesfm.parquet  (unique_id, scale, class, timesfm_200m_oos_mae,
        timesfm_200m_mase)
"""
import os, sys, json, time, warnings, traceback
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
for _v in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
    os.environ[_v] = os.environ.get('FM_THREADS', '8')
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
CHUNK = int(os.environ.get('FM_CHUNK', '256'))
CTX = 512   # timesfm-1.0-200m max context (multiple of patch len 32)


def main(ds):
    print(f'[{ds}] TimesFM-1.0-200M benchmark  chunk={CHUNK}', flush=True)
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    split = T - SPLIT[ds]
    uid2row = {u: i for i, u in enumerate(uids)}
    neu = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))
    elig_uids = neu.loc[neu['nhits_mase'].notna(), 'unique_id'].values
    eligible = np.array([uid2row[u] for u in elig_uids if u in uid2row], dtype=int)
    cl = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))[['unique_id', 'scale', 'class']]
    uid2scale = dict(zip(cl['unique_id'], cl['scale']))
    scale = np.array([uid2scale.get(u, np.nan) for u in uids], dtype=np.float32)
    print(f'[{ds}] n={n} T={T} split={split} eligible={len(eligible)}', flush=True)

    import timesfm
    t0 = time.time()
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(backend='cpu', per_core_batch_size=CHUNK,
                                       horizon_len=1, context_len=CTX),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id='google/timesfm-1.0-200m-pytorch'))
    print(f'[{ds}] loaded TimesFM in {time.time()-t0:.1f}s; forecasting...', flush=True)

    F = np.full((n, T), np.nan, dtype=np.float32)
    origins = list(range(split, T))
    n_elig = len(eligible)
    t0 = time.time(); done = 0
    for oi, t in enumerate(origins):
        for c0 in range(0, n_elig, CHUNK):
            rows = eligible[c0:c0 + CHUNK]
            ctxs = []
            for i in rows:
                h = Y[i, fa[i]:t]
                h = h[~np.isnan(h)]
                if h.size == 0:
                    h = np.zeros(1, dtype=np.float32)
                ctxs.append(h[-CTX:].astype(np.float32))
            pf, _ = tfm.forecast(ctxs, freq=[0] * len(ctxs))
            pf = np.asarray(pf)[:, 0]
            F[rows, t] = np.clip(pf, 0, None).astype(np.float32)
            done += len(rows)
        if oi == 0 or (oi + 1) % 5 == 0 or oi == len(origins) - 1:
            el = time.time() - t0; rate = done / max(el, 1e-9)
            eta = (n_elig * len(origins) - done) / max(rate, 1e-9)
            print(f'    origin {oi+1}/{len(origins)} (week {t})  {done:,}/{n_elig*len(origins):,} '
                  f'fc  {rate:,.0f} fc/s  elapsed {el/60:.1f}m  eta {eta/60:.1f}m', flush=True)

    _, te = lib.col_slices(Y, split)
    oos_mae, _ = lib.mae_over(F, Y, te)
    mase = oos_mae / scale
    out = pd.DataFrame({'unique_id': uids, 'timesfm_200m_oos_mae': oos_mae,
                        'timesfm_200m_mase': mase})
    out = out[out['unique_id'].isin(uids[eligible])].merge(cl, on='unique_id', how='left')
    out.loc[~np.isfinite(out['timesfm_200m_mase']), 'timesfm_200m_mase'] = np.nan
    out.to_parquet(os.path.join(RES, f'{ds}_timesfm.parquet'), index=False)
    print(f'[{ds}] TimesFM-200M: mean MASE={np.nanmean(out["timesfm_200m_mase"]):.3f} '
          f'median MASE={np.nanmedian(out["timesfm_200m_mase"]):.3f} '
          f'n={int(out["timesfm_200m_mase"].notna().sum())}', flush=True)
    print(f'[{ds}] saved {ds}_timesfm.parquet', flush=True)


if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'or2'
    try:
        main(ds)
    except Exception:
        traceback.print_exc(); sys.exit(1)
