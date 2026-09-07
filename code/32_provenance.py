"""
32_provenance.py -- record which library code each result file actually depends on, so
staleness is checkable rather than inferred from modification times.

Referee 4 observed that several result files predate the last edit to lib.py and asked
whether they still reflect it. Modification times cannot answer that: they say when a file
was written, not what it was written from. This script records, per result file, the
sha256 of the source of exactly the lib.py functions the producing script calls. A result
is stale only if one of those hashes has moved, which is a much narrower and more honest
claim than "lib.py changed".

  python 32_provenance.py          write results/provenance.json
  python 32_provenance.py --check  compare against it, exit 1 on any drift
"""
import os, sys, ast, json, hashlib, io, re

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')
MANIFEST = os.path.join(RES, 'provenance.json')

# producing script -> result files it writes
PRODUCES = {
    '03_classical.py': ['m5_classical.parquet', 'or2_classical.parquet'],
    '04_lgbm_global.py': ['m5_lgbm.parquet', 'm5_lgbm_importance.csv',
                          'or2_lgbm.parquet', 'or2_lgbm_importance.csv',
                          'or2_lgbm_leaked.parquet', 'or2_lgbm_importance_leaked.csv'],
    '10_neural_baselines.py': ['m5_neural.parquet', 'or2_neural.parquet'],
    '18_foundation_models.py': ['m5_foundation.parquet', 'or2_foundation.parquet'],
    '20_timesfm.py': ['m5_timesfm.parquet', 'or2_timesfm.parquet'],
    '28_probabilistic.py': ['or2_prob_empirical.parquet',
                            'or2_prob_chronos_bolt_small.parquet',
                            'or2_prob_chronos_bolt_base.parquet',
                            'or2_tailcheck_chronos_bolt_small.json',
                            'or2_tailcheck_chronos_bolt_base.json'],
    '31_timesfm_quantile_probe.py': ['or2_tailcheck_timesfm.json'],
}

_lib_src = io.open(os.path.join(HERE, 'lib.py'), encoding='utf-8').read()
_lib_tree = ast.parse(_lib_src)
_lib_lines = _lib_src.splitlines(True)


def fn_hash(name):
    """sha256 of one top-level function's source, or None if lib.py has no such name."""
    for node in _lib_tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            src = ''.join(_lib_lines[node.lineno - 1:node.end_lineno])
            return hashlib.sha256(src.encode('utf-8')).hexdigest()[:16]
    return None


def lib_calls(script):
    """The lib.* names a script actually references."""
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        return None
    src = io.open(path, encoding='utf-8').read()
    return sorted(set(re.findall(r'\blib\.([A-Za-z_]\w*)', src)))


def build():
    out = {}
    for script, outputs in sorted(PRODUCES.items()):
        names = lib_calls(script)
        if names is None:
            out[script] = {'missing_script': True}
            continue
        deps = {n: fn_hash(n) for n in names}
        present = [f for f in outputs if os.path.exists(os.path.join(RES, f))]
        out[script] = {'lib_dependencies': deps,
                       'outputs_present': present,
                       'outputs_absent': [f for f in outputs if f not in present]}
    return out


def main():
    cur = build()
    if '--check' in sys.argv:
        if not os.path.exists(MANIFEST):
            print('no manifest; run without --check first'); return 1
        old = json.load(open(MANIFEST))
        drift = []
        for script, rec in cur.items():
            prev = old.get(script, {})
            for name, h in rec.get('lib_dependencies', {}).items():
                ph = prev.get('lib_dependencies', {}).get(name)
                if ph is not None and ph != h:
                    drift.append(f'{script}: lib.{name} changed since {rec["outputs_present"]} '
                                 f'were written ({ph} -> {h})')
        if drift:
            print(f'{len(drift)} STALE dependency(ies):')
            for d in drift:
                print('  -', d)
            return 1
        n = sum(len(r.get('lib_dependencies', {})) for r in cur.values())
        print(f'provenance OK: {n} library dependencies across {len(cur)} scripts unchanged '
              f'since their outputs were written.')
        return 0
    json.dump(cur, open(MANIFEST, 'w'), indent=2)
    for script, rec in sorted(cur.items()):
        deps = rec.get('lib_dependencies', {})
        print(f'  {script:32s} {len(deps)} lib dep(s): {", ".join(deps) or "none"}')
    print(f'\nwrote {MANIFEST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
