"""
25_build_deposits.py -- assemble ready-to-paste deposit packages for Zenodo and SSRN.

Both take the title, abstract and keywords straight from manuscript_content, so the
deposit metadata cannot drift away from the paper. Neither service is scriptable
without credentials, so this produces the files and the field-by-field values to
paste, not an upload.

Writes manuscript/deposit/
"""
import os, json, re, shutil
import manuscript_content as MC

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAN = os.path.join(ROOT, 'manuscript')
OUT = os.path.join(MAN, 'deposit')
os.makedirs(OUT, exist_ok=True)

REPO = 'https://github.com/NISHCHAY026/ai-demand-planning-benchmark'
AUTHOR = 'Patel, Nishchay'
AFFIL = 'Independent Researcher'

def plain(s):
    """Web deposit forms mangle smart punctuation. Fold it to ASCII for metadata
    fields only; the typeset PDF keeps the proper glyphs."""
    return (s.replace('’', "'").replace('‘', "'")
             .replace('“', '"').replace('”', '"')
             .replace('–', '-').replace('—', ', ')
             .replace(' ', ' '))

blocks = MC.blocks()
title = next(b[1] for b in blocks if b[0] == 'title')
i = next(n for n, b in enumerate(blocks) if b[0] == 'h_abstract')
abstract = plain(re.sub(r'\s+', ' ', blocks[i + 1][1]).strip())
kw_raw = next(b[1] for b in blocks if b[0] == 'keywords')
keywords = [plain(k).strip(' .;') for k in kw_raw.replace('Keywords:', '').split(';') if k.strip(' .;')]
disclosure = plain(next(b[1] for b in blocks if b[0] == 'p' and 'Claude (Anthropic)' in b[1]))

# ---------------------------------------------------------------- Zenodo
zenodo = {
    'upload_type': 'publication',
    'publication_type': 'preprint',
    'title': title,
    'creators': [{'name': AUTHOR, 'affiliation': AFFIL}],
    'description': abstract,
    'keywords': keywords,
    'license': 'cc-by-4.0',
    'access_right': 'open',
    'language': 'eng',
    'related_identifiers': [
        {'identifier': REPO, 'relation': 'isSupplementedBy', 'resource_type': 'software'},
        {'identifier': 'https://doi.org/10.1016/j.ijforecast.2021.11.013',
         'relation': 'references', 'resource_type': 'publication-article'},
    ],
    'notes': disclosure,
}
with open(os.path.join(OUT, 'zenodo_metadata.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(zenodo, f, indent=2, ensure_ascii=False)

# .zenodo.json controls how the GitHub code archive is described when a release is cut
code_meta = {
    'upload_type': 'software',
    'title': 'ai-demand-planning-benchmark: reproducible out-of-sample benchmark of classical, '
             'gradient-boosted and deep forecasters on M5 and UCI Online Retail II',
    'creators': [{'name': AUTHOR, 'affiliation': AFFIL}],
    'description': 'Analysis pipeline and result tables for the study. Builds the weekly panels, '
                   'classifies demand by the SBC scheme, fits Naive, moving-average, exponential-smoothing, '
                   'Croston and Syntetos-Boylan forecasters, a global LightGBM model and the NHITS and '
                   'DeepAR deep global models, runs the rolling-origin evaluation, and produces every '
                   'result table and figure.',
    'license': 'MIT',
    'access_right': 'open',
    'keywords': keywords,
}
with open(os.path.join(OUT, 'dot_zenodo.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(code_meta, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- SSRN
# SSRN asks that any AI disclosure appear WITH the abstract, not only inside the PDF.
ssrn_abstract = abstract + '\n\nDeclaration of generative AI: ' + disclosure

JEL = [('C53', 'Forecasting and Prediction Methods; Simulation Modeling'),
       ('C45', 'Neural Networks and Related Topics'),
       ('C55', 'Large Data Sets: Modeling and Analysis'),
       ('L81', 'Retail and Wholesale Trade; e-Commerce'),
       ('M11', 'Production Management')]

lines = []
A = lines.append
A('SSRN SUBMISSION SHEET')
A('=' * 72)
A('')
A('Paste each field below into the SSRN submission form.')
A('')
A('--- TITLE ---------------------------------------------------------------')
A(title)
A('')
A('--- AUTHOR --------------------------------------------------------------')
A(f'{AUTHOR}   |   Affiliation: {AFFIL}')
A('SSRN requires the PDF itself to display the title and every author with')
A('affiliation. The compiled PDF does; do not upload the anonymized variant.')
A('')
A('--- DATE WRITTEN --------------------------------------------------------')
A('[ use the date you submit ]')
A('')
A(f'--- ABSTRACT ({len(ssrn_abstract)} chars, includes the required AI disclosure) ---')
A(ssrn_abstract)
A('')
A('--- KEYWORDS ------------------------------------------------------------')
A('; '.join(keywords))
A('')
A('--- JEL CODES (optional; does not affect distribution) -------------------')
for c, d in JEL:
    A(f'  {c}  {d}')
A('')
A('--- eJOURNALS (choose up to 7) ------------------------------------------')
A('Search the SSRN network list for these topics rather than trusting exact')
A('titles here, since SSRN renames journals periodically:')
for t in ['Operations Research', 'Supply Chain Management', 'Operations Management',
          'Applied Econometrics', 'Machine Learning', 'Decision Sciences',
          'Retailing / e-Commerce']:
    A(f'  - {t}')
A('')
A('--- FILE ----------------------------------------------------------------')
A('manuscript/arxiv/AI_demand_planning_OOS_benchmark.pdf  (19 pp, 1.76 MB)')
A('')
A('--- NOTE ----------------------------------------------------------------')
A('Posting here makes the paper public under your name. That is fine for a')
A('preprint and does not block a later arXiv submission, but it does defeat')
A('double-blind review at any venue that runs it.')
with open(os.path.join(OUT, 'SSRN_submission.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

# ---------------------------------------------------------------- shared PDF
pdf_src = os.path.join(MAN, 'arxiv', 'AI_demand_planning_OOS_benchmark.pdf')
if os.path.exists(pdf_src):
    shutil.copy2(pdf_src, os.path.join(OUT, 'AI_demand_planning_OOS_benchmark.pdf'))

print('wrote', OUT)
for f in sorted(os.listdir(OUT)):
    print(f'   {f}  ({os.path.getsize(os.path.join(OUT, f)):,} bytes)')
print()
print(f'  abstract          : {len(abstract)} chars')
print(f'  SSRN abstract     : {len(ssrn_abstract)} chars (with disclosure)')
print(f'  keywords          : {len(keywords)}')
print(f'  em dashes in meta : {sum(t.count(chr(0x2014)) for t in [title, abstract, ssrn_abstract])}')
