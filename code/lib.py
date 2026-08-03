"""
lib.py -- shared primitives for the public-data intermittent-demand study.

Design: all classical forecasters are vectorised ACROSS series (the recursion
loops over the ~100-280 time steps and updates every series simultaneously with
numpy), which makes the full M5 panel (30k series) run in seconds per parameter.
A series is "active" from its first non-zero week to the end of the panel; cells
before first activity are np.nan and never enter training statistics, fitting, or
scoring.
"""
import numpy as np, pandas as pd

# ----------------------------------------------------------------------------- #
#  Panel -> dense matrix
# ----------------------------------------------------------------------------- #
def build_matrix(panel):
    """panel: long df [unique_id, week_idx, y, ...] -> (Y[n,T] float32 with NaN
    before first activity, uids array, first_active_col int array)."""
    uids = np.sort(panel['unique_id'].unique())
    uid_ix = {u: i for i, u in enumerate(uids)}
    T = int(panel['week_idx'].max()) + 1
    Y = np.full((len(uids), T), np.nan, dtype=np.float32)
    r = panel['unique_id'].map(uid_ix).values
    c = panel['week_idx'].values.astype(int)
    Y[r, c] = panel['y'].values.astype(np.float32)
    # first active (first non-zero) column per series
    pos = np.where(np.nan_to_num(Y, nan=0.0) > 0, np.arange(T)[None, :], T + 1)
    first_active = pos.min(axis=1).astype(int)
    # set pre-activity to NaN (already NaN where no panel row; also blank any
    # leading zeros that the panel may carry)
    col = np.arange(T)[None, :]
    Y[col < first_active[:, None]] = np.nan
    return Y, uids, first_active


# ----------------------------------------------------------------------------- #
#  SBC demand classification (Syntetos-Boylan-Croston)
# ----------------------------------------------------------------------------- #
def classify(Y, first_active):
    """ADI = active span / #non-zero;  CV2 = (std/mean)^2 of non-zero sizes."""
    n, T = Y.shape
    out = []
    for i in range(n):
        s = Y[i, first_active[i]:]
        s = s[~np.isnan(s)]
        nz = s[s > 0]
        span = len(s)
        k = len(nz)
        adi = span / k if k > 0 else np.inf
        cv2 = (nz.std() / nz.mean()) ** 2 if k >= 2 and nz.mean() > 0 else 0.0
        if adi < 1.32 and cv2 < 0.49:   cls = 'Smooth'
        elif adi >= 1.32 and cv2 < 0.49: cls = 'Intermittent'
        elif adi < 1.32 and cv2 >= 0.49: cls = 'Erratic'
        else:                            cls = 'Lumpy'
        out.append((span, k, adi, cv2, cls))
    df = pd.DataFrame(out, columns=['span', 'n_nonzero', 'ADI', 'CV2', 'class'])
    return df


# ----------------------------------------------------------------------------- #
#  Vectorised one-step-ahead forecasters.  Each returns F[n,T]: the forecast for
#  column t made from information up to t-1.  Cells before first_active are NaN.
# ----------------------------------------------------------------------------- #
def _activemask(Y, first_active):
    col = np.arange(Y.shape[1])[None, :]
    return col >= first_active[:, None]

def f_naive(Y, first_active):
    F = np.full_like(Y, np.nan)
    F[:, 1:] = Y[:, :-1]
    F[~_activemask(Y, first_active)] = np.nan
    return F

def f_sma(Y, first_active, k):
    n, T = Y.shape
    y0 = np.nan_to_num(Y, nan=0.0)
    act = _activemask(Y, first_active).astype(np.float32)
    F = np.full((n, T), np.nan, dtype=np.float32)
    for t in range(1, T):
        lo = max(0, t - k)
        w = act[:, lo:t]
        denom = w.sum(axis=1)
        num = (y0[:, lo:t] * w).sum(axis=1)
        F[:, t] = np.where(denom > 0, num / np.maximum(denom, 1), np.nan)
    F[~_activemask(Y, first_active)] = np.nan
    return F

def _warm_ses(Y, first_active, split):
    """initial level = mean of training-window active demand."""
    n, T = Y.shape
    lvl = np.zeros(n, dtype=np.float32)
    for i in range(n):
        tr = Y[i, first_active[i]:split]
        tr = tr[~np.isnan(tr)]
        lvl[i] = tr.mean() if len(tr) else 0.0
    return lvl

def f_ses(Y, first_active, alpha, split):
    n, T = Y.shape
    y0 = np.nan_to_num(Y, nan=0.0)
    L = _warm_ses(Y, first_active, split)
    F = np.full((n, T), np.nan, dtype=np.float32)
    act = _activemask(Y, first_active)
    for t in range(T):
        on = act[:, t]
        F[on, t] = L[on]
        # update level with observed y_t where active
        L = np.where(on, alpha * y0[:, t] + (1 - alpha) * L, L)
    return F

def _warm_croston(Y, first_active, split):
    """z0 = mean non-zero size in train; p0 = train span / #non-zero (>=1)."""
    n = Y.shape[0]
    z0 = np.ones(n, dtype=np.float32); p0 = np.ones(n, dtype=np.float32)
    for i in range(n):
        tr = Y[i, first_active[i]:split]
        tr = tr[~np.isnan(tr)]
        nz = tr[tr > 0]
        if len(nz):
            z0[i] = nz.mean()
            p0[i] = max(1.0, len(tr) / len(nz))
    return z0, p0

def f_croston(Y, first_active, alpha, split, sba=False):
    n, T = Y.shape
    y0 = np.nan_to_num(Y, nan=0.0)
    z, p = _warm_croston(Y, first_active, split)
    q = np.ones(n, dtype=np.float32)
    corr = (1 - alpha / 2.0) if sba else 1.0
    F = np.full((n, T), np.nan, dtype=np.float32)
    act = _activemask(Y, first_active)
    for t in range(T):
        on = act[:, t]
        F[on, t] = corr * (z[on] / np.maximum(p[on], 1e-6))
        dpos = on & (y0[:, t] > 0)
        # update size & interval on demand periods
        z = np.where(dpos, alpha * y0[:, t] + (1 - alpha) * z, z)
        p = np.where(dpos, alpha * q + (1 - alpha) * p, p)
        q = np.where(dpos, 1.0, np.where(on, q + 1.0, q))
    return F


# ----------------------------------------------------------------------------- #
#  Scoring helpers
# ----------------------------------------------------------------------------- #
def col_slices(Y, split):
    T = Y.shape[1]
    tr = np.arange(0, split); te = np.arange(split, T)
    return tr, te

def mae_over(F, Y, cols):
    d = np.abs(F[:, cols] - Y[:, cols])
    m = ~np.isnan(d)
    cnt = m.sum(axis=1)
    s = np.nansum(d, axis=1)
    return np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan), cnt

def rmse_over(F, Y, cols):
    d = (F[:, cols] - Y[:, cols]) ** 2
    cnt = (~np.isnan(d)).sum(axis=1)
    return np.sqrt(np.where(cnt > 0, np.nansum(d, axis=1) / np.maximum(cnt, 1), np.nan))

def bias_over(F, Y, cols):
    d = F[:, cols] - Y[:, cols]
    cnt = (~np.isnan(d)).sum(axis=1)
    return np.where(cnt > 0, np.nansum(d, axis=1) / np.maximum(cnt, 1), np.nan)

def naive_scale(Y, first_active, split):
    """in-sample one-step naive MAE over the training window (MASE denominator)."""
    n, T = Y.shape
    sc = np.full(n, np.nan, dtype=np.float32)
    for i in range(n):
        tr = Y[i, first_active[i]:split]
        tr = tr[~np.isnan(tr)]
        if len(tr) >= 2:
            d = np.abs(np.diff(tr))
            sc[i] = d.mean() if len(d) else np.nan
    return sc


# ----------------------------------------------------------------------------- #
#  Global ML (LightGBM) feature construction + fit/predict -- shared by the primary
#  run and the robustness sweep.
# ----------------------------------------------------------------------------- #
LAGS = [1, 2, 3, 4, 8, 13, 26, 52]

def add_ml_features(panel, static, ds):
    df = panel.sort_values(['unique_id', 'week_idx']).reset_index(drop=True)
    g = df.groupby('unique_id', observed=True)['y']
    for L in LAGS:
        df[f'lag{L}'] = g.shift(L).astype('float32')
    sh = g.shift(1)
    gb = sh.groupby(df['unique_id'], observed=True)
    df['rmean4']  = gb.rolling(4,  min_periods=1).mean().values
    df['rmean13'] = gb.rolling(13, min_periods=1).mean().values
    df['rstd4']   = gb.rolling(4,  min_periods=2).std().values
    df['rmax4']   = gb.rolling(4,  min_periods=1).max().values
    df['expmean'] = gb.expanding(min_periods=1).mean().values
    grp = df['unique_id'].values; wi = df['week_idx'].values; yv = df['y'].values
    wsl = np.empty(len(df), dtype='float32'); cur = None; lastpos = None
    for i in range(len(df)):
        if grp[i] != cur:
            cur = grp[i]; lastpos = None
        wsl[i] = (wi[i] - lastpos) if lastpos is not None else np.nan
        if yv[i] > 0: lastpos = wi[i]
    df['weeks_since_demand'] = wsl
    df['woy_sin'] = np.sin(2*np.pi*df['woy']/52).astype('float32')
    df['woy_cos'] = np.cos(2*np.pi*df['woy']/52).astype('float32')
    df['month'] = df['month'].astype('int16')
    if ds == 'm5':
        # M5 sell_price is the POSTED weekly price from the competition's price file --
        # set independently of realised sales and known in advance, so same-week use is valid.
        df['price'] = df['sell_price'].astype('float32')
        # Normalise by an EXPANDING median of prices observed up to and including t.
        # A full-sample median is computed over the whole panel, test window included,
        # so it looks across the forecast origin. The level itself may be used at t
        # because M5 prices are posted in advance, but the normaliser must not be.
        expmed = (df.groupby('unique_id', observed=True)['sell_price']
                    .expanding(min_periods=1).median().values)
        df['price_ratio'] = (df['sell_price'] / np.where(expmed > 0, expmed, np.nan)).astype('float32')
    else:
        # OR2 prices are TRANSACTED prices, observed only in weeks with a sale; a same-week
        # price (or any fill indicator) perfectly reveals y>0 (verified: P(y>0 | price !=
        # series median) = 1.0). Use only information through week t-1: lag one week,
        # forward-fill the last observed transacted price, and normalise by the expanding
        # median of those lagged prices (past-only by construction).
        gp = df.groupby('unique_id', observed=True)['sell_price']
        lagp = gp.shift(1).groupby(df['unique_id'], observed=True).ffill()
        df['price'] = lagp.astype('float32')
        expmed = lagp.groupby(df['unique_id'], observed=True).expanding(min_periods=1).median().values
        df['price_ratio'] = (df['price'] / np.where(expmed > 0, expmed, np.nan)).astype('float32')
    feats = [f'lag{L}' for L in LAGS] + ['rmean4','rmean13','rstd4','rmax4','expmean',
             'weeks_since_demand','woy_sin','woy_cos','month','price','price_ratio']
    cats = ['month']
    s = static.set_index('unique_id')
    if ds == 'm5':
        df['snap'] = df['snap'].astype('float32'); df['n_events'] = df['n_events'].astype('float32')
        feats += ['snap','n_events']
        for c in ['dept_id','cat_id','store_id','state_id']:
            df[c] = df['unique_id'].map(s[c]).astype('category'); feats.append(c); cats.append(c)
    else:
        # no static price_med: it is a full-window (test-inclusive) aggregate of transacted prices
        df['country'] = df['unique_id'].map(s['country']).astype('category')
        feats += ['country']; cats.append('country')
    for c in cats:
        if df[c].dtype.name != 'category':
            df[c] = df[c].astype('category')
    return df, feats, cats

def fit_predict_lgbm(df, feats, cats, split, val, seed=42):
    """Train a global tweedie LightGBM on weeks<split-val (early-stop on the val
    band) and return the test frame with one-step predictions for weeks>=split."""
    import lightgbm as lgb
    val0 = split - val
    tr = df[df['week_idx'] < val0]
    va = df[(df['week_idx'] >= val0) & (df['week_idx'] < split)]
    te = df[df['week_idx'] >= split].copy()
    dtr = lgb.Dataset(tr[feats], tr['y'], categorical_feature=cats, free_raw_data=False)
    dva = lgb.Dataset(va[feats], va['y'], categorical_feature=cats, reference=dtr, free_raw_data=False)
    params = dict(objective='tweedie', tweedie_variance_power=1.1, metric='mae',
                  learning_rate=0.05, num_leaves=127, min_data_in_leaf=100,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                  max_depth=-1, verbosity=-1, n_jobs=-1, seed=seed)
    model = lgb.train(params, dtr, num_boost_round=2000, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(80), lgb.log_evaluation(0)])
    te['pred'] = np.clip(model.predict(te[feats], num_iteration=model.best_iteration), 0, None)
    return te, model
