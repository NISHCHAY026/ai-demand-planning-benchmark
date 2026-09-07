"""
repro_backtest.py -- reproducibility backtest, LAYER 1 (consistency):
verify that EVERY hardcoded number in the manuscript tables (1 through 12), plus key
inline claims,
is exactly backed by the computed result files. Zero-tolerance (rounded values must match).
Exit non-zero on any mismatch.
"""
import os, re, json, sys
import pandas as pd, numpy as np
import manuscript_content as MC

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
def csv(name): return pd.read_csv(os.path.join(RES, name))
def js(name):  return json.load(open(os.path.join(RES, name)))
TOL = 0.0006
fails, checks = [], 0

def eq(a, b, ctx):
    global checks
    checks += 1
    try:
        if abs(float(a) - float(b)) > TOL:
            fails.append(f'{ctx}: manuscript={a} vs result={b}')
    except Exception as e:
        fails.append(f'{ctx}: cannot compare {a!r} vs {b!r} ({e})')

blocks = MC.blocks()
tables = {b[4].split('.')[0]: b for b in blocks if b[0] == 'table' and b[4]}  # 'Table N' -> block

# ---------- Table 2: inversion ----------
t = tables['Table 2']; rows = t[2]
m5i = csv('m5_inversion.csv').set_index('method'); o2i = csv('or2_inversion.csv').set_index('method')
for r in rows:                       # [method, M5 inPB, M5 oosMASE, M5 oosPB, OR2 inPB, OR2 oosMASE, OR2 oosPB]
    m = r[0]
    eq(r[1], m5i.loc[m, 'insample_PB_pct'], f'T2 {m} M5 in-PB')
    eq(r[2], m5i.loc[m, 'oos_mean_MASE'],   f'T2 {m} M5 oosMASE')
    eq(r[3], m5i.loc[m, 'oos_PB_pct'],      f'T2 {m} M5 oosPB')
    eq(r[4], o2i.loc[m, 'insample_PB_pct'], f'T2 {m} OR2 in-PB')
    eq(r[5], o2i.loc[m, 'oos_mean_MASE'],   f'T2 {m} OR2 oosMASE')
    eq(r[6], o2i.loc[m, 'oos_PB_pct'],      f'T2 {m} OR2 oosPB')

# ---------- Table 3: overall ----------
t = tables['Table 3']; rows = t[2]
m5o = csv('m5_overall.csv').set_index('method'); o2o = csv('or2_overall.csv').set_index('method')
for r in rows:                       # [method, M5 mean, M5 med, M5 PB, OR2 mean, OR2 med, OR2 PB]
    m = r[0].replace('**', '')
    v = [x.replace('**', '') for x in r]
    eq(v[1], m5o.loc[m, 'mean_MASE'],   f'T3 {m} M5 mean'); eq(v[2], m5o.loc[m, 'median_MASE'], f'T3 {m} M5 med')
    eq(v[3], m5o.loc[m, 'PB_pct'],      f'T3 {m} M5 PB')
    eq(v[4], o2o.loc[m, 'mean_MASE'],   f'T3 {m} OR2 mean'); eq(v[5], o2o.loc[m, 'median_MASE'], f'T3 {m} OR2 med')
    eq(v[6], o2o.loc[m, 'PB_pct'],      f'T3 {m} OR2 PB')

# ---------- Table 4: by SBC class (SES / SBA / AI) ----------
t = tables['Table 4']; rows = t[2]
m5c = csv('m5_by_class.csv').set_index('class'); o2c = csv('or2_by_class.csv').set_index('class')
for r in rows:   # [class, M5 SES, M5 SBA, M5 TSB, M5 ML, OR2 SES, OR2 SBA, OR2 TSB, OR2 ML]
    c = r[0]
    eq(r[1], m5c.loc[c, 'SES'], f'T4 {c} M5 SES'); eq(r[2], m5c.loc[c, 'SBA'], f'T4 {c} M5 SBA')
    eq(r[3], m5c.loc[c, 'TSB'], f'T4 {c} M5 TSB')
    eq(r[4], m5c.loc[c, 'LightGBM (global)'], f'T4 {c} M5 ML')
    eq(r[5], o2c.loc[c, 'SES'], f'T4 {c} OR2 SES'); eq(r[6], o2c.loc[c, 'SBA'], f'T4 {c} OR2 SBA')
    eq(r[7], o2c.loc[c, 'TSB'], f'T4 {c} OR2 TSB')
    eq(r[8], o2c.loc[c, 'LightGBM (global)'], f'T4 {c} OR2 ML')

# ---------- Table 5: robustness ----------
t = tables['Table 5']; rows = t[2]
m5r = csv('m5_robustness.csv').set_index('test_weeks'); o2r = csv('or2_robustness.csv').set_index('test_weeks')
meth = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'MAPA', 'LightGBM']
for r in rows:                       # ['M5 — 13 wk', Naive..LightGBM]
    lab = r[0]
    ds = 'm5' if 'M5' in lab else 'or2'
    wk = int(re.search(r'(\d+)\s*wk', lab).group(1))
    src = (m5r if ds == 'm5' else o2r).loc[wk]
    for j, mth in enumerate(meth):
        eq(r[j+1].replace('**',''), src[mth], f'T5 {lab} {mth}')

# ---------- Table 6: neural (dynamic) vs summaries ----------
t = tables['Table 6']; rows = t[2]
m5n = js('m5_neural_summary.json'); o2n = js('or2_neural_summary.json')
keymap = {'SES':'SES','LightGBM (AI)':'LightGBM','LightGBM (global)':'LightGBM',
          'NHITS':'NHITS','DeepAR':'DeepAR'}
for r in rows:                       # [Method, M5 mean, M5 med, OR2 mean, OR2 med]
    k = keymap[r[0]]
    eq(r[1], m5n['subset_comparison_mean_median'][k][0], f'T6 {k} M5 mean')
    eq(r[2], m5n['subset_comparison_mean_median'][k][1], f'T6 {k} M5 med')
    eq(r[3], o2n['subset_comparison_mean_median'][k][0], f'T6 {k} OR2 mean')
    eq(r[4], o2n['subset_comparison_mean_median'][k][1], f'T6 {k} OR2 med')

# ---------- Table 7: MCB mean ranks vs mcb.json ----------
mcbj = js('mcb.json')
t7 = tables['Table 7']
for r in t7[2]:
    m = r[0]
    eq(r[1], mcbj['m5']['core6_fullset']['mean_ranks'][m], f'T7 {m} M5 rank')
    eq(r[2], mcbj['or2']['core6_fullset']['mean_ranks'][m], f'T7 {m} OR2 rank')
for ds in ['m5', 'or2']:
    checks += 1
    cd = f"{mcbj[ds]['core6_fullset']['critical_distance']:.3f}"
    if cd not in t7[4]:
        fails.append(f'T7 note: CD {cd} for {ds} not quoted')

# ---------- Table 8: RMSSE sensitivity vs rmsse.json ----------
rms = js('rmsse.json')
t8 = tables['Table 8']
for r in t8[2]:
    m = r[0]
    eq(r[1], rms['m5']['core6_fullset']['mean_RMSSE'][m],  f'T8 {m} M5 mean RMSSE')
    eq(r[2], rms['m5']['core6_fullset']['mcb']['mean_ranks'][m],  f'T8 {m} M5 rank')
    eq(r[3], rms['or2']['core6_fullset']['mean_RMSSE'][m], f'T8 {m} OR2 mean RMSSE')
    eq(r[4], rms['or2']['core6_fullset']['mcb']['mean_ranks'][m], f'T8 {m} OR2 rank')
# by-class and 8-method claims quoted in §5.9 prose
_prose = ' '.join(b[1] for b in blocks if b[0] == 'p' and isinstance(b[1], str))
a8m, a8o = rms['m5']['all8_subset'], rms['or2']['all8_subset']
for needle, ctx in [(f"{rms['m5']['core6_by_class']['Intermittent']['LightGBM (global)']:.3f}", 'M5 int LGBM RMSSE'),
                    (f"{rms['m5']['core6_by_class']['Lumpy']['LightGBM (global)']:.3f}", 'M5 lumpy LGBM RMSSE'),
                    (f"{a8m['mcb']['mean_ranks']['LightGBM (global)']:.2f}", 'M5 all8 LGBM rank'),
                    (f"{a8o['mean_RMSSE']['SES']:.3f}", 'OR2 all8 SES mean RMSSE'),
                    (f"{a8o['mean_RMSSE']['NHITS']:.3f}", 'OR2 all8 NHITS mean RMSSE'),
                    (f"{a8o['mcb']['mean_ranks']['DeepAR']:.2f}", 'OR2 all8 DeepAR rank')]:
    checks += 1
    if needle not in _prose:
        fails.append(f'PROSE {ctx}: "{needle}" not found in manuscript')

# ---------- Table 1: dataset overview vs fingerprint JSONs ----------
m5f, o2f = js('m5_fingerprint.json'), js('or2_fingerprint.json')
t1 = tables['Table 1']
def find1(sub): return next(r for r in t1[2] if sub in r[0])
num = lambda s: float(re.search(r'[\d.]+', s).group())
eq(find1('Series')[1].replace(',', ''), m5f['n_series'], 'T1 M5 n_series')
eq(find1('Series')[2].replace(',', ''), o2f['n_series'], 'T1 OR2 n_series')
eq(num(find1('Window')[1]), m5f['n_weeks'], 'T1 M5 n_weeks')
eq(num(find1('Window')[2]), o2f['n_weeks'], 'T1 OR2 n_weeks')
eq(num(find1('Zero-demand')[1]), m5f['pct_zero_weeks'], 'T1 M5 zero%')
eq(num(find1('Zero-demand')[2]), o2f['pct_zero_weeks'], 'T1 OR2 zero%')
adi5, cv5 = find1('Median ADI')[1].split('/'); adi2, cv2 = find1('Median ADI')[2].split('/')
eq(num(adi5), m5f['median_ADI'], 'T1 M5 ADI'); eq(num(cv5), m5f['median_CV2'], 'T1 M5 CV2')
eq(num(adi2), o2f['median_ADI'], 'T1 OR2 ADI'); eq(num(cv2), o2f['median_CV2'], 'T1 OR2 CV2')
eq(num(find1('Dominant')[1]), m5f['class_dist_pct']['Smooth'], 'T1 M5 dominant Smooth%')
eq(num(find1('Dominant')[2]), o2f['class_dist_pct']['Lumpy'], 'T1 OR2 dominant Lumpy%')

# ---------- Inline claims: key numbers must appear SOMEWHERE in the manuscript (prose or tables) ----------
def cellstxt(b): return ' '.join(str(x) for x in sum(b[2], [])) + ' ' + (b[4] or '')
fulltext = ' '.join(b[1] for b in blocks if b[0] in ('p', 'keywords') and isinstance(b[1], str)) \
         + ' ' + ' '.join(cellstxt(b) for b in blocks if b[0] == 'table')
inline = [
    (f"{m5f['pct_zero_weeks']}%", 'M5 zero-weeks'), (str(m5f['median_ADI']), 'M5 median ADI'),
    (f"{m5f['class_dist_pct']['Smooth']}%", 'M5 smooth%'), (f"{m5f['pct_intermittent_or_lumpy']:.0f}%", 'M5 int+lumpy%'),
    (f"{o2f['pct_zero_weeks']}%", 'OR2 zero-weeks'), (str(o2f['median_ADI']), 'OR2 median ADI'),
    (f"{o2f['class_dist_pct']['Lumpy']}%", 'OR2 lumpy%'), (f"{o2f['pct_smooth']}%", 'OR2 smooth%'),
    (f"{m5o.loc['LightGBM (global)','mean_MASE']:.3f}", 'M5 LightGBM mean MASE'),
    (f"{o2o.loc['LightGBM (global)','mean_MASE']:.3f}", 'OR2 LightGBM mean MASE'),
    (f"{o2o.loc['SES','mean_MASE']:.3f}", 'OR2 SES mean MASE'),
    (f"{o2i.loc['SBA','insample_PB_pct']:.1f}%", 'OR2 SBA in-sample PB'),
    (f"{o2i.loc['Naive','oos_PB_pct']:.1f}%", 'OR2 Naive OOS PB'),
    (f"{o2i.loc['SMA','oos_PB_pct']:.1f}%", 'OR2 SMA OOS PB'),
    # Section 5.2 quotes the in-sample champion and the out-of-sample win leader on BOTH
    # panels. Those sentences drifted once already when the ADIDA grid changed, because
    # nothing here checked them.
    (f"{m5i['insample_PB_pct'].max():.1f}%", 'M5 in-sample champion PB'),
    (f"{m5i.loc[m5i['insample_PB_pct'].idxmax(),'oos_PB_pct']:.1f}%", 'M5 in-sample champion OOS PB'),
    (f"{m5i['oos_PB_pct'].max():.1f}%", 'M5 OOS win leader PB'),
    (f"{m5o.loc['SES','mean_MASE']:.3f}", 'M5 SES mean MASE'),
    (f"{m5o.loc['TSB','mean_MASE']:.3f}", 'M5 TSB mean MASE'),
    (f"{o2o.loc['TSB','mean_MASE']:.3f}", 'OR2 TSB mean MASE'),
    (f"{m5o.loc['ADIDA','mean_MASE']:.3f}", 'M5 ADIDA mean MASE'),
    (f"{o2o.loc['Naive','mean_MASE']:.3f}", 'OR2 Naive mean MASE'),
    (f"{m5o.loc['LightGBM (global)','PB_pct']:.1f}%", 'M5 LightGBM PB'),
    (f"{o2o.loc['LightGBM (global)','PB_pct']:.1f}%", 'OR2 LightGBM PB'),
]
for needle, ctx in inline:
    checks += 1
    if needle not in fulltext:
        fails.append(f'INLINE {ctx}: "{needle}" not found anywhere in manuscript')

# ---------- Section 5.13's grid sensitivity, and the clustered critical distance ----------
# Both describe configurations the headline pipeline does not use, so neither leaves a trace
# in any other result file. These checks tie the prose to the artefacts that produced it.
_gs = js('grid_sensitivity.json')
for _ds, _meths in (('or2', ('SES', 'TSB', 'MAPA', 'SBA', 'Croston')),):
    for _m in _meths:
        _d = abs(_gs[_ds]['methods'][_m]['wide_minus_narrow'])
        checks += 1
        if f'{_d:.3f}' not in fulltext:
            fails.append(f'GRID {_ds} {_m}: wide-minus-narrow {_d:.3f} not stated in manuscript')
for _ds in ('m5', 'or2'):
    _h = _gs[_ds]['ses_high_alpha_diagnostic']
    for _v in (_h['share_above'], _h['mean_train_active_weeks_above'], _h['mean_train_active_weeks_below']):
        checks += 1
        if not any(f in fulltext for f in {str(_v), f'{float(_v):.1f}'}):
            fails.append(f'GRID {_ds}: high-alpha diagnostic value {_v} not stated in manuscript')
_cv = _gs['or2'].get('convergence_beyond_wide', {})
for _m, _d in _cv.items():
    checks += 1
    if f"{_d['movement']:.3f}" not in fulltext:
        fails.append(f"GRID convergence {_m}: movement {_d['movement']:.3f} not stated in manuscript")

_mc = js('mcb.json')
for _key, _lab in (('core6_product_clustered', 'nine-method'), ('all8_product_clustered', 'eleven-method')):
    _c = _mc['m5'][_key]
    checks += 1
    if f"{_c['critical_distance']:.3f}" not in fulltext:
        fails.append(f"MCB clustered M5 {_lab}: CD {_c['critical_distance']} not stated in manuscript")
checks += 1
if f"{_mc['m5']['core6_product_clustered']['N_clusters']:,}" not in fulltext:
    fails.append('MCB clustered M5: product count not stated in manuscript')

# ---------- Section 5.4's classification counterfactual ----------
# The full-span numbers quoted in Section 5.4 describe a labelling the pipeline no longer
# uses, so they appear in no other result file. 35_classification_sensitivity.py records
# them; these checks tie the prose to that artefact rather than to a claim.
_cs = js('classification_sensitivity.json')
for _ds, _cl in (('or2', 'Intermittent'), ('m5', 'Lumpy')):
    _v = _cs[_ds]['by_class_SES_mean_MASE'][_cl]
    for _k, _ctx in (('training_window', 'training-window'), ('full_span', 'full-span')):
        checks += 1
        if f"{_v[_k]['SES']:.3f}" not in fulltext:
            fails.append(f"CLASSIFY {_ds} {_cl} {_ctx} SES {_v[_k]['SES']:.3f} not stated in manuscript")
    checks += 1
    if f"{_cs[_ds]['pct_series_changing_class']:.1f}%" not in fulltext:
        fails.append(f"CLASSIFY {_ds}: {_cs[_ds]['pct_series_changing_class']:.1f}% class-change "
                     'share not stated in manuscript')
_mv = _cs['or2']['movers']
for _val, _ctx in ((_mv['moved_in_under_training_window']['n'], 'movers n'),
                   (_mv['moved_in_under_training_window']['mean_SES_MASE'], 'movers SES MASE'),
                   (_mv['moved_in_under_training_window']['mean_oos_weekly_demand'], 'movers OOS demand'),
                   (_mv['stayed']['mean_oos_weekly_demand'], 'stayers OOS demand')):
    checks += 1
    # prose rounds these to whatever precision reads naturally, so accept any of them
    _forms = {str(_val)} | {f'{float(_val):.{k}f}' for k in (0, 1, 2, 3)}
    if not any(f in fulltext for f in _forms):
        fails.append(f'CLASSIFY or2 {_ctx}: {_val} not stated in manuscript at any rounding')

# ---------- Week completeness: the panels must contain no partially covered week ----------
# Section 3 states that only weeks the sources cover end to end are kept. That claim leaves
# no trace in any results table, so it is asserted here directly against the M5 calendar.
_calpath = os.path.join(os.path.dirname(RES), 'data', 'm5', 'm5', 'datasets', 'calendar.csv')
if os.path.exists(_calpath):
    _cal = pd.read_csv(_calpath, usecols=['date', 'wm_yr_wk'])
    _dayn = _cal.groupby('wm_yr_wk').size()
    _complete = int((_dayn == 7).sum())
    checks += 1
    if js('m5_fingerprint.json')['n_weeks'] != _complete:
        fails.append(f"WEEKS M5: panel has {js('m5_fingerprint.json')['n_weeks']} weeks vs "
                     f'{_complete} complete seven-day weeks in the M5 calendar '
                     f'({int((_dayn < 7).sum())} partial week(s) present)')
    checks += 1
    if f'{int((_dayn < 7).sum())}' != '1':
        fails.append('WEEKS M5: expected exactly one partial calendar week; the Section 3 '
                     'wording assumes it')
# Online Retail II: the transaction span covers weeks 1..104 of the Monday grid end to end.
checks += 1
if js('or2_fingerprint.json')['n_weeks'] != 104:
    fails.append(f"WEEKS OR2: panel has {js('or2_fingerprint.json')['n_weeks']} weeks, expected 104 "
                 '(106 Monday-anchored buckets less the short first and last)')

# ---------- Tables 9-12: horizon, falsification, guidance, distribution ----------
# These four were outside the harness until Referee 4 pointed out that the drift it had
# caught in Table 11 could equally have gone unnoticed in any of them.

# Table 9: lead-time sensitivity vs <ds>_leadtime.csv
_meth9 = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'ADIDA', 'MAPA']
_lt = {d: csv(f'{d}_leadtime.csv').set_index('lead_weeks') for d in ('m5', 'or2')}
for r in tables['Table 9'][2]:
    lab = r[0]                                   # e.g. 'M5, L = 4'
    ds = 'm5' if lab.startswith('M5') else 'or2'
    L = int(lab.split('=')[1])
    row = _lt[ds].loc[L]
    for j, m in enumerate(_meth9):
        eq(r[j + 1], row[m], f'T9 {lab} {m}')
    checks += 1
    want = f"{int(row['Croston_rank'])} of {len(_meth9)}"
    if r[9] != want:
        fails.append(f'T9 {lab} Croston rank: manuscript={r[9]} vs result={want}')

# Table 10: zero-shot minus trained gaps vs gap_ci.json
_gap = js('gap_ci.json')
for r in tables['Table 10'][2]:
    lab = r[0]
    ds = 'm5' if lab.startswith('M5') else 'or2'
    cls = 'Intermittent' if 'Intermittent' in lab else 'Lumpy'
    g = _gap[ds][cls]
    checks += 1
    if f"{g['class_n']:,}" not in lab:
        fails.append(f"T10 {lab} n: manuscript label vs result={g['class_n']:,}")
    eq(r[2].rsplit(' ', 1)[1], g['best_trained']['mase'],  f'T10 {lab} best trained')
    eq(r[3].rsplit(' ', 1)[1], g['best_zeroshot']['mase'], f'T10 {lab} best zero-shot')
    sel = g['selected_min']
    eq(r[4], sel['gap'], f'T10 {lab} gap')
    lo, hi = sel['ci_bootstrap']
    for txt, val, side in ((r[5].split(' to ')[0], lo, 'lo'), (r[5].split(' to ')[1], hi, 'hi')):
        eq(txt.replace('+', ''), val, f'T10 {lab} CI {side}')

# Table 11: managerial guidance vs <ds>_managerial.csv
for r in tables['Table 11'][2]:
    lab = r[0]
    ds = 'm5' if lab.startswith('M5') else 'or2'
    cls = lab.split(', ')[1]
    d = csv(f'{ds}_managerial.csv').set_index('class').loc[cls]
    checks += 1
    if r[1] != f"{int(d['n']):,}":
        fails.append(f"T11 {lab} n: manuscript={r[1]} vs result={int(d['n']):,}")
    eq(r[2].rsplit(' ', 1)[1], d['mean_MASE'], f'T11 {lab} lowest mean MASE')
    eq(r[3].rstrip('%'), d['gain_over_simple_pct'], f'T11 {lab} gain over simple')
    eq(r[4].rsplit(' ', 1)[1].rstrip('%'), d['PB_pct'], f'T11 {lab} PB')
    for col, cell, ctx in ((d['best_by_mean_MASE'], r[2], 'best by MASE'),
                           (d['best_by_PercentageBest'], r[4], 'best by PB')):
        checks += 1
        if str(col) not in cell:
            fails.append(f'T11 {lab} {ctx}: manuscript={cell!r} vs result={col!r}')

# Table 12: distributional evaluation vs <ds>_prob_<model>.parquet
_prob = {'Empirical training quantile': 'empirical',
         'Chronos-Bolt-Small (zero-shot)': 'chronos_bolt_small',
         'Chronos-Bolt-Base (zero-shot)': 'chronos_bolt_base'}
_psum = js('or2_prob_summary.json')
for r in tables['Table 12'][2]:
    tag = _prob[r[0]]
    d = pd.read_parquet(os.path.join(RES, f'or2_prob_{tag}.parquet'))
    eq(r[1], np.nanmean(d[f'{tag}_pinball']), f'T12 {tag} scaled pinball')
    # coverage is quoted to one decimal, so compare at that precision rather than TOL
    eq(r[2].rstrip('%'), round(100 * np.nanmean(d[f'{tag}_cov90']), 1), f'T12 {tag} coverage')
    # the stored summary must agree with the parquet it was derived from
    eq(_psum[tag]['scaled_pinball'], np.nanmean(d[f'{tag}_pinball']), f'T12 {tag} summary vs parquet')
    eq(_psum[tag]['n'], int(d[f'{tag}_pinball'].notna().sum()), f'T12 {tag} summary n')
checks += 1
_n12 = len(pd.read_parquet(os.path.join(RES, 'or2_prob_empirical.parquet')))
if f'{_n12:,}' not in tables['Table 12'][1][0]:
    fails.append(f"T12 header n: {tables['Table 12'][1][0]!r} vs result={_n12:,}")

# The clamping claim carries a number in the prose; check it against the tail-check runs.
for _lab in ('chronos_bolt_small', 'chronos_bolt_base'):
    _tc = js(f'or2_tailcheck_{_lab}.json')
    checks += 1
    if _tc['share_q95_equals_q90'] != 1.0 or _tc['share_q99_equals_q90'] != 1.0:
        fails.append(f'TAILCHECK {_lab}: manuscript claims 100% clamping, result={_tc}')
    checks += 1
    if str(_tc['n_sampled']) not in fulltext:
        fails.append(f"TAILCHECK {_lab}: sample size {_tc['n_sampled']} not stated in manuscript")

# The leak counterfactual quoted in 5.7 must come from the shipped leaked-run artefacts.
_impL = csv('or2_lgbm_importance_leaked.csv')
_shareL = 100 * _impL[_impL.feature.isin(['price', 'price_ratio'])].gain.sum() / _impL.gain.sum()
checks += 1
if f'{_shareL:.0f}%' not in fulltext:
    fails.append(f'LEAK: price share {_shareL:.0f}% not found in manuscript')
_cl = pd.read_parquet(os.path.join(RES, 'or2_classical.parquet'))
_el = _cl[np.isfinite(_cl['scale']) & (_cl['scale'] > 0) & (_cl['train_nnz'] >= 2)][['unique_id']]
_mL = pd.read_parquet(os.path.join(RES, 'or2_lgbm_leaked.parquet')).merge(_el, on='unique_id')
checks += 1
if f'{np.nanmean(_mL.lgbm_mase):.3f}' not in fulltext:
    fails.append(f'LEAK: leaked mean MASE {np.nanmean(_mL.lgbm_mase):.3f} not found in manuscript')

print(f'LAYER 1 (manuscript <-> results consistency): {checks} checks')
if fails:
    print(f'  !! {len(fails)} MISMATCH(es):')
    for f in fails: print('   -', f)
    sys.exit(1)
print('  ALL CONSISTENT (every manuscript table value + key inline claims match the result files).')
