"""
17_build_submission.py -- build the double-blind IJF submission set from the shared
content: an ANONYMIZED manuscript (no author identity) and a separate TITLE PAGE
(author, affiliation, abstract, declarations), each in .docx/.pdf/.tex/.md.
Reuses the four renderers (loaded by path, since their filenames start with digits).
"""
import os, importlib.util
import manuscript_content as MC

CODE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code')
OUT  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript')

def load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(CODE, fname))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

R_docx = load('08_build_manuscript.py', 'm08').render_docx
R_pdf  = load('11_build_pdf.py',        'm11').render
R_tex  = load('13_build_latex.py',      'm13').render
R_md   = load('14_build_markdown.py',   'm14').render

anon = MC.blocks(anonymous=True)
tp   = MC.titlepage_blocks()
A = os.path.join(OUT, 'AI_demand_planning_OOS_benchmark_anonymized')
T = os.path.join(OUT, 'AI_demand_planning_OOS_benchmark_title_page')

print('--- anonymized manuscript ---')
R_docx(anon, A + '.docx')
R_pdf(anon,  A + '.pdf', 'AI in supply-chain demand planning (anonymized)')
R_tex(anon,  A + '.tex')
R_md(anon,   A + '.md')

print('--- title page ---')
R_docx(tp, T + '.docx')
R_pdf(tp,  T + '.pdf', 'Title page')
R_tex(tp,  T + '.tex')
R_md(tp,   T + '.md')

# sanity: anonymized files must NOT contain the author name
import glob
bad = []
for f in glob.glob(A + '.md') + glob.glob(A + '.tex'):
    if 'Nishchay' in open(f, encoding='utf-8').read():
        bad.append(f)
print('\nAnonymization check — files still containing author name:', bad if bad else 'NONE (clean)')
print('Done.')
