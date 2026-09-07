"""
28_probabilistic.py <m5|or2> <empirical|chronos_bolt_small|chronos_bolt_base>

Step 4 of the IJF revision plan: a distributional evaluation, answering Kolassa (2016)
directly rather than deferring it to future work.

Point accuracy is not what an inventory policy consumes. A stocking decision reads an
upper quantile of the predictive distribution, so we score the methods that emit one
under the SAME one-step rolling-origin protocol, on the SAME eligible series, with:

  * scaled pinball loss at the quantiles {0.5, 0.6, 0.7, 0.8, 0.9} -- the levels the
    scored models can actually express, see tail_check() and QLEVELS below -- divided per
    series by the in-sample naive MAE so it is scale-free and directly comparable with the
    MASE numbers elsewhere in the paper; and
  * empirical coverage at the nominal 90th percentile, which is the quantity a planner is
    implicitly promising when they set a service level. The 95th and 99th are the levels an
    inventory policy actually reads, and that neither Chronos-Bolt checkpoint nor TimesFM
    can emit, which is the point Section 5.12 makes rather than a gap in this script.

Methods scored:
  empirical            -- per-series empirical quantiles of the TRAINING window, held
                          constant across the test window. A model-free benchmark: it is
                          what a planner gets from the demand history alone, and it is
                          strong on intermittent data because it reproduces the zeros.
  chronos_bolt_small/base -- native predictive quantiles, zero-shot, no fitting.

TimesFM is deliberately absent: the public timesfm-1.0-200m checkpoint exposes only
decile quantiles, so it cannot be scored at the 95th and 99th percentiles an inventory
policy actually reads. That limitation is reported in the manuscript rather than worked
around by interpolating quantiles the model does not emit.

Resumable in the same way as 18_foundation_models.py (this box kills long CPU jobs):
checkpoints after every origin and self-limits to FM_MAX_SECONDS. Re-run until it prints
COMPLETE. Exit 0 = done, 3 = more work remains.

Output: results/<ds>_prob_<model>.parquet   (per-series scaled pinball + coverage)
"""
import os, sys, json, time, gc, warnings, traceback
_THREADS = os.environ.get('FM_THREADS', '8')
for _v in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[_v] = _THREADS
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
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
MAX_SECONDS = int(os.environ.get('FM_MAX_SECONDS', '480'))
# Scored at the quantiles the models can actually express. Chronos-Bolt is trained on
# deciles 0.1-0.9 and TimesFM-1.0 emits deciles only; asking either for the 0.95 or 0.99
# quantile returns the 0.9 value CLAMPED, not an error (Section 5.12 and tail_check()).
QLEVELS = [0.5, 0.6, 0.7, 0.8, 0.9]
COVER = [0.9]
HF = {'chronos_bolt_small': 'amazon/chronos-bolt-small',
      'chronos_bolt_base': 'amazon/chronos-bolt-base'}


def eligible_rows(ds, uids):
    """Exactly the series the neural/foundation comparison scored."""
    neu = pd.read_parquet(os.path.join(RES, f'{ds}_neural.parquet'))
    keep = set(neu.loc[neu['nhits_mase'].notna(), 'unique_id'])
    return np.array([i for i, u in enumerate(uids) if u in keep], dtype=int)


def q_empirical(Y, fa, elig, split, T):
    """Constant per-series training-window empirical quantiles."""
    n = Y.shape[0]
    Q = np.full((n, T, len(QLEVELS)), np.nan, dtype=np.float32)
    for i in elig:
        h = Y[i, fa[i]:split]
        h = h[~np.isnan(h)]
        if h.size == 0:
            continue
        qv = np.quantile(h, QLEVELS).astype(np.float32)
        Q[i, split:T, :] = qv
    return Q, True


def q_chronos(Y, fa, elig, split, T, label, ckpt):
    import torch
    torch.set_num_threads(int(os.environ.get('FM_THREADS', '8')))
    from chronos import BaseChronosPipeline
    n = Y.shape[0]
    if os.path.exists(ckpt):
        Q = np.load(ckpt)
        if Q.shape != (n, T, len(QLEVELS)):
            Q = np.full((n, T, len(QLEVELS)), np.nan, dtype=np.float32)
    else:
        Q = np.full((n, T, len(QLEVELS)), np.nan, dtype=np.float32)
    todo = [t for t in range(split, T) if np.isnan(Q[elig, t, 0]).any()]
    print(f'    origins todo={len(todo)}/{T-split} (self-limit {MAX_SECONDS}s)', flush=True)
    if not todo:
        return Q, True
    pipe = BaseChronosPipeline.from_pretrained(HF[label], device_map='cpu',
                                               dtype=torch.float32)
    t0 = time.time()
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
                q, _m = pipe.predict_quantiles(ctxs, prediction_length=1,
                                               quantile_levels=QLEVELS)
            Q[rows, t, :] = np.clip(q[:, 0, :].cpu().numpy().astype(np.float32), 0, None)
            del ctxs, q, _m
        tmp = ckpt + '.tmp.npy'; np.save(tmp, Q)
        # same Windows replace race as 18_foundation_models.py: retry, never abort on it
        for _try in range(8):
            try:
                os.replace(tmp, ckpt); break
            except PermissionError:
                time.sleep(0.5 * (_try + 1))
        else:
            print(f'    WARNING: checkpoint {os.path.basename(ckpt)} not updated', flush=True)
        gc.collect()
        el = time.time() - t0
        print(f'    origin {k+1}/{len(todo)} (week {t}) saved  elapsed {el/60:.1f}m', flush=True)
        if el > MAX_SECONDS and (k + 1) < len(todo):
            print('    self-limit reached; re-run to continue', flush=True)
            return Q, False
    return Q, True


def score(Y, elig, split, T, Q, scale):
    """Scaled pinball loss (mean over quantiles) and coverage at the nominal levels."""
    n = Y.shape[0]
    pin = np.full(n, np.nan, dtype=np.float64)
    cov = {c: np.full(n, np.nan, dtype=np.float64) for c in COVER}
    te = np.arange(split, T)
    for i in elig:
        y = Y[i, te]
        m = ~np.isnan(y)
        if not m.any() or not np.isfinite(scale[i]) or scale[i] <= 0:
            continue
        yv = y[m]
        losses = []
        for j, ql in enumerate(QLEVELS):
            f = Q[i, te, j][m]
            if np.isnan(f).any():
                losses = []
                break
            d = yv - f
            losses.append(np.mean(np.where(d >= 0, ql * d, (ql - 1.0) * d)))
        if not losses:
            continue
        pin[i] = float(np.mean(losses)) / scale[i]
        for c in COVER:
            j = QLEVELS.index(c)
            f = Q[i, te, j][m]
            cov[c][i] = float(np.mean(yv <= f))
    return pin, cov


def tail_check(ds, label, n_series=256):
    """Evidence for the clamping claim: ask the model for 0.9, 0.95 and 0.99 on a sample
    of series and measure how often the three come back identical. A model that could
    express the upper tail would return three different numbers."""
    import torch
    torch.set_num_threads(int(os.environ.get('FM_THREADS', '8')))
    from chronos import BaseChronosPipeline
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    T = Y.shape[1]; split = T - SPLIT[ds]
    elig = eligible_rows(ds, uids)[:n_series]
    pipe = BaseChronosPipeline.from_pretrained(HF[label], device_map='cpu', dtype=torch.float32)
    ctxs = []
    for i in elig:
        h = Y[i, fa[i]:split]; h = h[~np.isnan(h)]
        ctxs.append(torch.tensor((h if h.size else np.zeros(1)).astype(np.float32)))
    with torch.no_grad():
        q, _ = pipe.predict_quantiles(ctxs, prediction_length=1,
                                      quantile_levels=[0.9, 0.95, 0.99])
    a = q[:, 0, :].cpu().numpy()
    same_95 = float(np.mean(np.isclose(a[:, 0], a[:, 1])))
    same_99 = float(np.mean(np.isclose(a[:, 0], a[:, 2])))
    out = {'dataset': ds, 'model': label, 'n_sampled': int(len(elig)),
           'share_q95_equals_q90': round(same_95, 4),
           'share_q99_equals_q90': round(same_99, 4)}
    with open(os.path.join(RES, f'{ds}_tailcheck_{label}.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2), flush=True)
    return 0


def main(ds, model):
    panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
    Y, uids, fa = lib.build_matrix(panel)
    n, T = Y.shape
    split = T - SPLIT[ds]
    elig = eligible_rows(ds, uids)
    cl = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))[
        ['unique_id', 'scale', 'class']]
    u2s = dict(zip(cl['unique_id'], cl['scale']))
    scale = np.array([u2s.get(u, np.nan) for u in uids], dtype=np.float64)
    print(f'[{ds}/{model}] n={n} T={T} split={split} eligible={len(elig)} '
          f'quantiles={QLEVELS}', flush=True)

    if model == 'empirical':
        Q, done = q_empirical(Y, fa, elig, split, T)
    else:
        ckpt = os.path.join(RES, f'_ckpt_prob_{ds}_{model}.npy')
        Q, done = q_chronos(Y, fa, elig, split, T, model, ckpt)
    if not done:
        print(f'[{ds}/{model}] PARTIAL', flush=True)
        return 3

    pin, cov = score(Y, elig, split, T, Q, scale)
    out = pd.DataFrame({'unique_id': uids[elig],
                        f'{model}_pinball': pin[elig],
                        **{f'{model}_cov{int(c*100)}': cov[c][elig] for c in COVER}})
    out = out.merge(cl, on='unique_id', how='left')
    out.to_parquet(os.path.join(RES, f'{ds}_prob_{model}.parquet'), index=False)
    ck = os.path.join(RES, f'_ckpt_prob_{ds}_{model}.npy')
    if os.path.exists(ck):
        os.remove(ck)
    # Record the aggregates as a first-class result. They were previously recomputed from
    # the parquet at render time, which put Table 12's numbers outside the reach of both
    # repro_backtest.py and the prose scan.
    sp = os.path.join(RES, f'{ds}_prob_summary.json')
    summ = json.load(open(sp)) if os.path.exists(sp) else {}
    summ[model] = {'n': int(np.isfinite(pin[elig]).sum()),
                   'scaled_pinball': round(float(np.nanmean(pin[elig])), 4),
                   **{f'coverage_{int(c*100)}': round(float(np.nanmean(cov[c][elig])) * 100, 2)
                      for c in COVER}}
    with open(sp, 'w') as f:
        json.dump(summ, f, indent=2, sort_keys=True)

    print(f'[{ds}/{model}] COMPLETE  scaled pinball mean={np.nanmean(pin[elig]):.4f}  '
          + '  '.join(f'cov{int(c*100)}={np.nanmean(cov[c][elig])*100:.1f}%' for c in COVER),
          flush=True)
    return 0


if __name__ == '__main__':
    ds = sys.argv[1] if len(sys.argv) > 1 else 'or2'
    model = sys.argv[2] if len(sys.argv) > 2 else 'empirical'
    try:
        if model == 'tailcheck':
            sys.exit(tail_check(ds, sys.argv[3] if len(sys.argv) > 3 else 'chronos_bolt_small'))
        sys.exit(main(ds, model))
    except Exception:
        traceback.print_exc(); sys.exit(1)
