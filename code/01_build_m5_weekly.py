"""
01_build_m5_weekly.py
Aggregate the M5 (Walmart) daily SKU-store panel to a weekly planning bucket and
persist a compact panel with the M5-standard exogenous features (price, SNAP,
event calendar). Weekly is the canonical retail replenishment bucket and matches
the intermittent-demand framing of the study.

Output: public_study/data/m5_weekly.parquet  (long: unique_id, week_idx, y, + features)
        public_study/data/m5_static.parquet   (unique_id -> cat/dept/store/state)
"""
import os, numpy as np, pandas as pd
from datasetsforecast.m5 import M5

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA, exist_ok=True)

print('Loading M5 (cached)...')
Y_df, X_df, S_df = M5.load(directory=DATA + r'\m5')   # Y:[unique_id,ds,y]  X:+exog  S:static

# --- align X onto Y (same row order from loader; verify on a sample, then attach) ---
assert len(Y_df) == len(X_df)
chk = np.random.RandomState(0).randint(0, len(Y_df), 5000)
assert (Y_df['unique_id'].values[chk] == X_df['unique_id'].values[chk]).all()
assert (Y_df['ds'].values[chk] == X_df['ds'].values[chk]).all()
df = Y_df.copy()
df['sell_price'] = X_df['sell_price'].astype('float32').values
df['is_event']   = X_df['event_name_1'].notna().values.astype('int8')
snap = (X_df['snap_CA'].astype('int8').values, X_df['snap_TX'].astype('int8').values,
        X_df['snap_WI'].astype('int8').values)
del Y_df, X_df

# state per series -> pick that series' SNAP column
state = S_df.set_index('unique_id')['state_id'].astype(str)
df = df.merge(S_df[['unique_id','state_id']], on='unique_id', how='left')
st = df['state_id'].astype(str).values
df['snap'] = (snap[0]*(st=='CA') + snap[1]*(st=='TX') + snap[2]*(st=='WI')).astype('int8')
df.drop(columns=['state_id'], inplace=True)

# --- map each calendar date to the canonical M5 week (wm_yr_wk) ---
cal = pd.read_csv(DATA + r'\m5\m5\datasets\calendar.csv', usecols=['date','wm_yr_wk','month','wday'])
cal['date'] = pd.to_datetime(cal['date'])
wkmap = cal.set_index('date')['wm_yr_wk']
df['wm_yr_wk'] = df['ds'].map(wkmap).astype('int32')
# dense 0..W-1 week index in chronological order
weeks = np.sort(df['wm_yr_wk'].unique())
widx = {w:i for i,w in enumerate(weeks)}
df['week_idx'] = df['wm_yr_wk'].map(widx).astype('int16')
# week-of-year proxy for seasonality (position within a 52-week cycle)
df['woy'] = (df['week_idx'] % 52).astype('int16')
month_of_week = cal.groupby('wm_yr_wk')['month'].first()
df['month'] = df['wm_yr_wk'].map(month_of_week).astype('int8')

print('Daily rows:', len(df), '| weeks:', len(weeks))

# --- weekly aggregation per series ---
g = df.groupby(['unique_id','week_idx'], observed=True)
wk = g.agg(y=('y','sum'),
           sell_price=('sell_price','mean'),
           snap=('snap','sum'),
           n_events=('is_event','sum'),
           woy=('woy','first'),
           month=('month','first')).reset_index()
wk['y'] = wk['y'].astype('float32')
print('Weekly rows (observed weeks only):', len(wk))

# Reindex each series onto the FULL weekly grid from its first active week to the
# global last week (zero-fill gaps). Leading pre-launch weeks are dropped so that
# intermittency reflects genuine demand sparsity, not product non-existence.
# Vectorised: build the complete series x week grid, left-join, then trim leading weeks.
W = len(weeks)
uids = wk['unique_id'].cat.categories if hasattr(wk['unique_id'], 'cat') else wk['unique_id'].unique()
uids = np.asarray(uids)
first_active = (wk.loc[wk['y'] > 0].groupby('unique_id', observed=True)['week_idx'].min()).astype('int16')
price_fill = wk.groupby('unique_id', observed=True)['sell_price'].median()
seas = wk[['week_idx','woy','month']].drop_duplicates('week_idx').set_index('week_idx').sort_index()

grid = pd.MultiIndex.from_product([uids, np.arange(W, dtype='int16')],
                                  names=['unique_id','week_idx']).to_frame(index=False)
grid['week_idx'] = grid['week_idx'].astype('int16')
panel = grid.merge(wk[['unique_id','week_idx','y','sell_price','snap','n_events']],
                   on=['unique_id','week_idx'], how='left')
# trim leading pre-launch weeks (single mask: series sold at least once AND week >= first sale)
fa = panel['unique_id'].map(first_active).values
keep = np.isfinite(fa) & (panel['week_idx'].values >= np.nan_to_num(fa, nan=1e9))
panel = panel.loc[keep].copy()
panel['y'] = panel['y'].fillna(0.0).astype('float32')
panel['snap'] = panel['snap'].fillna(0).astype('int8')
panel['n_events'] = panel['n_events'].fillna(0).astype('int8')
panel['sell_price'] = panel['sell_price'].fillna(panel['unique_id'].map(price_fill)).astype('float32')
panel = panel.merge(seas, on='week_idx', how='left')
panel['woy'] = panel['woy'].astype('int16'); panel['month'] = panel['month'].astype('int8')
panel = panel.sort_values(['unique_id','week_idx']).reset_index(drop=True)
print('Final panel rows:', len(panel), '| series:', panel["unique_id"].nunique())

panel.to_parquet(DATA + r'\m5_weekly.parquet', index=False)
S_df.to_parquet(DATA + r'\m5_static.parquet', index=False)
print('Saved m5_weekly.parquet + m5_static.parquet')
print('Weeks per series (describe):')
print(panel.groupby('unique_id', observed=True).size().describe())
