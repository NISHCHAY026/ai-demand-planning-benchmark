"""
36_grid_sensitivity.py -- does the narrow tuning grid handicap the classical arm?

The per-series tuner selects a boundary value of the smoothing constant on 54% to 89% of
series depending on method and panel. Taken at face value that says the grid, not the data,
is deciding the parameter, and that the classical baseline in a machine-learning comparison
is under-tuned. This script tests the claim rather than arguing about it: it re-runs every
tuned classical method on a deliberately wide grid (lib.WIDE_*) and compares.

The answer is the opposite of the objection. Widening makes the level-based methods WORSE
out of sample. On short, sparse histories the training-window criterion is noisy, and the
extra freedom is spent fitting that noise: the series that select a high smoothing constant
once allowed to are precisely the ones with the fewest active training weeks, and they score
worse. The narrow literature range acts as a shrinkage prior. The Croston family, whose
criterion is better behaved, does improve slightly.

Output: results/grid_sensitivity.json
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA, RES = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'results')
sys.path.insert(0, HERE)
import lib

SPLIT = {'m5': 26, 'or2': 14}


def methods(Y, fa, split):
    return [
        ('SMA',     lambda p: lib.f_sma(Y, fa, p),                        lib.SMA_K, lib.WIDE_SMA_K),
        ('SES',     lambda p: lib.f_ses(Y, fa, p, split),                 lib.SES_A, lib.WIDE_SES_A),
        ('Croston', lambda p: lib.f_croston(Y, fa, p, split, sba=False),  lib.CRO_A, lib.WIDE_CRO_A),
        ('SBA',     lambda p: lib.f_croston(Y, fa, p, split, sba=True),   lib.CRO_A, lib.WIDE_CRO_A),
        ('TSB',     lambda p: lib.f_tsb(Y, fa, p, split),                 lib.CRO_A, lib.WIDE_CRO_A),
        ('MAPA',    lambda p: lib.f_mapa(Y, fa, p, split),                lib.SES_A, lib.WIDE_SES_A),
    ]


def sweep(build, grid, Y, tr, te, scale, el):
    """Per-series training-MAE selection, returning OOS mean MASE and the selected params."""
    n = Y.shape[0]
    best = np.full(n, np.inf, dtype=np.float32)
    oos = np.full(n, np.nan, dtype=np.float32)
    sel = np.full(n, -1, dtype=int)
    for j, p in enumerate(grid):
        F = build(p)
        crit, _ = lib.mae_over(F, Y, tr)
        xm, _ = lib.mae_over(F, Y, te)
        b = np.isfinite(crit) & (crit < best)
        best = np.where(b, crit, best)
        oos = np.where(b, xm, oos)
        sel = np.where(b, j, sel)
        del F
    chosen = np.array([grid[i] if i >= 0 else np.nan for i in sel], dtype=float)
    return float(np.nanmean((oos / scale)[el])), chosen


# Convergence check: grids extended beyond WIDE_*, to show the wide grids are not themselves
# the binding constraint. Section 5.13 quotes these movements, so they are recorded here
# instead of living only in a comment.
EXTRA_CRO = [0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2,
             0.3, 0.4, 0.5, 0.65, 0.8, 0.9, 0.95, 0.99]
EXTRA_SES = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75,
             0.9, 0.95, 0.99]


def main():
    out = {}
    for ds in ('m5', 'or2'):
        panel = pd.read_parquet(os.path.join(DATA, f'{ds}_weekly.parquet'))
        Y, uids, fa = lib.build_matrix(panel)
        T = Y.shape[1]; split = T - SPLIT[ds]
        tr, te = lib.col_slices(Y, split)
        scale = lib.naive_scale(Y, fa, split)
        nnz = np.array([np.nansum(Y[i, fa[i]:split] > 0) for i in range(Y.shape[0])])
        el = np.isfinite(scale) & (scale > 0) & (nnz >= 2)
        rec = {'n_eligible': int(el.sum()), 'methods': {}}
        print(f'[{ds}] n={int(el.sum()):,}')
        for name, build, narrow, wide in methods(Y, fa, split):
            mn, cn = sweep(build, narrow, Y, tr, te, scale, el)
            mw, cw = sweep(build, wide, Y, tr, te, scale, el)
            edge = lambda c, g: float(np.mean((c[el] == min(g)) | (c[el] == max(g))))
            rec['methods'][name] = {
                'narrow': {'grid': list(narrow), 'mean_MASE': round(mn, 4),
                           'boundary_share': round(100 * edge(cn, narrow), 1)},
                'wide': {'grid_size': len(wide), 'mean_MASE': round(mw, 4),
                         'boundary_share': round(100 * edge(cw, wide), 1)},
                'wide_minus_narrow': round(mw - mn, 4)}
            print(f'   {name:8s} narrow {mn:.4f} (edge {100*edge(cn,narrow):4.1f}%)   '
                  f'wide {mw:.4f} (edge {100*edge(cw,wide):4.1f}%)   diff {mw-mn:+.4f}')
        # why widening hurts: who takes the newly available high smoothing constants
        _, cw_ses = sweep(methods(Y, fa, split)[1][1], lib.WIDE_SES_A, Y, tr, te, scale, el)
        hi = el & (cw_ses > max(lib.SES_A))
        lo = el & (cw_ses <= max(lib.SES_A))
        rec['ses_high_alpha_diagnostic'] = {
            'threshold': max(lib.SES_A),
            'share_above': round(100 * float(hi.sum()) / float(el.sum()), 1),
            'mean_train_active_weeks_above': round(float(nnz[hi].mean()), 1),
            'mean_train_active_weeks_below': round(float(nnz[lo].mean()), 1)}
        print(f"   SES series taking alpha > {max(lib.SES_A)} once allowed: "
              f"{rec['ses_high_alpha_diagnostic']['share_above']}%, "
              f"{rec['ses_high_alpha_diagnostic']['mean_train_active_weeks_above']} active training "
              f"weeks vs {rec['ses_high_alpha_diagnostic']['mean_train_active_weeks_below']} for the rest")
        if ds == 'or2':
            # only the sparse panel is quoted for convergence; it is where the grid matters
            conv = {}
            for name, build, narrow, wide in methods(Y, fa, split):
                if name not in ('Croston', 'SBA', 'MAPA'):
                    continue
                extra = EXTRA_SES if name == 'MAPA' else EXTRA_CRO
                mw = rec['methods'][name]['wide']['mean_MASE']
                me, _ = sweep(build, extra, Y, tr, te, scale, el)
                conv[name] = {'wide_mean_MASE': mw, 'extended_mean_MASE': round(me, 4),
                              'movement': round(abs(me - mw), 4), 'extended_grid_size': len(extra)}
                print(f'   convergence {name:8s} wide {mw:.4f} -> extended {me:.4f} '
                      f'(moves {abs(me-mw):.4f})')
            rec['convergence_beyond_wide'] = conv
        out[ds] = rec
    with open(os.path.join(RES, 'grid_sensitivity.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print('\nsaved results/grid_sensitivity.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
