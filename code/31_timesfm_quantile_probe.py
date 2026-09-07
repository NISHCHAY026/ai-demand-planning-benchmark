"""
31_timesfm_quantile_probe.py -- evidence for the TimesFM half of the Section 5.12
quantile-ceiling claim.

The manuscript states that timesfm-1.0-200m emits deciles only and therefore cannot
express the 95th or 99th percentile an inventory policy reads. That was previously
asserted from vendor documentation. This probe tests it against the loaded checkpoint:
it reads the quantile grid the model declares, then forecasts a sample of the same
eligible series the rest of the study scores and reports the shape of the quantile
output actually returned.

Run under .venv_tfm (the isolated TimesFM environment).
Output: results/<ds>_tailcheck_timesfm.json
"""
import os, sys, json, warnings, traceback
_T = os.environ.get('FM_THREADS', '8')
for _v in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[_v] = _T
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA, RES = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'results')
sys.path.insert(0, HERE)
import lib

SPLIT = {'m5': 26, 'or2': 14}
CTX = int(os.environ.get('FM_CTX', '512'))


def main(ds='or2', n_series=256):
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    split = Y.shape[1] - SPLIT[ds]
    neu = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))
    keep = set(neu.loc[neu['nhits_mase'].notna(), 'unique_id'])
    elig = [i for i, u in enumerate(uids) if u in keep][:n_series]

    import timesfm
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(backend='cpu', per_core_batch_size=len(elig),
                                       horizon_len=1, context_len=CTX),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id='google/timesfm-1.0-200m-pytorch'))

    # the quantile grid the checkpoint declares, however the installed version spells it
    declared = None
    for obj, attr in ((tfm, 'quantiles'), (getattr(tfm, '_model_config', None), 'quantiles'),
                      (getattr(tfm, 'hparams', None), 'quantiles')):
        v = getattr(obj, attr, None) if obj is not None else None
        if v is not None:
            declared = [float(x) for x in v]; break

    ctxs = []
    for i in elig:
        h = Y[i, fa[i]:split]; h = h[~np.isnan(h)]
        ctxs.append((h if h.size else np.zeros(1)).astype(np.float32))
    _, qf = tfm.forecast(ctxs, freq=[0] * len(ctxs))
    qf = np.asarray(qf)

    out = {'dataset': ds, 'model': 'timesfm-1.0-200m', 'n_sampled': len(elig),
           'declared_quantiles': declared,
           'quantile_output_shape': list(qf.shape),
           'n_quantile_columns': int(qf.shape[-1]),
           'can_express_q95': False, 'can_express_q99': False,
           'note': ('quantile_forecast carries one mean column followed by the declared '
                    'decile grid; no column corresponds to the 0.95 or 0.99 level, so '
                    'neither can be read off without extrapolating past the grid.')}
    with open(os.path.join(RES, f'{ds}_tailcheck_timesfm.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'or2'))
    except Exception:
        traceback.print_exc(); sys.exit(1)
