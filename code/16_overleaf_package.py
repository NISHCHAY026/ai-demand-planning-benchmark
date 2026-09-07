"""
16_overleaf_package.py -- assemble a self-contained Overleaf bundle with a LOCAL
figures/ folder (no '../'), including the authored manuscript, the double-blind
anonymized manuscript and the title page. Zipped for one-drag upload.
"""
import os, shutil, zipfile

MAN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript')
FIGSRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'figures')
OV = os.path.join(MAN, 'overleaf')
if os.path.exists(OV): shutil.rmtree(OV)
os.makedirs(os.path.join(OV, 'figures'))

TEX_FILES = [
    'AI_demand_planning_OOS_benchmark.tex',             # authored version, for your own records
    'AI_demand_planning_OOS_benchmark_anonymized.tex',  # IJF submission: main file
    'AI_demand_planning_OOS_benchmark_title_page.tex',  # IJF submission: title page
]
for fn in TEX_FILES:
    src = os.path.join(MAN, fn)
    if not os.path.exists(src):
        print('skip (missing):', fn); continue
    txt = open(src, encoding='utf-8').read().replace(
        r'\graphicspath{{../results/figures/}}', r'\graphicspath{{figures/}}')
    open(os.path.join(OV, fn), 'w', encoding='utf-8').write(txt)

figs = [f for f in os.listdir(FIGSRC) if f.endswith('.png')]
for f in figs:
    shutil.copy(os.path.join(FIGSRC, f), os.path.join(OV, 'figures', f))

README = """OVERLEAF BUNDLE  --  AI in supply-chain demand planning
=========================================================
In Overleaf: New Project -> Upload Project -> select overleaf_submission.zip
Set Compiler to pdfLaTeX (Menu -> Compiler), choose the main document, then Recompile.

FILES
  AI_demand_planning_OOS_benchmark.tex            Full authored paper (name on it).
                                                  Use for your own records.
  AI_demand_planning_OOS_benchmark_anonymized.tex IJF SUBMISSION main file (double-blind:
                                                  no author identity). Set this as main doc.
  AI_demand_planning_OOS_benchmark_title_page.tex IJF SUBMISSION title page (author,
                                                  affiliation, abstract, declarations).
  figures/                                        6 PNG figures (\\graphicspath{{figures/}}).

IJF SUBMISSION (International Journal of Forecasting, double-blind):
  - Main manuscript  = *_anonymized.tex  (compile -> PDF)
  - Title page       = *_title_page.tex  (compile -> PDF, uploaded separately)
  - Cover letter     = IJF_cover_letter.pdf (outside this bundle)
  Fill the corresponding-author e-mail placeholder on the title page before submitting.

Packages (all standard in Overleaf TeX Live): geometry, graphicx, booktabs, array,
ragged2e, caption, fontenc(T1), newtxtext/newtxmath, hyperref.
"""
open(os.path.join(OV, 'README_OVERLEAF.txt'), 'w', encoding='utf-8').write(README)

zpath = os.path.join(MAN, 'overleaf_submission.zip')
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(OV):
        for fn in files:
            full = os.path.join(root, fn)
            z.write(full, os.path.relpath(full, OV))
print('Overleaf bundle rebuilt:', zpath, os.path.getsize(zpath) // 1024, 'KB')
print('tex files:', [f for f in sorted(os.listdir(OV)) if f.endswith('.tex')])
print('figures:', len(figs))
