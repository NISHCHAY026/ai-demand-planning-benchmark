"""
23_build_pandoc_md.py -- render the whole manuscript as ONE Pandoc-ready Markdown file
with inline LaTeX math, from the same shared content blocks as every other output.

Differences from 14_build_markdown.py, which produces plain GitHub-Flavored Markdown:
  * YAML front matter carrying title, author, abstract and keywords, so the file
    converts straight to PDF/DOCX/LaTeX with pandoc and needs no wrapper.
  * Mathematical notation written as inline LaTeX rather than Unicode glyphs, so it
    typesets properly instead of depending on font coverage for alpha, superscript two,
    set membership and the minus sign.
  * Self-contained in the sense that all eight sections, all nine tables and all
    references live in the single file. Figures are referenced by relative path, since
    a Markdown file cannot carry binary image data.

Convert with, for example:
    pandoc AI_demand_planning_OOS_benchmark_pandoc.md -o paper.pdf
    pandoc AI_demand_planning_OOS_benchmark_pandoc.md -o paper.docx
    pandoc AI_demand_planning_OOS_benchmark_pandoc.md -s -o paper.tex

Writes manuscript/AI_demand_planning_OOS_benchmark_pandoc.md
"""
import os
import manuscript_content as MC

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript')
os.makedirs(OUTDIR, exist_ok=True)
FIGREL = '../results/figures/'

# Unicode notation -> inline LaTeX. Order matters: the most specific pattern must come
# first, because each replacement consumes the Unicode source character and later
# patterns then cannot match inside the LaTeX it produced.
MATH = [
    ('ADI = 1.32, CV² = 0.49', r'$\mathrm{ADI} = 1.32$, $\mathrm{CV}^2 = 0.49$'),
    ('α∈{0.05,…,0.4}', r'$\alpha \in \{0.05,\dots,0.4\}$'),
    ('α∈{0.01,…,0.3}', r'$\alpha \in \{0.01,\dots,0.3\}$'),
    ('k∈{1,2,3,4,6,13}', r'$k \in \{1,2,3,4,6,13\}$'),
    ('k∈{2,3,4,6,13}', r'$k \in \{2,3,4,6,13\}$'),
    ('k∈{2,3,4}', r'$k \in \{2,3,4\}$'),
    ('1 − α/2', r'$1-\alpha/2$'),
    ('P(y > 0 | price deviates from the series median) = 1.0',
     r'$P(y > 0 \mid \text{price deviates from the series median}) = 1.0$'),
    ('ADI = 1.32', r'$\mathrm{ADI} = 1.32$'),
    ('CV² = 0.49', r'$\mathrm{CV}^2 = 0.49$'),
    ('ADI / CV²', r'$\mathrm{ADI}$ / $\mathrm{CV}^2$'),
    ('CV²', r'$\mathrm{CV}^2$'),
    ('MASE = 1', r'$\mathrm{MASE} = 1$'),
    ('MASE < 1', r'$\mathrm{MASE} < 1$'),
    ('in-sample → out-of-sample', r'in-sample $\to$ out-of-sample'),
    ('week t−1', r'week $t-1$'),
    (' α ', r' $\alpha$ '),
]


def math(s):
    s = str(s)
    for old, new in MATH:
        s = s.replace(old, new)
    return s


def cell(s):
    return math(s).replace('|', r'\|').replace('\n', ' ')


def table_md(header, rows, note, opts):
    opts = opts or {}
    out = ['', '| ' + ' | '.join(cell(h) for h in header) + ' |',
           '| ' + ' | '.join([':---'] + [':---:'] * (len(header) - 1)) + ' |']
    for ri, row in enumerate(rows):
        bold = opts.get('bold_last_row') and ri == len(rows) - 1
        out.append('| ' + ' | '.join(f'**{cell(v)}**' if bold else cell(v) for v in row) + ' |')
    if note:
        out += ['', f'*{math(note)}*']
    return '\n'.join(out) + '\n'


def fig_md(fname, caption):
    alt = caption.split('. ', 1)[0]
    return f'\n![{cell(alt)}]({FIGREL}{fname})\n\n*{math(caption)}*\n'


def yaml_block(text):
    """Emit a YAML block scalar so quotes and colons in the prose need no escaping."""
    return '\n'.join('    ' + line for line in text.split('\n'))


def render(blocks, out_path):
    title = author = affil = abstract = keywords = None
    for i, b in enumerate(blocks):
        if b[0] == 'title':
            title = b[1]
        elif b[0] == 'authors':
            author, affil = ', '.join(b[1]), b[2]
        elif b[0] == 'h_abstract':
            abstract = blocks[i + 1][1]
        elif b[0] == 'keywords':
            keywords = b[1].strip('*').replace('Keywords: ', '')

    md = ['---']
    md.append(f'title: |\n{yaml_block(math(title))}')
    if author:
        md.append(f'author: |\n{yaml_block(author + (", " + affil if affil else ""))}')
    if abstract:
        md.append(f'abstract: |\n{yaml_block(math(abstract))}')
    if keywords:
        md.append(f'keywords: |\n{yaml_block(math(keywords))}')
    md += ['geometry: margin=1in', 'fontsize: 11pt', 'linkcolor: black',
           'header-includes:', '    - \\usepackage{booktabs}', '    - \\usepackage{amsmath}',
           '---', '']

    skip_next_p = False
    i = 0
    while i < len(blocks):
        b = blocks[i]; k = b[0]
        if k in ('title', 'authors', 'keywords'):
            i += 1; continue
        if k == 'h_abstract':
            skip_next_p = True   # abstract already lives in the front matter
            i += 1; continue
        if k == 'p' and skip_next_p:
            skip_next_p = False
            i += 1; continue
        if k == 'subtitle':
            md.append(f'*{math(b[1])}*\n')
        elif k == 'note':
            md.append(f'> {math(b[1])}\n')
        elif k == 'h1':
            md.append(f'\n# {math(b[1])}\n')
        elif k == 'h2':
            md.append(f'\n## {math(b[1])}\n')
        elif k == 'p':
            md.append(math(b[1]) + '\n')
        elif k == 'table':
            md.append(table_md(b[1], b[2], b[4], b[5] if len(b) > 5 else None))
        elif k == 'figure':
            md.append(fig_md(b[1], b[2]))
        elif k == 'bullet':
            while i < len(blocks) and blocks[i][0] == 'bullet':
                md.append(f'- {math(blocks[i][1])}'); i += 1
            md.append('')
            continue
        elif k == 'refs':
            for j, r in enumerate(b[1], 1):
                md.append(f'{j}. {math(r)}')
            md.append('')
        i += 1

    text = '\n'.join(md)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)

    # release gate: no em dashes, and no unconverted maths glyphs left in the prose
    leftovers = {c: text.count(c) for c in 'α²∈−…→' if c in text}
    print(f'Saved Pandoc Markdown: {out_path}')
    print(f'  em dashes (U+2014): {text.count(chr(0x2014))}')
    print('  unconverted maths glyphs: ' + (repr(leftovers) if leftovers else 'none'))
    print(f'  lines: {len(text.splitlines())}, chars: {len(text):,}')


if __name__ == '__main__':
    render(MC.blocks(), os.path.join(OUTDIR, 'AI_demand_planning_OOS_benchmark_pandoc.md'))
