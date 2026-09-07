"""
24_build_arxiv.py -- assemble a flat, self-contained arXiv submission from the
built LaTeX manuscript.

arXiv compiles each submission in a single flat directory, so three things have to
change relative to the local .tex:
  * \\graphicspath must point at the submission directory, not ../results/figures/
  * every referenced figure must sit beside the .tex
  * \\pdfoutput=1 in the first few lines tells arXiv to use pdfLaTeX rather than
    trying DVI first, which is what you want with PNG figures

It also writes abstract.txt, because arXiv asks for the abstract as plain text in a
web form with a 1920 character limit, and the LaTeX abstract has to be converted by
hand otherwise.

Writes manuscript/arxiv/ and manuscript/arxiv_submission.tar.gz
"""
import os, re, shutil, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAN = os.path.join(ROOT, 'manuscript')
FIGS = os.path.join(ROOT, 'results', 'figures')
OUT = os.path.join(MAN, 'arxiv')

SRC = os.path.join(MAN, 'AI_demand_planning_OOS_benchmark.tex')
TEXNAME = 'AI_demand_planning_OOS_benchmark.tex'

os.makedirs(OUT, exist_ok=True)
# Clear only what this script manages, and tolerate locks. A blanket rmtree fails
# with PermissionError whenever the compiled PDF is open in a viewer.
for f in os.listdir(OUT):
    if os.path.splitext(f)[1].lower() in ('.tex', '.png', '.txt'):
        try:
            os.remove(os.path.join(OUT, f))
        except OSError as e:
            print(f'  could not remove {f}: {e}')

tex = open(SRC, encoding='utf-8').read()

# 1. force pdfLaTeX on arXiv
if '\\pdfoutput=1' not in tex:
    tex = '\\pdfoutput=1\n' + tex

# 2. flatten the graphics path
tex = tex.replace('\\graphicspath{{../results/figures/}}', '\\graphicspath{{./}}')

open(os.path.join(OUT, TEXNAME), 'w', encoding='utf-8', newline='\n').write(tex)

# 3. copy every referenced figure beside the .tex
refs = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', tex)
missing = []
for f in sorted(set(refs)):
    src = os.path.join(FIGS, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(OUT, f))
    else:
        missing.append(f)
print(f'figures referenced: {len(set(refs))}, copied: {len(set(refs)) - len(missing)}')
if missing:
    print('  MISSING:', missing)

# 4. plain-text abstract for the arXiv metadata form
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.S)
abstract = m.group(1).strip() if m else ''
plain = abstract
plain = re.sub(r'\\textbf\{([^}]*)\}', r'\1', plain)
plain = re.sub(r'\\textit\{([^}]*)\}', r'\1', plain)
plain = re.sub(r'\\emph\{([^}]*)\}', r'\1', plain)
plain = plain.replace('\\%', '%').replace('\\&', '&').replace('\\_', '_')
plain = plain.replace('\\na\\"{\\i}ve', 'naive').replace('\\"{\\i}', 'i')
plain = re.sub(r'\\[a-zA-Z]+\s*', '', plain)
plain = plain.replace('{', '').replace('}', '')
plain = plain.replace('---', ', ').replace('--', '-')
plain = re.sub(r'[ \t]+', ' ', plain).strip()
open(os.path.join(OUT, 'abstract.txt'), 'w', encoding='utf-8', newline='\n').write(plain + '\n')

LIMIT = 1920
print(f'abstract.txt: {len(plain)} chars, {len(plain.split())} words '
      f'(arXiv metadata limit {LIMIT})')
if len(plain) > LIMIT:
    print(f'  OVER THE LIMIT BY {len(plain)-LIMIT} CHARS. arXiv will reject the '
          f'metadata form until this is shortened.')

# 5. gates
print('\n--- checks ---')
print(f'  em dash (---)        : {tex.count("---")}')
print(f'  raw U+2014 / U+2013  : {tex.count(chr(0x2014))} / {tex.count(chr(0x2013))}')
for env in ('document', 'abstract', 'tabular', 'center'):
    o, c = tex.count('\\begin{%s}' % env), tex.count('\\end{%s}' % env)
    print(f'  \\begin/\\end{{{env}}}{" "*(12-len(env))}: {o} / {c} {"OK" if o == c else "UNBALANCED"}')
stray = sorted({c for c in tex if ord(c) > 127})
print(f'  stray non-ASCII      : {[hex(ord(c)) for c in stray] if stray else "none"}')
flat = '{{./}}' in tex
pdfout = tex.startswith('\\pdfoutput=1')
print('  graphicspath         : ' + ('flat (./)' if flat else 'STILL RELATIVE'))
print('  pdfoutput            : ' + ('set' if pdfout else 'MISSING'))

# 6. tarball
tgz = os.path.join(MAN, 'arxiv_submission.tar.gz')
# Ship the source and the figures only. abstract.txt is metadata for the web form,
# and .aux/.log/.out/.pdf are local compile byproducts: arXiv rejects or ignores
# them, and a bundled PDF can make it skip building from source altogether.
SHIP = ('.tex', '.png')
with tarfile.open(tgz, 'w:gz') as t:
    for f in sorted(os.listdir(OUT)):
        if os.path.splitext(f)[1].lower() in SHIP:
            t.add(os.path.join(OUT, f), arcname=f)
print(f'\nwrote {OUT}')
print(f'wrote {tgz} ({os.path.getsize(tgz)/1024:.0f} KB)')
print('  contents:', ', '.join(sorted(os.listdir(OUT))))
