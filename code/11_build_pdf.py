"""11_build_pdf.py -- render the manuscript, and an optional companion document, to PDF (reportlab) from the
same shared content blocks used by the .docx builders. No Office/LibreOffice required."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
                                KeepTogether)
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import manuscript_content as MC

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'figures')
OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript')
NAVY = colors.HexColor('#1E2761')

# Times New Roman TTF (Windows) -> full Unicode (α, →, ≥, ², curly quotes)
F = 'TNR'
try:
    pdfmetrics.registerFont(TTFont('TNR', r'C:\Windows\Fonts\times.ttf'))
    pdfmetrics.registerFont(TTFont('TNR-Bold', r'C:\Windows\Fonts\timesbd.ttf'))
    pdfmetrics.registerFont(TTFont('TNR-Italic', r'C:\Windows\Fonts\timesi.ttf'))
    pdfmetrics.registerFont(TTFont('TNR-BoldItalic', r'C:\Windows\Fonts\timesbi.ttf'))
    pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-Bold', italic='TNR-Italic',
                                  boldItalic='TNR-BoldItalic')
except Exception:
    F = 'Times-Roman'

def S(name, **kw):
    base = dict(fontName=F, fontSize=11, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6)
    base.update(kw); return ParagraphStyle(name, **base)

ST = {
 'title':    S('title', fontName=F+'-Bold' if F=='TNR' else 'Times-Bold', fontSize=16, leading=19,
               alignment=TA_CENTER, spaceAfter=10),
 'authors':  S('authors', fontSize=11, alignment=TA_CENTER, spaceAfter=2),
 'affil':    S('affil', fontName=F+'-Italic' if F=='TNR' else 'Times-Italic', fontSize=9,
               alignment=TA_CENTER, spaceAfter=12),
 'subtitle': S('subtitle', fontName=F+'-Italic' if F=='TNR' else 'Times-Italic', fontSize=10,
               alignment=TA_CENTER, spaceAfter=6),
 'note':     S('note', fontName=F+'-Italic' if F=='TNR' else 'Times-Italic', fontSize=9,
               alignment=TA_CENTER, spaceAfter=8),
 'abstract': S('abstract', fontName=F+'-Bold' if F=='TNR' else 'Times-Bold', fontSize=11, spaceAfter=2,
               alignment=TA_LEFT),
 'keywords': S('keywords', fontName=F+'-Italic' if F=='TNR' else 'Times-Italic', fontSize=10, spaceAfter=10),
 'h1':       S('h1', fontName=F+'-Bold' if F=='TNR' else 'Times-Bold', fontSize=14, leading=17,
               textColor=colors.black, alignment=TA_LEFT, spaceBefore=12, spaceAfter=5),
 'h2':       S('h2', fontName=F+'-Bold' if F=='TNR' else 'Times-Bold', fontSize=12, leading=15,
               alignment=TA_LEFT, spaceBefore=10, spaceAfter=4),
 'p':        S('p'),
 'bullet':   S('bullet', fontSize=10.5, leading=13.5, leftIndent=16, bulletIndent=4, spaceAfter=3),
 'tnote':    S('tnote', fontName=F+'-Italic' if F=='TNR' else 'Times-Italic', fontSize=8.5,
               alignment=TA_LEFT, spaceAfter=10),
 'ref':      S('ref', fontSize=9.5, leading=11.5, leftIndent=18, firstLineIndent=-18, spaceAfter=4),
 'cap':      S('cap', fontSize=9, leading=11, alignment=TA_LEFT, spaceAfter=12),
}
BOLD = F+'-Bold' if F=='TNR' else 'Times-Bold'
ITAL = F+'-Italic' if F=='TNR' else 'Times-Italic'

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def fig_flow(fname, caption, maxw=6.3):
    path = os.path.join(FIG, fname)
    iw, ih = ImageReader(path).getSize()
    w = min(maxw*inch, 6.5*inch); h = w*ih/iw
    parts = caption.split('. ', 1)
    cap = f'<font name="{BOLD}">{esc(parts[0])}. </font>'
    if len(parts) > 1: cap += f'<font name="{ITAL}">{esc(parts[1])}</font>'
    return KeepTogether([Image(path, width=w, height=h, hAlign='CENTER'),
                         Spacer(1, 3), Paragraph(cap, ST['cap'])])

def table_flow(header, rows, widths, note=None, opts=None):
    opts = opts or {}
    hdr = [Paragraph(f'<font color="white"><b>{esc(h)}</b></font>',
                     ParagraphStyle('h', fontName=BOLD, fontSize=8, leading=9.5,
                                    alignment=TA_CENTER, textColor=colors.white)) for h in header]
    body = [hdr]
    for ri, row in enumerate(rows):
        boldrow = opts.get('bold_last_row') and ri == len(rows)-1
        fn = BOLD if boldrow else F
        cells = []
        for ci, v in enumerate(row):
            al = TA_LEFT if ci == 0 else TA_CENTER
            cells.append(Paragraph(esc(str(v)), ParagraphStyle('c', fontName=fn, fontSize=8, leading=10, alignment=al)))
        body.append(cells)
    cw = [w*inch for w in widths]
    t = Table(body, colWidths=cw, repeatRows=1)
    style = [('BACKGROUND',(0,0),(-1,0),NAVY), ('GRID',(0,0),(-1,-1),0.5,colors.grey),
             ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),2),
             ('BOTTOMPADDING',(0,0),(-1,-1),2), ('LEFTPADDING',(0,0),(-1,-1),3),
             ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F2F3F7')])]
    t.setStyle(TableStyle(style))
    flow = [t]
    if note: flow += [Spacer(1,2), Paragraph(esc(note), ST['tnote'])]
    return KeepTogether(flow) if len(rows) <= 6 else (flow[0] if len(flow)==1 else _seq(flow))

def _seq(flow):
    from reportlab.platypus import Flowable
    return flow  # return list; extend() handles it

def render(blocks, out_path, title='Document'):
    story = []
    for blk in blocks:
        k = blk[0]
        if k == 'title':
            story.append(Paragraph(esc(blk[1]), ST['title']))
        elif k == 'authors':
            story.append(Paragraph(esc(', '.join(blk[1])), ST['authors']))
            story.append(Paragraph(esc(blk[2]), ST['affil']))
        elif k == 'subtitle':
            story.append(Paragraph(esc(blk[1]), ST['subtitle']))
        elif k == 'note':
            story.append(Paragraph(esc(blk[1]), ST['note']))
        elif k == 'h_abstract':
            story.append(Paragraph(esc(blk[1]), ST['abstract']))
        elif k == 'keywords':
            story.append(Paragraph(esc(blk[1]), ST['keywords']))
        elif k == 'h1':
            story.append(Paragraph(esc(blk[1]), ST['h1']))
        elif k == 'h2':
            story.append(Paragraph(esc(blk[1]), ST['h2']))
        elif k == 'p':
            story.append(Paragraph(esc(blk[1]), ST['p']))
        elif k == 'bullet':
            story.append(Paragraph(esc(blk[1]), ST['bullet'], bulletText='•'))
        elif k == 'table':
            header, rows, widths, note = blk[1], blk[2], blk[3], blk[4]
            opts = blk[5] if len(blk) > 5 else None
            tf = table_flow(header, rows, widths, note, opts)
            story.extend(tf) if isinstance(tf, list) else story.append(tf)
        elif k == 'figure':
            story.append(fig_flow(blk[1], blk[2]))
        elif k == 'refs':
            for r in blk[1]:
                story.append(Paragraph(esc(r), ST['ref']))

    def page_num(canvas, doc):
        canvas.saveState(); canvas.setFont(F, 9)
        canvas.drawCentredString(letter[0]/2, 0.5*inch, str(doc.page)); canvas.restoreState()

    doc = SimpleDocTemplate(out_path, pagesize=letter, topMargin=inch, bottomMargin=inch,
                            leftMargin=inch, rightMargin=inch, title=title)
    doc.build(story, onFirstPage=page_num, onLaterPages=page_num)
    print('Saved PDF:', out_path)

if __name__ == '__main__':
    render(MC.blocks(), os.path.join(OUTDIR, 'AI_demand_planning_OOS_benchmark.pdf'),
           'AI in supply-chain demand planning')
    _blocks, _stem, _ = MC.companion_blocks()
    if _blocks:
        render(_blocks, os.path.join(OUTDIR, f'{_stem}.pdf'), 'companion document')
