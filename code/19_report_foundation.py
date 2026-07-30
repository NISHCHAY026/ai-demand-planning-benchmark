"""
19_report_foundation.py  -- format the REAL benchmark outputs into markdown tables for
the manuscript. Reads results/<ds>_foundation_summary.json (which already contains the
unified all-methods comparison on the identical neural-eligible series, overall and by
regime). Prints to stdout AND writes results/foundation_tables.md. No numbers are typed
by hand here; everything is read from the saved result files.
"""
import os, json

RES = r'D:\Research Pack\AI_Demand_Planning_Paper\results'
DATASETS = ['m5', 'or2']
DSNAME = {'m5': 'M5 (Walmart)', 'or2': 'Online Retail II'}
# display order; foundation models appended dynamically
ORDER = ['Naive', 'SMA', 'SES', 'Croston', 'SBA', 'LightGBM', 'NHITS', 'DeepAR']
PRETTY = {'chronos_bolt_small': 'Chronos-Bolt-Small (48M)',
          'chronos_bolt_base': 'Chronos-Bolt-Base (205M)',
          'timesfm_200m': 'TimesFM-200M'}


def load(ds):
    p = os.path.join(RES, f'{ds}_foundation_summary.json')
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def fmt(x):
    return f'{x:.3f}' if isinstance(x, (int, float)) else str(x)


def main():
    out = []
    summ = {ds: load(ds) for ds in DATASETS}
    avail = {ds: s for ds, s in summ.items() if s}
    if not avail:
        print('no foundation summaries found yet'); return

    # collect foundation model labels actually present
    fm_labels = []
    for s in avail.values():
        for m in s.get('models', []):
            if m not in fm_labels:
                fm_labels.append(m)
    methods = ORDER + [m for m in fm_labels]

    out.append('## Overall accuracy: mean (median) MASE, identical neural-eligible series\n')
    hdr = '| Method | ' + ' | '.join(
        f'{DSNAME[ds]}  (n={avail[ds]["subset_n_all_methods"]})' for ds in DATASETS if ds in avail) + ' |'
    out.append(hdr)
    out.append('|' + '---|' * (1 + len([d for d in DATASETS if d in avail])))
    for m in methods:
        label = PRETTY.get(m, m)
        cells = []
        for ds in DATASETS:
            if ds not in avail:
                continue
            comp = avail[ds]['subset_comparison_mean_median']
            if m in comp:
                mean, med = comp[m]
                cells.append(f'{mean:.3f} ({med:.3f})')
            else:
                cells.append('—')
        out.append(f'| {label} | ' + ' | '.join(cells) + ' |')

    out.append('\n## Mean MASE by demand regime\n')
    for ds in DATASETS:
        if ds not in avail:
            continue
        s = avail[ds]
        bc = s['by_class']
        regimes = [r for r in ['Smooth', 'Erratic', 'Intermittent', 'Lumpy'] if r in bc]
        out.append(f'\n**{DSNAME[ds]}**  (regime n in header)\n')
        out.append('| Method | ' + ' | '.join(f'{r} (n={bc[r]["n"]})' for r in regimes) + ' |')
        out.append('|' + '---|' * (1 + len(regimes)))
        for m in methods:
            label = PRETTY.get(m, m)
            cells = []
            for r in regimes:
                v = bc[r].get(m)
                cells.append(f'{v:.3f}' if v is not None else '—')
            out.append(f'| {label} | ' + ' | '.join(cells) + ' |')

    text = '\n'.join(out)
    print(text)
    with open(os.path.join(RES, 'foundation_tables.md'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    print('\n[written results/foundation_tables.md]')


if __name__ == '__main__':
    main()
