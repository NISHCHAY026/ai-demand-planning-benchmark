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
| `12_check_citations.py`  | Citation-integrity audit (no orphan/uncited references) |
| `manuscript_content.py`  | **Single source of truth** for the paper content |
| `08_build_manuscript.py` | → `.docx`  | 
| `11_build_pdf.py`        | → `.pdf` (reportlab, no Office needed) |
| `13_build_latex.py`      | → `.tex` (article class; graphicx, booktabs) |
| `14_build_markdown.py`   | → `.md` (GFM) |
| `23_build_pandoc_md.py`  | → one Pandoc-ready `.md` with YAML front matter and inline LaTeX maths |
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
python 07_figures.py ; python 12_check_citations.py
python 08_build_manuscript.py
python 11_build_pdf.py ; python 13_build_latex.py ; python 14_build_markdown.py
```

## Deliverables: `manuscript/`
Everything in **four formats** (`.docx`, `.pdf`, `.tex`, `.md`) from one shared source.

**Reading copy:**
- `AI_demand_planning_OOS_benchmark.{docx,pdf,tex,md}` (full paper: 8 sections, 6 tables, 6 figures).

**IJF submission package (International Journal of Forecasting, double-blind):**
- `..._anonymized.{docx,pdf,tex,md}`: main manuscript, author identity removed (verified clean).
- `..._title_page.{docx,pdf,tex,md}`: author, affiliation, abstract, declarations (fill the e-mail placeholder).
- `IJF_cover_letter.{docx,pdf,md}`: submission cover letter.
- `overleaf_submission.zip`: all `.tex` + local `figures/` + README; drag into Overleaf, compile with pdfLaTeX.

`results/` holds all CSV/JSON result tables. `results/figures/` holds the six PNG figures.

## Integrity
- **Citations:** `12_check_citations.py` verifies every in-text citation resolves to a reference
  and every reference is cited (0 orphans, 0 uncited). Separately, all 38 references were checked
  against the Crossref REST API on 2026-07-29, comparing DOI resolution and target identity, title,
  year, container title, volume, issue, page range, and author surnames in order. 35 verified clean.
  Three carry no DOI because none exists (Ke et al. 2017 and Oreshkin et al. 2020 are NeurIPS and
  ICLR proceedings, absent from Crossref; executive orders have no DOI). None fabricated. What that
  check cannot establish is whether each in-text citation faithfully represents the cited work's
  argument, which is a separate reading task.
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
