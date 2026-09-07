"""
12_check_citations.py -- verify citation integrity of the manuscript:
  (a) every in-text (Author, year) / Author (year) citation resolves to a reference;
  (b) every reference is cited at least once.
Prints a report and exits non-zero if any gap is found.
"""
import re, sys
import manuscript_content as MC

blocks = MC.blocks()
# collect body text and the references list
body, refs = [], []
for b in blocks:
    if b[0] in ('p', 'h1', 'h2', 'h_abstract', 'keywords') and isinstance(b[1], str):
        body.append(b[1])
    elif b[0] == 'table':
        body.append(' '.join(map(str, sum(b[2], []))) + ' ' + (b[4] or ''))
    elif b[0] == 'refs':
        refs = b[1]
text = ' '.join(body)

YEAR = r'(1[89]\d\d|20\d\d)'
STOP = {'In','We','The','On','Critical','Both','Section','Table','Figure','As','For','It','This',
        'LightGBM','NHITS','DeepAR','Tweedie','SNAP','SBC','MASE','ADI','US','U'}
NAME = r"[A-Z][A-Za-zÀ-ÿ’'\-]+"
cites = set()
# parentheticals: split on ';' and take the year present in EACH chunk
for m in re.finditer(r'\(([^()]+)\)', text):
    inner = m.group(1)
    if not re.search(YEAR, inner):
        continue
    for chunk in re.split(r';', inner):
        yrs = re.findall(YEAR, chunk)
        if not yrs:
            continue
        names = [n for n in re.findall(NAME, chunk) if n not in STOP]
        if names:
            cites.add((names[0], yrs[0]))
# narrative: Author (year) / Author et al. (year) / A, B and C (year)
for m in re.finditer(r'(' + NAME + r'(?:[ ,]+(?:and |& )?' + NAME + r'){0,3})(?:\s+et\s+al\.?)?\s*,?\s*\(' + YEAR + r'\)', text):
    names = [n for n in re.findall(NAME, m.group(1)) if n not in STOP]
    if names:
        cites.add((names[0], m.group(2)))

def ref_surnames_year(r):
    yr = re.search(YEAR, r); yr = yr.group(0) if yr else ''
    head = r.split(str(yr))[0] if yr else r
    surs = re.findall(NAME, head)
    return surs, yr

ref_index = [ref_surnames_year(r) for r in refs]

def resolves(surname, yr):
    sl = surname.lower()
    for surs, ry in ref_index:
        if ry == yr and any(sl == s.lower() or sl in s.lower() or s.lower() in sl for s in surs):
            return True
    # special case: Executive Order
    if surname.lower() in ('executive','u.s.','u') and any('Executive' in r and yr in r for r in refs):
        return True
    return False

print('=== in-text citations found:', len(cites), '===')
orphans = []
for sur, yr in sorted(cites):
    ok = resolves(sur, yr)
    print(f'  {"OK " if ok else "!! "} {sur} {yr}')
    if not ok: orphans.append((sur, yr))

print('\n=== references cited? ===')
uncited = []
for r, (surs, ry) in zip(refs, ref_index):
    head = surs[0] if surs else '?'
    hit = any((ry == yr) and any(s.lower() == sur.lower() or s.lower() in sur.lower()
              or sur.lower() in s.lower() for s in surs) for sur, yr in cites)
    if 'Executive Order' in r and '14017' in text:    # cited inline by EO number
        hit = True
    print(f'  {"OK " if hit else "!! "} {head} {ry}')
    if not hit: uncited.append((head, ry))

print('\n=== SUMMARY ===')
print('orphan citations (cited, no reference):', orphans if orphans else 'NONE')
print('uncited references (listed, never cited):', uncited if uncited else 'NONE')
print('references total:', len(refs))
sys.exit(1 if (orphans or uncited) else 0)
