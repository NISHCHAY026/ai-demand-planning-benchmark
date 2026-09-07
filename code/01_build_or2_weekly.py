"""
01_build_or2_weekly.py
Construct a weekly SKU-level demand panel from the UCI Online Retail II dataset
(a real UK online retailer, Dec-2009 to Dec-2011). Invoices are cleaned of
cancellations, returns and non-product service codes, then aggregated to weekly
units sold per StockCode -- a genuine retail demand-planning series. Only weeks the
transaction window covers end to end are kept, so a short first or last bucket cannot be
read as a fall in demand.

Output: public_study/data/or2_weekly.parquet (long: unique_id, week_idx, y, sell_price, woy, month)
        public_study/data/or2_static.parquet  (unique_id -> country, price band, description)
"""
import os, re, numpy as np, pandas as pd

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
print('Reading Online Retail II (both sheets)...')
xls = pd.ExcelFile(DATA + r'\online_retail_II.xlsx')
raw = pd.concat([pd.read_excel(xls, sheet_name=s) for s in xls.sheet_names], ignore_index=True)
print('Raw rows:', len(raw))

raw.columns = [c.strip() for c in raw.columns]
raw['Invoice']   = raw['Invoice'].astype(str)
raw['StockCode'] = raw['StockCode'].astype(str).str.strip().str.upper()

# --- clean ---
n0 = len(raw)
raw = raw[~raw['Invoice'].str.startswith('C')]                 # drop cancellations
raw = raw[raw['Quantity'] > 0]                                 # drop returns/zeros
raw = raw[raw['Price'] > 0]                                    # drop zero-price lines
# keep genuine product codes: 5+ leading digits (e.g. 85048, 79323P); drop POST,DOT,D,M,BANK CHARGES,...
is_product = raw['StockCode'].str.match(r'^\d{5}')
raw = raw[is_product]
print(f'After cleaning: {len(raw)} rows (dropped {n0-len(raw)}) | distinct StockCodes: {raw["StockCode"].nunique()}')

# --- weekly buckets (Monday-anchored) ---
raw['InvoiceDate'] = pd.to_datetime(raw['InvoiceDate'])
d0 = raw['InvoiceDate'].dt.normalize().min()
d0 = d0 - pd.Timedelta(days=d0.weekday())                      # back up to Monday
raw['week_idx'] = ((raw['InvoiceDate'].dt.normalize() - d0).dt.days // 7).astype('int16')

# Keep only weekly buckets the observed data covers END TO END. The transaction window
# starts on a Tuesday and stops on a Friday, so the first bucket is missing its Monday and
# the last is missing its Sunday -- respectively about 18% and 9% of a typical week's units,
# since this retailer trades Monday to Friday plus Sunday and is effectively closed on
# Saturdays. A partially covered bucket is a smaller week, not a weaker demand week, and in
# the hold-out window that difference is charged to the forecaster. The same completeness
# rule is applied to M5, whose calendar ends two days into its final week.
_dmin = raw['InvoiceDate'].dt.normalize().min()
_dmax = raw['InvoiceDate'].dt.normalize().max()
_w = np.arange(int(raw['week_idx'].max()) + 1)
_starts = d0 + pd.to_timedelta(_w * 7, unit='D')
_complete = _w[(_starts >= _dmin) & (_starts + pd.Timedelta(days=6) <= _dmax)]
_dropped = sorted(set(_w) - set(_complete))
if _dropped:
    print(f'Dropping {len(_dropped)} partially covered week(s) at the span edges: '
          + ', '.join(f'{int(w)} ({(d0 + pd.Timedelta(days=int(w)*7)).date()})' for w in _dropped))
    raw = raw[raw['week_idx'].isin(_complete)].copy()
    d0 = d0 + pd.Timedelta(days=int(_complete[0]) * 7)          # re-anchor to the first kept week
    raw['week_idx'] = (raw['week_idx'] - int(_complete[0])).astype('int16')
W = int(raw['week_idx'].max()) + 1
print('Weeks in window:', W, '| span', d0.date(), '->', raw['InvoiceDate'].max().date())

wk = (raw.groupby(['StockCode','week_idx'])
         .agg(y=('Quantity','sum'), sell_price=('Price','mean')).reset_index())
wk['y'] = wk['y'].astype('float32')
wk = wk.rename(columns={'StockCode':'unique_id'})

# seasonality features per week
woy = (d0 + pd.to_timedelta(np.arange(W)*7, unit='D'))
seas = pd.DataFrame({'week_idx': np.arange(W, dtype='int16'),
                     'woy': (pd.DatetimeIndex(woy).isocalendar().week.values % 52).astype('int16'),
                     'month': pd.DatetimeIndex(woy).month.astype('int8')})

# --- reindex each series from first active week to global end; zero-fill ---
uids = np.sort(wk['unique_id'].unique())
first_active = wk.loc[wk['y'] > 0].groupby('unique_id')['week_idx'].min().astype('int16')
grid = pd.MultiIndex.from_product([uids, np.arange(W, dtype='int16')],
                                  names=['unique_id','week_idx']).to_frame(index=False)
grid['week_idx'] = grid['week_idx'].astype('int16')
panel = grid.merge(wk, on=['unique_id','week_idx'], how='left')
fa = panel['unique_id'].map(first_active).values
keep = np.isfinite(fa) & (panel['week_idx'].values >= np.nan_to_num(fa, nan=1e9))
panel = panel.loc[keep].copy()
panel['y'] = panel['y'].fillna(0.0).astype('float32')
# sell_price stays NaN in weeks with no transaction: OR2 prices are transacted prices, so
# any fill derived from the series (e.g. its median) would let a model detect sale weeks
# (and a full-window median additionally looks ahead). Downstream features must lag price.
panel['sell_price'] = panel['sell_price'].astype('float32')
panel = panel.merge(seas, on='week_idx', how='left')
panel = panel.sort_values(['unique_id','week_idx']).reset_index(drop=True)
print('Final panel rows:', len(panel), '| series:', panel['unique_id'].nunique())

# static attributes
desc = (raw.sort_values('InvoiceDate').groupby('StockCode')['Description'].last())
ctry = (raw.groupby('StockCode')['Country'].agg(lambda s: s.value_counts().index[0]))
pmed = raw.groupby('StockCode')['Price'].median()
static = pd.DataFrame({'unique_id': uids})
static['description'] = static['unique_id'].map(desc)
static['country']     = static['unique_id'].map(ctry)
static['price_med']   = static['unique_id'].map(pmed).astype('float32')

panel.to_parquet(DATA + r'\or2_weekly.parquet', index=False)
static.to_parquet(DATA + r'\or2_static.parquet', index=False)
print('Saved or2_weekly.parquet + or2_static.parquet')
print('Weeks per series (describe):'); print(panel.groupby('unique_id').size().describe())
