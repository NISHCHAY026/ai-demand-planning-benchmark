"""
34_refresh_class_labels.py -- re-stamp the SBC class column on stored model results.

02_classify.py now classifies on the training window only. The per-series forecast files
written by the neural and foundation runs carry a `class` column that was merged in at
write time, so after a re-classification they hold the previous labels. The forecasts
themselves are unaffected (no model uses the class), which is why re-running hours of
inference to update a label column would be waste rather than rigour.

This re-merges the current label from <ds>_classical.parquet into those files and rebuilds
the by-class blocks of the neural summaries from the stored per-series errors. The
analysis scripts (26, 27, 29) already read class from classical.parquet and so were never
affected; this exists so the stored files and the summaries agree with them.

  python 34_refresh_class_labels.py
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')

TARGETS = ['{ds}_neural.parquet', '{ds}_foundation.parquet', '{ds}_timesfm.parquet']
CLASSES = ['Smooth', 'Intermittent', 'Erratic', 'Lumpy']


def main():
    for ds in ('m5', 'or2'):
        cur = pd.read_parquet(os.path.join(RES, f'{ds}_classical.parquet'))[['unique_id', 'class']]
        lut = dict(zip(cur['unique_id'], cur['class']))
        for pat in TARGETS:
            p = os.path.join(RES, pat.format(ds=ds))
            if not os.path.exists(p):
                continue
            d = pd.read_parquet(p)
            if 'class' not in d.columns:
                print(f'  {os.path.basename(p):34s} no class column, skipped'); continue
            new = d['unique_id'].map(lut)
            moved = int((new.fillna('') != d['class'].fillna('')).sum())
            d['class'] = new
            d.to_parquet(p, index=False)
            print(f'  {os.path.basename(p):34s} {moved:,} label(s) updated')

        # rebuild the by-class block of the neural summary from stored per-series errors
        sp = os.path.join(RES, f'{ds}_neural_summary.json')
        np_p = os.path.join(RES, f'{ds}_neural.parquet')
        if os.path.exists(sp) and os.path.exists(np_p):
            per = pd.read_parquet(np_p)
            summ = json.load(open(sp))
            summ['by_class'] = {}
            for cl in CLASSES:
                # count only series that carry a forecast: the mean is taken over those,
                # so reporting the full class membership beside it would misdescribe it
                sub = per[(per['class'] == cl) & per['nhits_mase'].notna()]
                if len(sub):
                    summ['by_class'][cl] = {
                        'n': int(len(sub)),
                        'NHITS': round(float(np.nanmean(sub['nhits_mase'])), 3),
                        'DeepAR': round(float(np.nanmean(sub['deepar_mase'])), 3)}
            summ['class_source'] = 'training-window classification (02_classify.py)'
            json.dump(summ, open(sp, 'w'), indent=2)
            print(f'  {ds}_neural_summary.json by_class rebuilt: '
                  + ', '.join(f"{c} n={summ['by_class'][c]['n']:,}" for c in summ['by_class']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
