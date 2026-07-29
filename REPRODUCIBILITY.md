# Reproducibility backtest

Two independent, re-runnable layers verify that the first paper
(`AI_demand_planning_OOS_benchmark.*`) is reproducible and internally consistent.
Both passed.

## Revision 2026-06-09: validity audit corrections (numbers changed deliberately)
An adversarial validity audit (beyond reproducibility) found and fixed two issues; all
results, figures and manuscript text were regenerated and both layers re-passed afterwards:
1. **OR2 same-week price leak.** Online Retail II prices are transacted prices that exist
   only in weeks with a sale; the original same-week price feature perfectly identified sale
   weeks (P(y>0 | price ≠ series median) = 1.0, 23% of LightGBM gain) and inflated OR2
   LightGBM from mean MASE 0.943 (honest) to 0.867 (leaky). Fixed in `lib.add_ml_features`
   (strictly lagged, forward-filled price; expanding-median ratio; no fill at panel build).
   M5 is unaffected (posted catalogue prices are legitimately known in advance).
2. **Percentage-Best tie-splitting.** On sparse series many methods forecast exactly zero
   and tie at minimum error (96–98% of series in OR2's zero deciles); argmin had assigned
   ties to the first column (Naive). PB now splits ties fractionally (1/k each).
3. **Table 5 ⟷ Table 3 alignment.** The robustness sweep originally used a looser
   eligibility filter than the primary analysis, so identical splits showed different mean
   MASE across tables. `06_robustness` now applies the same per-split filter (finite
   positive scale, ≥2 non-zero training weeks) and, at the primary split, scores the saved
   `04` predictions. The primary rows of Table 5 now equal Table 3 by construction.
Also documented: the OR2 8-week robustness LightGBM cell is an early-stopping underfit
caused by the validation band landing on the pre-Christmas surge (57 trees), reported,
with its median, in §5.5 as an operational-fragility finding.

## Layer 1: manuscript ⟷ results consistency  (`code/repro_backtest.py`)
Extracts **every** hardcoded value from the manuscript's Tables 1–6 (directly from
`manuscript_content.blocks()`) plus key inline claims, and checks each **exactly**
(zero tolerance) against the computed result files:
`m5/or2_overall.csv`, `*_inversion.csv`, `*_by_class.csv`, `*_robustness.csv`,
`*_fingerprint.json`, `*_neural_summary.json`.

**Result (post-revision): 182 checks, ALL CONSISTENT.** No number in the paper is
unsupported by the computed results. Key inline needles are computed from the result CSVs
at check time, so the gate cannot pass on stale strings. The gate also covers Table 7
(MCB mean ranks and critical distances) against `results/mcb.json`, produced by
`code/mcb_analysis.py` (Koning et al. 2005-style MCB/Nemenyi analysis), and Table 8
(RMSSE sensitivity, the M5 competition's squared-error metric) against
`results/rmsse.json`, produced by `code/rmsse_analysis.py`. Current total: 208 checks.

**Layer 2 (post-revision):** snapshot → re-run `04 (or2)` + `05` → compare:
**23/23 files bit-for-bit identical** for the corrected pipeline.

## Layer 2: the pipeline regenerates the results  (`code/_repro_diff.py`)
`snapshot → re-run → compare` (bit-for-bit numeric diff). Verified end-to-end from the
**raw public data**:

| Stage | Re-run | Result |
|---|---|---|
| `01_*` weekly panel build (from raw M5 + UCI Online Retail II) | yes | **identical** (max\|diff\| = 0; M5 6,838,696×8, OR2 419,814×6) |
| `02_classify` + `03_classical` + `05_aggregate` | yes | **23 files identical** (bit-for-bit) |
| `04_lgbm_global` (LightGBM, default seed, fixed thread count) | yes | **identical** on re-run (empirically bit-reproducible on this config) |
| `10_neural_baselines` OR2 (NHITS + DeepAR) | yes | **identical**, re-ran to exactly 0.723 / 0.755 (\|diff\| = 0.0000) |

→ The full chain **raw data → panels → classification → classical → LightGBM → neural →
aggregates is bit-for-bit reproducible**, and the manuscript matches it exactly.

**Render fidelity (`code/_repro_extra.py`):** the *built* `.md` and `.tex` carry the exact
result numbers (0.952, 0.867, 1.145, 0.986, 1.000 all present in both). Source ⟶ rendered
output is faithful, not just the in-memory content.

## Stage notes (verified, not silently assumed)
- **`06_robustness` (Table 5):** re-run in full (six M5/OR2 LightGBM fits + classical, ~12 min,
  completed within the box's CPU-kill window). OR2 **bit-identical**; M5 reproduces to
  **max\|diff\| = 2.66e-15**, floating-point machine epsilon from non-associative summation in
  the multithreaded LightGBM reduction, ~12 orders of magnitude below the manuscript's 3-decimal
  rounding. Every rounded Table 5 value is therefore exactly reproducible (Layer 1 re-confirmed).
- **`10_neural_baselines` (Table 6, NHITS/DeepAR):** seeded (neuralforecast default) and run
  single-threaded (`OMP/MKL=1`, `torch.set_num_threads(1)`). Empirically re-ran **bit-identical**
  on OR2 (NHITS 0.723, DeepAR 0.755, \|diff\| = 0.0000), i.e. deterministic on this config. The
  single-thread pin removes the usual CPU-training nondeterminism. (Other hardware/thread counts
  may differ slightly; ranking is stable regardless.) Table 6 is also **generated dynamically**
  from each run's `*_neural_summary.json`, so the manuscript always reflects the computed numbers.
- **Foundation models (TimesFM / Chronos):** zero-shot inference; the recovered TimesFM
  OR2 run reproduced its documented 0.762 mean MASE.

## Environment constraint
This machine silently kills CPU jobs running longer than ~12 minutes. Heavy stages are
sized/seeded to finish within that window (M5 LightGBM ≈ 4 min; neural single-threaded).
Only the `06` robustness sweep (6 LightGBM fits in one process) can approach the limit,
run it once and let it complete.

## How to reproduce
```powershell
cd code
python repro_backtest.py                 # Layer 1: 166 consistency checks
python _repro_diff.py snapshot           # Layer 2: capture current results
python 02_classify.py; python 03_classical.py; python 04_lgbm_global.py; python 05_aggregate.py
python _repro_diff.py compare            # -> "ALL IDENTICAL (bit-for-bit numeric match)"
```
All pipeline scripts use `__file__`-relative paths, so they run correctly regardless of
where the project folder is moved or renamed.
