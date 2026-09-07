"""
30_sync_tables.py -- rewrite the hard-coded table bodies in manuscript_content.py from
the current result files.

Why this exists: the manuscript tables were typed by hand, so any re-run of the analysis
silently desynchronised them from results/. repro_backtest.py catches the drift but the
repair was manual and error-prone, and one table (Table 11) had drifted in every cell.
This script makes the numbers a build product rather than a transcription.

It rewrites ONLY the row payload of each table it knows about, leaving headers, column
widths and captions untouched. Run it after any analysis re-run, then run
repro_backtest.py, which should then report zero mismatches.
"""
import os, re, io, json
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')
SRC = os.path.join(HERE, 'manuscript_content.py')

csv = lambda n: pd.read_csv(os.path.join(RES, n))
js = lambda n: json.load(open(os.path.join(RES, n)))
f3 = lambda v: f'{float(v):.3f}'
f1 = lambda v: f'{float(v):.1f}'

CORE = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'ADIDA', 'MAPA', 'LightGBM (global)']
CLASSICAL = CORE[:-1]


def rows_table1(existing):
    """Numeric cells come from the two fingerprint JSONs; the descriptive rows (source,
    domain, exogenous features) are editorial and carried over unchanged."""
    m, o = js('m5_fingerprint.json'), js('or2_fingerprint.json')
    yrs = {r[0]: re.search(r'\((\d{4}.\d{4})\)', r[1] + r[2]) for r in existing if 'Window' in r[0]}
    keep = {r[0]: r for r in existing}
    out = []
    for r in existing:
        k = r[0]
        if 'Series' in k:
            out.append([k, f"{m['n_series']:,}", f"{o['n_series']:,}"])
        elif 'Window' in k:
            span = lambda cell: re.search(r'\(.*\)', cell).group(0)
            out.append([k, f"{m['n_weeks']} weeks {span(keep[k][1])}",
                           f"{o['n_weeks']} weeks {span(keep[k][2])}"])
        elif 'Panel observations' in k:
            out.append([k, f"{m['panel_cells']/1e6:.2f} million",
                           f"{o['panel_cells']/1e6:.2f} million"])
        elif 'Zero-demand' in k:
            out.append([k, f"{m['pct_zero_weeks']}%", f"{o['pct_zero_weeks']}%"])
        elif 'Median ADI' in k:
            out.append([k, f"{m['median_ADI']} / {m['median_CV2']}",
                           f"{o['median_ADI']} / {o['median_CV2']}"])
        elif 'Dominant' in k:
            dm = max(m['class_dist_pct'], key=m['class_dist_pct'].get)
            do = max(o['class_dist_pct'], key=o['class_dist_pct'].get)
            out.append([k, f"{dm} ({m['class_dist_pct'][dm]}%)",
                           f"{do} ({o['class_dist_pct'][do]}%)"])
        else:
            out.append(list(r))
    return out


def rows_table2():
    m, o = csv('m5_inversion.csv').set_index('method'), csv('or2_inversion.csv').set_index('method')
    return [[k, f1(m.loc[k, 'insample_PB_pct']), f3(m.loc[k, 'oos_mean_MASE']),
             f1(m.loc[k, 'oos_PB_pct']), f1(o.loc[k, 'insample_PB_pct']),
             f3(o.loc[k, 'oos_mean_MASE']), f1(o.loc[k, 'oos_PB_pct'])] for k in CLASSICAL]


def rows_table3():
    m, o = csv('m5_overall.csv').set_index('method'), csv('or2_overall.csv').set_index('method')
    return [[k, f3(m.loc[k, 'mean_MASE']), f3(m.loc[k, 'median_MASE']), f1(m.loc[k, 'PB_pct']),
             f3(o.loc[k, 'mean_MASE']), f3(o.loc[k, 'median_MASE']), f1(o.loc[k, 'PB_pct'])]
            for k in CORE]


def rows_table4():
    m, o = csv('m5_by_class.csv').set_index('class'), csv('or2_by_class.csv').set_index('class')
    cls = ['Smooth', 'Intermittent', 'Erratic', 'Lumpy']
    return [[c] + [f3(m.loc[c, k]) for k in ('SES', 'SBA', 'TSB', 'LightGBM (global)')]
                + [f3(o.loc[c, k]) for k in ('SES', 'SBA', 'TSB', 'LightGBM (global)')]
            for c in cls]


def rows_table5():
    """Hold-out-horizon sweep, straight from the two robustness CSVs."""
    meth = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'MAPA', 'LightGBM']
    out = []
    for ds, lab in (('m5', 'M5'), ('or2', 'OR2')):
        d = csv(f'{ds}_robustness.csv')
        for _, r in d.iterrows():
            out.append([f"{lab} {int(r['test_weeks'])} wk"] + [f3(r[k]) for k in meth])
    return out


def rows_table7():
    j = js('mcb.json')
    return [[k, f3(j['m5']['core6_fullset']['mean_ranks'][k]),
                f3(j['or2']['core6_fullset']['mean_ranks'][k])] for k in CORE]


def rows_table8():
    j = js('rmsse.json')
    return [[k, f3(j['m5']['core6_fullset']['mean_RMSSE'][k]),
                f3(j['m5']['core6_fullset']['mcb']['mean_ranks'][k]),
                f3(j['or2']['core6_fullset']['mean_RMSSE'][k]),
                f3(j['or2']['core6_fullset']['mcb']['mean_ranks'][k])] for k in CORE]


def rows_table9():
    want = {'m5': [1, 4, 13, 26], 'or2': [1, 4, 7]}
    meth = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'ADIDA', 'MAPA']
    out = []
    for ds, lab in (('m5', 'M5'), ('or2', 'OR2')):
        d = csv(f'{ds}_leadtime.csv').set_index('lead_weeks')
        for L in want[ds]:
            r = d.loc[L]
            out.append([f'{lab}, L = {L}'] + [f3(r[k]) for k in meth]
                       + [f"{int(r['Croston_rank'])} of {len(meth)}"])
    return out


def rows_table10():
    """Falsification test: every cell comes from gap_ci.json, including the simple-method
    column, so no part of Table 10 is transcribed by hand."""
    j = js('gap_ci.json')
    short = {'Chronos-Bolt-Small': 'Chronos-Bolt-S', 'Chronos-Bolt-Base': 'Chronos-Bolt-B'}
    out = []
    for ds, lab in (('m5', 'M5'), ('or2', 'OR2')):
        for cl in ('Intermittent', 'Lumpy'):
            g = j[ds][cl]
            s = g['selected_min']
            lo, hi = s['ci_bootstrap']
            nm = lambda d: f"{short.get(d['method'], d['method'])} {f3(d['mase'])}"
            out.append([f"{lab}, {cl} (n = {g['class_n']:,})",
                        nm(g['best_simple']), nm(g['best_trained']), nm(g['best_zeroshot']),
                        f"{s['gap']:+.3f}", f"{lo:+.3f} to {hi:+.3f}"])
    return out


def rows_table12(existing):
    """Distributional evaluation; the final column states what each method can express and
    is editorial, so it is carried over."""
    tag = {'Empirical training quantile': 'empirical',
           'Chronos-Bolt-Small (zero-shot)': 'chronos_bolt_small',
           'Chronos-Bolt-Base (zero-shot)': 'chronos_bolt_base'}
    s = js('or2_prob_summary.json')
    return [[r[0], f3(s[tag[r[0]]]['scaled_pinball']),
             f"{s[tag[r[0]]]['coverage_90']:.1f}%", r[3]] for r in existing]


def rows_table11(existing):
    """Numeric cells come from the managerial CSVs; the guidance column is editorial
    prose written in the manuscript, so it is carried over from the existing rows."""
    guide = {r[0]: r[5] for r in existing} if existing else {}
    out = []
    for ds, lab in (('m5', 'M5'), ('or2', 'OR2')):
        d = csv(f'{ds}_managerial.csv')
        for _, r in d.iterrows():
            key = f"{lab}, {r['class']}"
            out.append([key, f"{int(r['n']):,}",
                        f"{r['best_by_mean_MASE']} {f3(r['mean_MASE'])}",
                        f"{f1(r['gain_over_simple_pct'])}%",
                        f"{r['best_by_PercentageBest']} {f1(r['PB_pct'])}%",
                        guide.get(key, '')])
    return out


def fmt(rows, indent=9):
    pad = ' ' * indent
    lines = ['[' + repr(rows[0]).replace('"', "'")]
    for r in rows[1:]:
        lines.append(pad + repr(r).replace('"', "'"))
    return ',\n'.join(lines) + ']'


TABLES = [('Table 1', rows_table1), ('Table 2', rows_table2), ('Table 3', rows_table3), ('Table 4', rows_table4), ('Table 5', rows_table5),
          ('Table 7', rows_table7), ('Table 8', rows_table8), ('Table 9', rows_table9),
          ('Table 10', rows_table10), ('Table 11', rows_table11),
          ('Table 12', rows_table12)]

text = io.open(SRC, encoding='utf-8').read()
changed = 0
for name, fn in TABLES:
    cap = text.find(f"'{name}. ")
    if cap < 0:
        print(f'  {name}: caption not found, skipped'); continue
    blk = text.rfind("A(('table'", 0, cap)
    hdr_end = text.find('],', blk)                      # end of the header list
    rows_start = text.find('[[', hdr_end)
    rows_end = text.find(']],', rows_start) + 2
    if not (blk < hdr_end < rows_start < rows_end):
        print(f'  {name}: could not bracket rows, skipped'); continue
    import ast
    existing = ast.literal_eval(text[rows_start:rows_end])
    new = fmt(fn(existing) if name in ('Table 1', 'Table 11', 'Table 12') else fn())
    if text[rows_start:rows_end] == new:
        print(f'  {name}: already in sync'); continue
    text = text[:rows_start] + new + text[rows_end:]
    changed += 1
    print(f'  {name}: rewritten from results')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print(f'\n{changed} table(s) rewritten. Now run repro_backtest.py.')
