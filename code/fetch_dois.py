import os
"""
18_fetch_dois.py -- look up each reference's DOI from the Crossref REST API and verify
the match by year (and a fuzzy title check). Prints a key->DOI mapping for review.
Crossref returns authoritative DOIs, so nothing here is guessed.
"""
import json, urllib.request, urllib.parse, difflib, time

UA = 'PublicStudyRefCheck/1.0 (mailto:research@example.com)'

# (key, title, first-author surname, year)  -- conference items w/o Crossref DOIs flagged
REFS = [
 ('bacchetti', 'Spare parts classification and demand forecasting for stock control investigating the gap between research and practice', 'Bacchetti', 2012),
 ('babai', 'Intermittent demand forecasting an empirical study on accuracy and the risk of obsolescence', 'Babai', 2014),
 ('bojer', 'Kaggle forecasting competitions an overlooked learning opportunity', 'Bojer', 2021),
 ('challu', 'NHITS Neural Hierarchical Interpolation for Time Series Forecasting', 'Challu', 2023),
 ('chen', 'XGBoost A Scalable Tree Boosting System', 'Chen', 2016),
 ('croston', 'Forecasting and stock control for intermittent demands', 'Croston', 1972),
 ('friedman', 'Greedy function approximation a gradient boosting machine', 'Friedman', 2001),
 ('hewamalage', 'Recurrent neural networks for time series forecasting current status and future directions', 'Hewamalage', 2021),
 ('hyndman', 'Another look at measures of forecast accuracy', 'Hyndman', 2006),
 ('januschowski', 'Criteria for classifying forecasting methods', 'Januschowski', 2020),
 ('ke', 'LightGBM A Highly Efficient Gradient Boosting Decision Tree', 'Ke', 2017),
 ('kolassa', 'Evaluating predictive count data distributions in retail sales forecasting', 'Kolassa', 2016),
 ('kourentzes13', 'Intermittent demand forecasts with neural networks', 'Kourentzes', 2013),
 ('kourentzes14', 'Improving forecasting by estimating time series structural components across multiple frequencies', 'Kourentzes', 2014),
 ('lim', 'Temporal fusion transformers for interpretable multi-horizon time series forecasting', 'Lim', 2021),
 ('m4', 'The M4 Competition 100000 time series and 61 forecasting methods', 'Makridakis', 2020),
 ('m5', 'M5 accuracy competition results findings and conclusions', 'Makridakis', 2022),
 ('montero', 'Principles and algorithms for forecasting groups of time series locality and globality', 'Montero-Manso', 2021),
 ('adida', 'An aggregate disaggregate intermittent demand approach ADIDA to forecasting an empirical proposition and analysis', 'Nikolopoulos', 2011),
 ('nbeats', 'N-BEATS Neural basis expansion analysis for interpretable time series forecasting', 'Oreshkin', 2020),
 ('horses', 'Horses for courses in demand forecasting', 'Petropoulos', 2014),
 ('fap', 'Forecasting theory and practice', 'Petropoulos', 2022),
 ('pince', 'Intermittent demand forecasting for spare parts a critical review', 'Pin', 2021),
 ('deepar', 'DeepAR Probabilistic forecasting with autoregressive recurrent networks', 'Salinas', 2020),
 ('smyl', 'A hybrid method of exponential smoothing and recurrent neural networks for time series forecasting', 'Smyl', 2020),
 ('syn16', 'Supply chain forecasting theory practice their gap and the future', 'Syntetos', 2016),
 ('sb01', 'On the bias of intermittent demand estimates', 'Syntetos', 2001),
 ('sb05', 'The accuracy of intermittent demand estimates', 'Syntetos', 2005),
 ('sbc05', 'On the categorization of demand patterns', 'Syntetos', 2005),
 ('tashman', 'Out-of-sample tests of forecasting accuracy an analysis and review', 'Tashman', 2000),
 ('td09', 'Forecasting intermittent demand a comparative study', 'Teunter', 2009),
 ('tsb11', 'Intermittent demand linking forecasting to inventory obsolescence', 'Teunter', 2011),
 ('wallstrom', 'Evaluation of forecasting error measurements and techniques for intermittent demand', 'Wallstrom', 2010),
 ('willemain', 'A new approach to forecasting intermittent demand for service parts inventories', 'Willemain', 2004),
]

def crossref(title, author, year):
    q = urllib.parse.urlencode({'query.bibliographic': f'{title} {author}', 'rows': 3})
    url = f'https://api.crossref.org/works?{q}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    best = None
    for it in data['message']['items']:
        t = (it.get('title') or [''])[0]
        yr = None
        for k in ('published-print', 'published-online', 'issued', 'published'):
            if it.get(k, {}).get('date-parts'):
                yr = it[k]['date-parts'][0][0]; break
        sim = difflib.SequenceMatcher(None, title.lower(), t.lower()).ratio()
        cand = {'doi': it.get('DOI'), 'title': t, 'year': yr, 'sim': round(sim, 2)}
        if best is None or sim > best['sim']:
            best = cand
    return best

out = {}
for key, title, author, year in REFS:
    try:
        b = crossref(title, author, year)
        ok = b and b['sim'] >= 0.6 and (b['year'] in (year, year - 1, year + 1) if b['year'] else False)
        flag = 'OK ' if ok else '?? '
        out[key] = b['doi'] if ok else None
        print(f"{flag}{key:12s} {str(b['doi']):42s} yr={b['year']} sim={b['sim']}  | {b['title'][:50]}")
    except Exception as e:
        out[key] = None
        print(f"ERR {key:12s} {repr(e)[:60]}")
    time.sleep(0.2)

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'dois.json'), 'w') as f:
    json.dump(out, f, indent=2)
print('\nSaved dois.json (', sum(1 for v in out.values() if v), 'of', len(REFS), 'resolved )')
