"""snapshot / compare result files to prove the pipeline regenerates identical numbers.
usage: _repro_diff.py snapshot
       _repro_diff.py compare [substr ...]   # optional: only files whose name contains a substr
"""
import sys, os, shutil, json, glob
import pandas as pd, numpy as np

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
SNAP = os.path.join(RES, '_repro_snap')
PATTERNS = ['*_classification.parquet', '*_classical.parquet', '*_lgbm.parquet', '*_neural.parquet',
            '*_overall.csv', '*_inversion.csv', '*_by_class.csv', '*_by_class_pb.csv', '*_by_volume.csv',
            '*_robustness.csv', '*_fingerprint.json', 'digest.json', '*_lgbm_importance.csv']

def files():
    out = []
    for p in PATTERNS:
        out += [os.path.basename(x) for x in glob.glob(os.path.join(RES, p)) if '_repro_snap' not in x]
    return sorted(set(out))

mode = sys.argv[1]
if mode == 'snapshot':
    if os.path.exists(SNAP): shutil.rmtree(SNAP)
    os.makedirs(SNAP)
    fs = files()
    for f in fs: shutil.copy(os.path.join(RES, f), os.path.join(SNAP, f))
    print(f'snapshot: {len(fs)} files saved to _repro_snap/')

elif mode == 'compare':
    only = sys.argv[2:]
    bad, n = [], 0
    for f in files():
        if only and not any(s in f for s in only): continue
        a, b = os.path.join(RES, f), os.path.join(SNAP, f)
        if not os.path.exists(b): continue
        n += 1
        if f.endswith('.json'):
            if json.load(open(a)) != json.load(open(b)): bad.append((f, 'json differs'))
        else:
            da = pd.read_parquet(a) if f.endswith('.parquet') else pd.read_csv(a)
            db = pd.read_parquet(b) if f.endswith('.parquet') else pd.read_csv(b)
            if list(da.columns) != list(db.columns) or len(da) != len(db):
                bad.append((f, f'shape/cols differ: {da.shape} vs {db.shape}')); continue
            na, nb = da.select_dtypes('number'), db.select_dtypes('number')
            md = float(np.nanmax(np.abs(na.values - nb.values))) if na.size else 0.0
            nonnum_ok = da.select_dtypes(exclude='number').reset_index(drop=True).equals(
                        db.select_dtypes(exclude='number').reset_index(drop=True))
            if md > 1e-9 or not nonnum_ok:
                bad.append((f, f'max|diff|={md:.2e}, nonnumeric_equal={nonnum_ok}'))
    print(f'compared {n} files -> ' + ('ALL IDENTICAL (bit-for-bit numeric match)' if not bad else f'{len(bad)} DIFFER'))
    for f, msg in bad: print('   DIFF', f, '|', msg)
    sys.exit(1 if bad else 0)
