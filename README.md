# Evaluation design decides the winner
### Horizon, leakage and metric effects in intermittent demand forecasting

A reproducible out-of-sample benchmark on two public retail datasets.

End-to-end, **public-data-only** study comparing eight classical forecasters, a global
gradient-boosted model (LightGBM, the M5-winning class), two deep neural forecasters
(NHITS, DeepAR) and two pretrained zero-shot models (Chronos-Bolt, TimesFM) for retail demand
planning across the full intermittency spectrum.

The finding the title refers to: four individually defensible choices about *how the
comparison is run*, rather than about the methods, each move the ranking on the same data.

## Headline findings
1. **The evaluation horizon reverses the Croston ranking.** Scored one step ahead, Croston is
   last of the eight classical methods on M5. Re-scored on cumulated lead-time demand, which is
   the quantity an inventory system actually consumes, it is first at 26 weeks, its error
   against a naive benchmark falling from 1.005 to 0.568. On the sparse panel it stays last at
   every lead time, so evaluation design and demand regime interact.
2. **A silent target leak, documented and fixed.** A same-week transacted-price feature
   identifies sale weeks by its mere presence in transactional data, where price exists only in
   weeks with a sale. The two price variables carried **42%** of the model's gain and ranked
   first and second of twenty-one features, inflating apparent accuracy from mean MASE 0.868 to
   0.678. All results use the corrected, strictly-lagged specification; the discarded one is
   kept behind `04_lgbm_global.py --leaked` so the counterfactual regenerates.
3. **The error metric reverses the benchmark's standing.** MASE and RMSSE agree on the winner
   (LightGBM on M5 at 0.936, SES on Online Retail II at 0.835) but not on the ordering behind
   it: the naive forecast wins more series than any method but one on the sparse panel under
   MASE, and has the worst mean RMSSE on both (1.001 and 0.800).
4. **In-sample selection inverts out-of-sample.** On Online Retail II, SBA wins 39.4% of series
   in-sample yet records mean MASE 1.088 out of sample, worse than a naive random walk (0.957).
   On M5 the in-sample champion, ADIDA, keeps a good mean error but loses two thirds of its
   win rate.
5. **Machine-learning value is conditional on the demand regime, and on which kind.**
   Cross-sectional gradient boosting leads the dense panel (0.936) but finishes behind five
   classical methods on the sparse one (0.868 against SES 0.835). The deep global models post
   the study's largest margins on the sparse tail, 27% over the best simple method on the
   intermittent class, but only on series long enough to admit them.
6. **Two pretrained models that need no per-series history still lose to trained ones** in
   every sparse demand class on both panels, so what bounds accuracy there is data sufficiency
   and not model class.

## Datasets (both public, downloaded by the code)
- **M5** (Walmart store–SKU daily sales) via `datasetsforecast`. 30,490 series.
- **UCI Online Retail II** (ID 502), UK online retailer 2009–2011. 4,675 product series.

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
| `26_foundation_analysis.py` | Zero-shot models against trained ones; the data-sufficiency test (§5.11, Table 10) |
| `27_managerial_table.py` | Method selection by demand class, mean MASE against Percentage-Best (§6.1, Table 11) |
| `28_probabilistic.py`    | Distributional evaluation: scaled pinball and coverage on the sparse panel (§5.12, Table 12) |
| `29_gap_ci.py`           | Paired bootstrap intervals on the zero-shot minus trained gaps (§5.9, Table 10) |
| `31_timesfm_quantile_probe.py` | Probes the TimesFM quantile grid, evidence for the ceiling claim (§5.12) |
| `35_classification_sensitivity.py` | What the full-span SBC convention does to the by-class results (§5.4) |
| `36_grid_sensitivity.py` | Whether the narrow tuning grid handicaps the classical arm (§5.13) |
| `mcb_analysis.py`        | Nemenyi ranks, including the product-clustered critical distance (§5.10) |
| `rmsse_analysis.py`      | Squared-error RMSSE sensitivity |
| `lib.py`                 | Shared vectorised forecasters, metrics, tuning grids, ML feature builder |
| **Manuscript build** | |
| `manuscript_content.py`  | Single source of truth for every table, figure caption and paragraph |
| `30_sync_tables.py`      | Rewrites all eleven table bodies from `results/`, so numbers are a build product |
| `08`,`11`,`13`,`14`,`23`,`24` | Render docx, PDF, LaTeX, Markdown, pandoc and arXiv bundles |
| **Verification** | |
| `repro_backtest.py`      | Re-reads every table cell and inline claim against the result files |
| `12_check_citations.py`  | Orphan and uncited-reference check |
| `32_provenance.py`       | Per-function `lib.py` hashes for each result file, so staleness is checkable |
| `33_prose_scan.py`       | Flags numbers that appear in prose but in no result file |
| `34_refresh_class_labels.py` | Re-stamps SBC labels on stored model outputs after a re-classification |

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
python 18_foundation_models.py ; python 20_timesfm.py m5   # zero-shot, separate envs
python 26_foundation_analysis.py ; python 27_managerial_table.py
```

## Scope: what this repository contains

This repository holds the analysis pipeline and its outputs: the code that builds the weekly
panels, classifies demand, fits every forecaster, runs the evaluation, and writes the result
tables and figures. Everything in `results/` regenerates from `code/` and the two public
datasets.

The manuscript ships with it, as a single current copy at
`manuscript/AI_demand_planning_OOS_benchmark.pdf`. It regenerates from `manuscript_content.py`
and the builders listed above, so the PDF here and the numbers in `results/` are the same
artefact seen two ways. There is deliberately one copy and not a version history: the paper is
rebuilt in place whenever a result changes.

`results/` holds every CSV and JSON result table. `results/figures/` holds the seven figures.

## Integrity
- **Numbers:** every table/figure value is produced by the scripts from the public data; the
  manuscript's dynamic neural table (Table 6) is read directly from `results/*_neural_summary.json`.

## Method notes
- Weekly planning bucket; each series runs from its first sale to window end (no pre-launch zeros).
- One-step-ahead rolling origin; classical params fit on training only; LightGBM and neural models
  use early stopping or a fixed step budget on a pre-test validation band. Because the horizon is one
  step, every lag and rolling feature is an actual past observation, so no method sees a value the
  others could not have seen at that origin. The feature sets are not identical: the global model
  additionally reads price and, on M5, the SNAP and event calendars, and it fits on a slightly
  shorter history because of its early-stopping band. What is held identical is the origin.
- Neural models require an input window, so they are scored on series with adequate history; on that
  same subset every method is re-scored for an apples-to-apples comparison (Table 6).
- MASE (scale-free) is the primary metric; Percentage-Best counts each series once.
- This machine has no LaTeX/Office installed, so PDFs are rendered directly via reportlab; the `.tex`
  is verified structurally (balanced environments, no stray Unicode) and compiles with pdflatex.
