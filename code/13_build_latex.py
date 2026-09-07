"""13_build_latex.py -- render the manuscript, and an optional companion document, to LaTeX (.tex) from the
shared content blocks. Compiles with pdflatex (article class; graphicx, booktabs)."""
import os, re
import manuscript_content as MC

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript'); os.makedirs(OUTDIR, exist_ok=True)

# unicode -> LaTeX (applied AFTER escaping ASCII specials)
UNI = [('α', r'$\alpha$'), ('β', r'$\beta$'), ('²', r'\textsuperscript{2}'),
       ('→', r'$\rightarrow$'), ('≥', r'$\geq$'), ('≤', r'$\leq$'), ('≈', r'$\approx$'),
       ('∈', r'$\in$'), ('×', r'$\times$'), ('−', r'$-$'), ('—', '---'), ('–', '--'), ('…', r'\ldots{}'),
       ('’', "'"), ('‘', '`'), ('“', '``'), ('”', "''"),
       ('ï', r'\"{\i}'), ('é', r"\'e"), ('è', r'\`e'), ('ü', r'\"u'), ('ö', r'\"o'),
       ('ç', r'\c{c}'), ('ñ', r'\~n'), ('à', r'\`a'), ('£', r'\pounds{}'),
       # accented capitals + Turkish letters introduced by author names (Pinçe, Arık, Wallström)
       ('Ç', r'\c{C}'), ('Ö', r'\"O'), ('Ü', r'\"U'), ('Ä', r'\"A'), ('ä', r'\"a'),
       ('ı', r'{\i}'), ('İ', r'\.I'), ('ş', r'\c{s}'), ('Ş', r'\c{S}'), ('ğ', r'\u{g}'),
       ('Ğ', r'\u{G}'), ('á', r"\'a"), ('í', r"\'i"), ('ó', r"\'o"), ('ú', r"\'u"),
       ('â', r'\^a'), ('ô', r'\^o'), ('Á', r"\'A"), ('É', r"\'E")]
SPECIAL = [('\\', r'\textbackslash{}'), ('&', r'\&'), ('%', r'\%'), ('$', r'\$'),
           ('#', r'\#'), ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
           ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}'),
           ('<', r'\textless{}'), ('>', r'\textgreater{}')]

def esc(s):
    s = str(s)
    for a, b in SPECIAL: s = s.replace(a, b)
    for a, b in UNI:     s = s.replace(a, b)
    s = s.replace('$$', '')          # merge adjacent inline-math (e.g. "α∈" -> $\alpha\in$)
    return s

PRE = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{ragged2e}
\usepackage{caption}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\graphicspath{{../results/figures/}}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\captionsetup{labelformat=empty,font=small}
\title{%s}
\author{%s}
\date{}
\begin{document}
\maketitle
"""

# letterpaper with 1in margins leaves a 6.5in text block. The declared column
# widths are authored for readability, not measured against the page, so scale
# them down whenever they plus the intercolumn padding would overrun it. Without
# this every table in the paper overflows the right margin, by up to 149pt.
TEXTWIDTH_IN = 6.5
TABCOLSEP_IN = 3 / 72.27          # \tabcolsep set to 3pt below

def fit_widths(widths):
    pad = 2 * len(widths) * TABCOLSEP_IN
    avail = TEXTWIDTH_IN - pad
    total = sum(widths)
    if total <= avail:
        return list(widths)
    return [w * avail / total for w in widths]

def col_spec(widths):
    widths = fit_widths(widths)
    cols = '>{\\RaggedRight}p{%.2fin}' % widths[0]
    for w in widths[1:]:
        cols += '>{\\centering\\arraybackslash}p{%.2fin}' % w
    return cols

def table_tex(header, rows, widths, note, opts):
    opts = opts or {}
    out = ['\\begin{center}\\small\\setlength{\\tabcolsep}{3pt}',
           '\\begin{tabular}{%s}' % col_spec(widths), '\\toprule']
    out.append(' & '.join('\\textbf{%s}' % esc(h) for h in header) + ' \\\\')
    out.append('\\midrule')
    for ri, row in enumerate(rows):
        bold = opts.get('bold_last_row') and ri == len(rows) - 1
        cells = [('\\textbf{%s}' % esc(v)) if bold else esc(v) for v in row]
        out.append(' & '.join(cells) + ' \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{center}']
    if note:
        out.append('\\noindent{\\footnotesize\\textit{%s}}\\par\\smallskip' % esc(note))
    return '\n'.join(out)

def fig_tex(fname, caption):
    parts = caption.split('. ', 1)
    cap = '\\textbf{%s.} ' % esc(parts[0]) + ('\\textit{%s}' % esc(parts[1]) if len(parts) > 1 else '')
    return ('\\begin{center}\\includegraphics[width=0.95\\linewidth]{%s}\\end{center}\n'
            '\\noindent{\\footnotesize %s}\\par\\medskip' % (fname, cap))

def render(blocks, out_path, is_brief=False):
    title = next(b[1] for b in blocks if b[0] == 'title')
    if is_brief:
        body = [r'\documentclass[11pt]{article}',
                r'\usepackage[letterpaper,margin=1in]{geometry}',
                r'\usepackage[T1]{fontenc}\usepackage{newtxtext,newtxmath}',
                r'\usepackage[hidelinks]{hyperref}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}',
                r'\begin{document}',
                r'\begin{center}{\Large\textbf{%s}}\end{center}' % esc(title)]
    else:
        ab = next((b for b in blocks if b[0] == 'authors'), None)
        autharg = (esc(', '.join(ab[1])) + r'\\ \textit{' + esc(ab[2]) + '}') if ab else ''
        body = [PRE % (esc(title), autharg)]
    i = 0
    while i < len(blocks):
        b = blocks[i]; k = b[0]
        if k in ('title', 'authors'):
            pass
        elif k == 'subtitle':
            body.append(r'\begin{center}\textit{%s}\end{center}' % esc(b[1]))
        elif k == 'note':
            body.append(r'{\small\textit{%s}}\par\medskip' % esc(b[1]))
        elif k == 'h_abstract':
            body.append(r'\begin{abstract}')
            # next block is the abstract paragraph
        elif k == 'keywords':
            body.append(r'\noindent\textit{%s}\par' % esc(b[1]))
        elif k == 'h1':
            body.append(r'\section*{%s}' % esc(b[1]))
        elif k == 'h2':
            body.append(r'\subsection*{%s}' % esc(b[1]))
        elif k == 'p':
            body.append(esc(b[1]))
            # close abstract env if the previous structural block was the abstract header
            if i >= 1 and blocks[i-1][0] == 'h_abstract':
                body.append(r'\end{abstract}')
        elif k == 'table':
            note = b[4]; opts = b[5] if len(b) > 5 else None
            body.append(table_tex(b[1], b[2], b[3], note, opts))
        elif k == 'figure':
            body.append(fig_tex(b[1], b[2]))
        elif k == 'bullet':
            items = []
            while i < len(blocks) and blocks[i][0] == 'bullet':
                items.append(r'\item ' + esc(blocks[i][1])); i += 1
            body.append('\\begin{itemize}\n' + '\n'.join(items) + '\n\\end{itemize}')
            continue
        elif k == 'refs':
            body.append(r'{\small')
            for r in b[1]:
                # Emit any trailing DOI/URL inside \url{} so xurl can break it. Left as
                # bare escaped text it cannot hyphenate and overflows the right margin.
                m = re.search(r'(https?://\S+?)\s*$', r)
                if m:
                    line = esc(r[:m.start()]) + r'\url{' + m.group(1) + '}'
                else:
                    line = esc(r)
                body.append(r'\hangindent=1.5em\hangafter=1 ' + line + r'\par\smallskip')
            body.append(r'}')
        i += 1
    body.append(r'\end{document}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(body))
    print('Saved LaTeX:', out_path)

if __name__ == '__main__':
    render(MC.blocks(), os.path.join(OUTDIR, 'AI_demand_planning_OOS_benchmark.tex'))
    _blocks, _stem, _brief = MC.companion_blocks()
    if _blocks:
        render(_blocks, os.path.join(OUTDIR, f'{_stem}.tex'), is_brief=_brief)
