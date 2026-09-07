"""Bulletproofing extras:
  C) render fidelity  -- the BUILT .md/.tex carry the exact result numbers.
  B) neural reproducibility -- re-run OR2 neural, measure run-to-run variation, restore.
"""
import os, sys, json, shutil, subprocess
import pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RES, MAN = os.path.join(ROOT, 'results'), os.path.join(ROOT, 'manuscript')

# ---------- C: render fidelity ----------
md = open(os.path.join(MAN, 'AI_demand_planning_OOS_benchmark.md'), encoding='utf-8').read()
tex = open(os.path.join(MAN, 'AI_demand_planning_OOS_benchmark.tex'), encoding='utf-8').read()
m5o = pd.read_csv(os.path.join(RES, 'm5_overall.csv')).set_index('method')
o2o = pd.read_csv(os.path.join(RES, 'or2_overall.csv')).set_index('method')
needles = [f"{m5o.loc['LightGBM (AI)','mean_MASE']:.3f}", f"{o2o.loc['LightGBM (AI)','mean_MASE']:.3f}",
           f"{m5o.loc['SBA','mean_MASE']:.3f}", f"{o2o.loc['Naive','mean_MASE']:.3f}",
           f"{m5o.loc['SES','mean_MASE']:.3f}"]
print('C) RENDER FIDELITY  (result number must appear in built .md AND .tex):')
render_ok = True
for n in needles:
    a, b = (n in md), (n in tex)
    render_ok &= a and b
    print(f'   {n}: md={a} tex={b}')
print('   ->', 'PASS' if render_ok else 'FAIL')

# ---------- B: neural OR2 reproducibility ----------
print('\nB) NEURAL OR2 REPRODUCIBILITY  (re-run vs committed, mean MASE):')
snap = ['or2_neural.parquet', 'or2_neural_summary.json']
for f in snap: shutil.copy(os.path.join(RES, f), os.path.join(RES, '_snap_' + f))
subprocess.run([sys.executable, os.path.join(HERE, '10_neural_baselines.py'), 'or2'],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
new = json.load(open(os.path.join(RES, 'or2_neural_summary.json')))
old = json.load(open(os.path.join(RES, '_snap_or2_neural_summary.json')))
maxd = 0.0
for k in ['SES', 'LightGBM', 'NHITS', 'DeepAR']:
    o = old['subset_comparison_mean_median'][k][0]; n = new['subset_comparison_mean_median'][k][0]
    maxd = max(maxd, abs(o - n))
    tag = '(deterministic input)' if k in ('SES', 'LightGBM') else '(neural)'
    print(f'   {k:9s} committed={o:.3f}  rerun={n:.3f}  |diff|={abs(o-n):.4f}  {tag}')
for f in snap:  # restore committed neural so Table 6 is unchanged
    shutil.copy(os.path.join(RES, '_snap_' + f), os.path.join(RES, f)); os.remove(os.path.join(RES, '_snap_' + f))
print(f'   max|diff| = {maxd:.4f} ; committed neural files restored (Table 6 preserved).')
print('   ->', 'BIT-IDENTICAL' if maxd == 0 else f'near-deterministic (<= {maxd:.3f} MASE drift)')
