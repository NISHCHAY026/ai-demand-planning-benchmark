"""15_build_cover_letter.py -- submission cover letter to the International Journal of
Forecasting, rendered to .docx, .pdf and .md."""
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter as LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'manuscript')
from datetime import date as _date
DATE = _date.today().strftime('%B %d, %Y').replace(' 0', ' ')   # build date, e.g. 'June 9, 2026'
JOURNAL = 'International Journal of Forecasting'
TITLE = ('Evaluation design decides the winner: horizon, leakage and metric effects '
         'in intermittent demand forecasting')
AUTHOR = 'Nishchay Patel'
AFFIL = 'Independent Researcher'

HEAD = [DATE, '', 'The Editors', JOURNAL, '', f'Re: Submission of an original research manuscript']
SAL = 'Dear Editors,'
BODY = [
 (f'I am pleased to submit the enclosed manuscript, “{TITLE},” for consideration as an original '
  'research article in the International Journal of Forecasting.'),
 ('The central claim is that a forecasting comparison reports two things at once, something about the '
  'methods and something about the evaluation that ranked them, and that the second is routinely left '
  'implicit. Holding the data, the forecasters and the protocol fixed on two public retail panels that '
  'bracket the intermittency spectrum, I vary three individually defensible design choices and each '
  'one reverses the ranking. Scoring on cumulative lead-time demand rather than one step ahead moves '
  'Croston from seventh of eight classical methods to first on the denser panel, its error against a '
  'naive benchmark falling from 0.992 to 0.563, so a long-standing empirical verdict on the Croston '
  'family turns out to be in part an artefact of how it is scored, and in part a confusion between the '
  'family and two of its members: TSB, the third, is second best on both panels at one step without '
  'any change of horizon. Restricting a single price feature '
  'to strictly past values removes a silent target leak, since a same-week transacted price identifies '
  'sale weeks perfectly and carries 42 percent of the model’s gain, and moves the gradient-boosted '
  'model from ahead of every classical method to behind tuned exponential smoothing. Replacing MASE '
  'with RMSSE turns the naive benchmark from the method winning the most series into the worst method '
  'overall on both panels.'),
 ('The work extends an evaluation lineage this journal has shaped. Tashman (2000) set the standard for '
  'out-of-sample test design; Kolassa (2016) argued that the metric must match the decision in '
  'low-count retail settings; and Teunter and Duncan (2009) predicted that per-period scoring would '
  'understate Croston-type estimators, which is what the horizon result confirms at scale on public '
  'data. The benchmark supporting these demonstrations is itself substantial: eight classical '
  'forecasters including TSB and the two standard temporal-aggregation methods (ADIDA, MAPA), a '
  'global gradient-boosted model, two deep global models (NHITS and DeepAR) and two '
  'pretrained zero-shot foundation models (Chronos-Bolt and TimesFM), all evaluated under one '
  'identical rolling-origin protocol on the M5 competition data and UCI Online Retail II. The '
  'pretrained models also serve as a falsification test of the data-sufficiency explanation for why '
  'machine learning fails on sparse demand, since they need no per-series history and still lose to '
  'trained models in every sparse demand class.'),
 ('The practical guidance follows directly and is of immediate use to planners: match the error metric '
  'to the loss the decision carries, match the evaluation horizon to the replenishment cycle, audit '
  'the timing of every feature before believing a reported gain, and validate out-of-sample rather '
  'than on the fitting window. Every table and figure regenerates end to end from the public sources, '
  'so each design choice I vary can be varied again by others.'),
 ('I confirm that this manuscript is original, has not been published previously, and is not under '
  'consideration for publication elsewhere. There are no conflicts of interest to declare. In keeping '
  'with the journal’s emphasis on replicability, all datasets are public and the full analysis code is '
  'available for review and release. The manuscript has been prepared for double-blind review; a '
  'separate title page carries the author identification.'),
 ('Thank you for considering this submission. I would be glad to provide any further information the '
  'editors or reviewers may require.'),
]
CLOSE = ['Sincerely,', '', AUTHOR, AFFIL]

# ---------- DOCX ----------
doc = Document()
n = doc.styles['Normal']; n.font.name = 'Times New Roman'; n.font.size = Pt(11)
n.paragraph_format.space_after = Pt(8); n.paragraph_format.line_spacing = 1.15
sec = doc.sections[0]
sec.top_margin = sec.bottom_margin = Inches(1); sec.left_margin = sec.right_margin = Inches(1)
def dp(t, after=8, align='left'):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align == 'justify' else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(t); r.font.name = 'Times New Roman'; r.font.size = Pt(11); return p
for h in HEAD: dp(h, after=2)
dp('', after=2); dp(SAL, after=8)
for b in BODY: dp(b, after=8, align='justify')
for c in CLOSE: dp(c, after=2)
doc.save(os.path.join(OUT, 'IJF_cover_letter.docx'))

# ---------- MD ----------
md = ['  \n'.join(HEAD), '', SAL, '', *[b + '\n' for b in BODY], '  \n'.join(CLOSE)]
open(os.path.join(OUT, 'IJF_cover_letter.md'), 'w', encoding='utf-8').write('\n'.join(md))

# ---------- PDF ----------
F = 'TNR'
try:
    pdfmetrics.registerFont(TTFont('TNR', r'C:\Windows\Fonts\times.ttf'))
    pdfmetrics.registerFont(TTFont('TNR-Italic', r'C:\Windows\Fonts\timesi.ttf'))
except Exception:
    F = 'Times-Roman'
body_style = ParagraphStyle('b', fontName=F, fontSize=11, leading=15, alignment=TA_JUSTIFY, spaceAfter=8)
flat = ParagraphStyle('f', fontName=F, fontSize=11, leading=14, alignment=TA_LEFT, spaceAfter=2)
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
story = []
for h in HEAD: story.append(Paragraph(esc(h) or '&nbsp;', flat))
story.append(Spacer(1, 6)); story.append(Paragraph(SAL, flat)); story.append(Spacer(1, 6))
for b in BODY: story.append(Paragraph(esc(b), body_style))
story.append(Spacer(1, 6))
for c in CLOSE: story.append(Paragraph(esc(c) or '&nbsp;', flat))
SimpleDocTemplate(os.path.join(OUT, 'IJF_cover_letter.pdf'), pagesize=LETTER,
                  topMargin=inch, bottomMargin=inch, leftMargin=inch, rightMargin=inch
                  ).build(story)
print('Saved IJF cover letter: docx, md, pdf')
