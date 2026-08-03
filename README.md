# The conditional value of AI in supply-chain demand planning
### A reproducible out-of-sample benchmark on two public retail datasets

End-to-end, **public-data-only** study comparing classical statistical forecasters, a global
gradient-boosted model (LightGBM, the M5-winning class), and two deep neural forecasters
(NHITS, DeepAR) for retail demand planning across the full intermittency spectrum.

## Headline findings
1. **In-sample selection inverts out-of-sample.** The forecaster that looks best on the
   history used to fit it is not the one that generalises. On Online Retail II, SBA wins
   47% of series in-sample yet is beaten by a naïve random walk out-of-sample.
2. **AI value is real but depends on the kind of AI and the data.** Global LightGBM is
   decisively best on the dense M5 panel (mean MASE 0.952, 44% Percentage-Best). On the sparse
   Online Retail II panel, with price features restricted to strictly past information, it
   records 0.943 and is **beaten by tuned SES (0.876) and SMA (0.907)**; the deep global models
   (NHITS 0.723, DeepAR 0.755 on the eligible subset) are the strongest methods there.
3. **A silent target leak, documented and fixed.** A same-week transacted-price feature
   perfectly identifies sale weeks in transactional data (P(y>0 | price ≠ series median) = 1.0)
   and inflated the GBM's apparent OR2 accuracy from 0.943 to 0.867, enough to flip its
   ranking against every classical method. All results use the corrected, strictly-lagged
   price specification; the episode is reported in §5.6 as a caution for AI benchmarking.
4. **That value is conditional on demand regime and data sufficiency.** On the sparse
   intermittent tail the zero-forecasting simple methods jointly take 61–65% of wins
   (Percentage-Best uses fractional tie-splitting) and, by MAE-based scoring, **no method
   beats the naïve benchmark**, and the most complex (neural) models cannot even be applied
   there.
5. **The metric matters as much as the method (RMSSE sensitivity).** Under the M5
   competition's squared-error RMSSE the substantive leaders are unchanged (LightGBM on M5,
   SES on OR2), but the naive benchmark, winner of the most MAE ties, is the **worst**
   method in all eight demand classes, and Croston/SBA recover materially: their poor MASE
   showing is partly a property of median-rewarding metrics, exactly as their proponents
   argue. Method *and metric* must match the decision.

## Datasets (both public, downloaded by the code)
- **M5** (Walmart store–SKU daily sales) via `datasetsforecast`. 30,490 series.
- **UCI Online Retail II** (ID 502), UK online retailer 2009–2011. 4,707 product series.

## Pipeline (`code/`, run in order)
| Script | Purpose |
|---|---|
| `01_build_m5_weekly.py`  | M5 daily → weekly panel + price/SNAP/event features |
| `01_build_or2_weekly.py` | Online Retail II invoices → weekly demand panel (cleaned) |
| `02_classify.py`         | SBC demand classification (ADI/CV²) + demand fingerprint |
| `03_classical.py`        | Naive/SMA/SES/Croston/SBA, in-sample & rolling-origin OOS |
| `04_lgbm_global.py`      | Global LightGBM (Tweedie) forecaster, OOS |
| `05_aggregate.py`        | Inversion, overall accuracy, by-class & by-volume tables |
| `06_robustness.py`       | Ranking stability across hold-out horizons |
| `07_figures.py`          | Six publication figures |
| `10_neural_baselines.py` | Global NHITS + DeepAR (neuralforecast), same OOS protocol |
| `22_leadtime.py`         | Horizon sensitivity: classical methods re-scored on cumulative L-week demand (§5.10, Table 9) |
| `18_foundation_models.py`| Zero-shot Chronos-Bolt inference, same OOS protocol |
| `20_timesfm.py`          | Zero-shot TimesFM inference (separate environment) |
| `mcb_analysis.py`        | Multiple-comparisons-with-the-best (Nemenyi) ranks |
| `rmsse_analysis.py`      | Squared-error RMSSE sensitivity |
| `lib.py`                 | Shared vectorised forecasters, metrics, ML feature builder |

## Getting the data

Neither dataset is committed to this repository. `data/` is gitignored: the two files total over
2 GB, and neither is ours to redistribute. Fetch both before running anything.

**M5** downloads itself. `01_build_m5_weekly.py` calls `M5.load()` from `datasetsforecast`, which
pulls the competition files into `data/m5/` on first run. Nothing to do by hand.

**Online Retail II** has to be fetched manually. Download the archive from the UCI Machine Learning
Repository (dataset ID 502, https://archive.ics.uci.edu/dataset/502/online+retail+ii), unzip it, and
put `online_retail_II.xlsx` directly in `data/`. `01_build_or2_weekly.py` reads that path and does
not download anything, so it fails with a missing-file error if you skip this.

```powershell
# after downloading and unzipping from UCI:
#   data\online_retail_II.xlsx
```

Expect roughly 2.2 GB in `data/` once both are in place.

## Reproduce
```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd code
python 01_build_m5_weekly.py ; python 01_build_or2_weekly.py
python 02_classify.py ; python 03_classical.py ; python 04_lgbm_global.py
python 05_aggregate.py ; python 06_robustness.py
python 10_neural_baselines.py or2 ; python 10_neural_baselines.py m5
python 22_leadtime.py ; python 07_figures.py
python mcb_analysis.py ; python rmsse_analysis.py
```

## Scope: what this repository contains

This repository holds the analysis pipeline and its outputs: the code that builds the weekly
panels, classifies demand, fits every forecaster, runs the evaluation, and writes the result
tables and figures. Everything in `results/` regenerates from `code/` and the two public
datasets.

The manuscript itself is not included. The paper is under peer review, the review is
double-blind, and the paper will be released when it is published. Until then the numbers
backing it are all here in `results/` and can be recomputed independently.

`results/` holds every CSV and JSON result table. `results/figures/` holds the seven figures.

## Integrity
- **Numbers:** every table/figure value is produced by the scripts from the public data; the
  manuscript's dynamic neural table (Table 6) is read directly from `results/*_neural_summary.json`.

## Method notes
- Weekly planning bucket; each series runs from its first sale to window end (no pre-launch zeros).
- One-step-ahead rolling origin; classical params fit on training only; LightGBM and neural models
  use early stopping / fixed step budget on a pre-test validation band. Because the horizon is one
  step, every lag/feature is an actual past observation → all methods see the **same information set**.
- Neural models require an input window, so they are scored on series with adequate history; on that
  same subset every method is re-scored for an apples-to-apples comparison (Table 6).
- MASE (scale-free) is the primary metric; Percentage-Best counts each series once.
- This machine has no LaTeX/Office installed, so PDFs are rendered directly via reportlab; the `.tex`
  is verified structurally (balanced environments, no stray Unicode) and compiles with pdflatex.
