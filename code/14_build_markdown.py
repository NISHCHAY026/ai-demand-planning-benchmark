"""14_build_markdown.py -- render the manuscript, and an optional companion document, to GitHub-Flavored
Markdown from the shared content blocks. UTF-8; figures embedded by relative path."""
import os
import manuscript_content as MC

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript'); os.makedirs(OUTDIR, exist_ok=True)
FIGREL = '../results/figures/'

def cell(s): return str(s).replace('|', r'\|').replace('\n', ' ')

def table_md(header, rows, note, opts):
    opts = opts or {}
    out = ['', '| ' + ' | '.join(cell(h) for h in header) + ' |']
    out.append('| ' + ' | '.join([':---'] + [':---:'] * (len(header) - 1)) + ' |')
    for ri, row in enumerate(rows):
        bold = opts.get('bold_last_row') and ri == len(rows) - 1
        cells = [f'**{cell(v)}**' if bold else cell(v) for v in row]
        out.append('| ' + ' | '.join(cells) + ' |')
    if note:
        out += ['', f'*{note}*']
    return '\n'.join(out) + '\n'

def fig_md(fname, caption):
    parts = caption.split('. ', 1)
    alt = parts[0]
    return f'\n![{cell(alt)}]({FIGREL}{fname})\n\n*{caption}*\n'

def render(blocks, out_path, is_brief=False):
    md = []
    i = 0
    while i < len(blocks):
        b = blocks[i]; k = b[0]
        if k == 'title':
            md.append(f'# {b[1]}\n')
        elif k == 'authors':
            md.append(f'**{", ".join(b[1])}**  \n*{b[2]}*\n')
        elif k == 'subtitle':
            md.append(f'*{b[1]}*\n')
        elif k == 'note':
            md.append(f'> {b[1]}\n')
        elif k == 'h_abstract':
            md.append('## Abstract\n')
        elif k == 'keywords':
            md.append(f'*{b[1]}*\n')
        elif k == 'h1':
            md.append(f'\n## {b[1]}\n')
        elif k == 'h2':
            md.append(f'\n### {b[1]}\n')
        elif k == 'p':
            md.append(b[1] + '\n')
        elif k == 'table':
            note = b[4]; opts = b[5] if len(b) > 5 else None
            md.append(table_md(b[1], b[2], note, opts))
        elif k == 'figure':
            md.append(fig_md(b[1], b[2]))
        elif k == 'bullet':
            while i < len(blocks) and blocks[i][0] == 'bullet':
                md.append(f'- {blocks[i][1]}'); i += 1
            md.append('')
            continue
        elif k == 'refs':
            # heading comes from the preceding ('h1', 'References') block
            for j, r in enumerate(b[1], 1):
                md.append(f'{j}. {r}')
            md.append('')
        i += 1
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print('Saved Markdown:', out_path)

if __name__ == '__main__':
    render(MC.blocks(), os.path.join(OUTDIR, 'AI_demand_planning_OOS_benchmark.md'))
    _blocks, _stem, _brief = MC.companion_blocks()
    if _blocks:
        render(_blocks, os.path.join(OUTDIR, f'{_stem}.md'), is_brief=_brief)
