"""
33_prose_scan.py -- catch numbers that live only in the prose.

repro_backtest.py verifies every table cell and a curated list of inline claims. The gap
it cannot close is a number written into a sentence and never entered in a table: when the
ADIDA grid changed, Section 5.2's in-sample Percentage-Best figures went stale and nothing
noticed, because no table carried them.

This scans every prose paragraph for decimal numbers and reports any that appear in no
result file at any of three roundings. It is a lint, not a proof: a match only says the
value exists somewhere in results/, not that it was used correctly. Treat each hit as a
question to answer rather than a failure, and add genuine constants to ALLOW.

  python 33_prose_scan.py            report
  python 33_prose_scan.py --strict   exit 1 if anything unexplained is found
"""
import os, re, sys, json
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')
sys.path.insert(0, HERE)
import manuscript_content as MC

# Values that are definitionally not results: published constants, section numbers, and
# figures computed in the text from the panels rather than stored in a result file.
ALLOW = {
    '1.32': 'SBC average-inter-demand-interval cut-off (Syntetos, Boylan & Croston 2005)',
    '0.49': 'SBC squared-coefficient-of-variation cut-off',
    '3.195': 'M5 truncated-week panel mean, Section 3 (computed from data/m5_weekly.parquet)',
    '10.413': 'M5 panel mean for the week before it, Section 3',
    '0.161': 'M5 TSB-minus-Croston mean MASE difference, Section 5.2',
    '0.268': 'OR2 TSB-minus-Croston mean MASE difference, Section 5.2',
    '0.025': 'M5 mean-MASE shift from the truncated week, Section 3 (measured, not stored)',
    '0.005': 'largest Chronos-vs-TimesFM per-class difference on M5, Section 5.9 (derived)',
    '0.190': 'leaked-minus-corrected OR2 LightGBM mean MASE, 0.868 - 0.678, Section 6.1 (derived)',
    '1.96': 'normal quantile for a 95% interval',
    '5.11': 'section cross-reference',
    '5.12': 'section cross-reference',
    '5.13': 'section cross-reference',
}


def pool():
    """Every numeric value in results/, at three roundings."""
    out = set()

    def add(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return
        for k in (2, 3):
            out.add(f'{v:.{k}f}')
            out.add(f'{abs(v):.{k}f}')   # prose quotes the magnitude of signed differences

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)):
            add(o)

    for f in os.listdir(RES):
        p = os.path.join(RES, f)
        if not os.path.isfile(p):
            continue
        try:
            if f.endswith('.csv'):
                d = pd.read_csv(p)
                for c in d.columns:
                    for v in pd.to_numeric(d[c], errors='coerce').dropna():
                        add(v)
            elif f.endswith('.json'):
                walk(json.load(open(p)))
        except Exception:
            continue
    return out


def main():
    known = pool()
    sec = '(front matter)'
    hits = []
    for b in MC.blocks():
        if b[0] in ('h1', 'h2'):
            sec = b[1]
        text = None
        if b[0] == 'p' and isinstance(b[1], str):
            text = b[1]
        elif b[0] == 'table' and b[4]:
            text = b[4]                      # captions carry claims too
        elif b[0] == 'figure' and len(b) > 2:
            text = b[2]                      # and so do figure captions
        elif b[0] == 'bullet' and isinstance(b[1], str):
            text = b[1]                      # highlights bullets restate headline numbers
        if not text:
            continue
        for m in re.finditer(r'\b\d+\.\d{2,3}\b', text):
            v = m.group()
            if v in ALLOW:
                continue
            # compare at the precision the sentence actually writes: rounding a
            # three-decimal claim down to one decimal makes the check meaningless,
            # because some value in results/ matches almost any single decimal.
            dp = len(v.split('.')[1])
            if f'{float(v):.{dp}f}' in known:
                continue
            hits.append((sec, v, text[max(0, m.start() - 60):m.start() + 20]))

    if not hits:
        print(f'prose scan: no unexplained decimals ({len(known):,} values indexed from results/).')
        return 0
    print(f'prose scan: {len(hits)} decimal(s) in prose with no match in results/:\n')
    for s, v, c in hits:
        print(f'  [{s[:38]:38s}] {v:>9s}  ...{c.strip()}')
    print('\nEach is either a stale number, a value computed in the text, or a constant.\n'
          'Resolve it or add it to ALLOW with a reason.')
    return 1 if '--strict' in sys.argv else 0


if __name__ == '__main__':
    sys.exit(main())
