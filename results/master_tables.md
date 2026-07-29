# Master cross-method comparison (real runs)

One-step rolling-origin out-of-sample MASE; identical series across all methods (scored by every available method). Lower is better; **bold** = best in column.


## Overall — mean (median) MASE

| Method | M5 (Walmart) (n=29574) | Online Retail II (n=4133) |
|---|---|---|
| Naive | 1.197 (1.019) | 0.938 (0.374) |
| SMA | 1.062 (0.885) | 0.872 (0.357) |
| SES | 1.031 (0.857) | 0.836 (0.402) |
| Croston | 1.215 (0.902) | 1.141 (0.770) |
| SBA | 1.205 (0.899) | 1.109 (0.742) |
| LightGBM | **0.983 (0.821)** | 0.911 (0.500) |
| NHITS | 0.989 (0.826) | **0.723 (0.275)** |
| DeepAR | 1.007 (0.833) | 0.755 (0.277) |
| Chronos-Bolt-Small (48M) | 1.018 (0.839) | 0.744 (0.281) |
| Chronos-Bolt-Base (205M) | — | 0.735 (0.285) |
| TimesFM-200M | — | 0.762 (0.309) |

## M5 (Walmart) — mean MASE by regime

| Method | Smooth (n=15408) | Erratic (n=1911) | Intermittent (n=9829) | Lumpy (n=2426) |
|---|---|---|---|---|
| Naive | 1.017 | 0.938 | 1.422 | 1.631 |
| SMA | 0.882 | 0.861 | 1.273 | 1.507 |
| SES | 0.857 | 0.838 | 1.230 | 1.478 |
| Croston | 0.914 | 0.908 | 1.599 | 1.812 |
| SBA | 0.917 | 0.899 | 1.573 | 1.784 |
| LightGBM | 0.811 | 0.790 | 1.184 | 1.413 |
| NHITS | 0.829 | 0.798 | 1.174 | 1.402 |
| DeepAR | 0.834 | 0.810 | 1.211 | 1.432 |
| Chronos-Bolt-Small (48M) | 0.845 | 0.803 | 1.221 | 1.458 |

## Online Retail II — mean MASE by regime

| Method | Smooth (n=93) | Erratic (n=1016) | Intermittent (n=560) | Lumpy (n=2464) |
|---|---|---|---|---|
| Naive | 0.948 | 1.043 | 0.646 | 0.961 |
| SMA | 0.814 | 0.917 | 0.584 | 0.921 |
| SES | 0.765 | 0.860 | 0.572 | 0.888 |
| Croston | 0.779 | 0.884 | 1.134 | 1.262 |
| SBA | 0.763 | 0.863 | 1.128 | 1.219 |
| LightGBM | 0.982 | 0.921 | 0.829 | 0.922 |
| NHITS | 0.797 | 0.826 | 0.403 | 0.750 |
| DeepAR | 0.765 | 0.835 | 0.400 | 0.803 |
| Chronos-Bolt-Small (48M) | 0.755 | 0.810 | 0.453 | 0.783 |
| Chronos-Bolt-Base (205M) | 0.752 | 0.811 | 0.454 | 0.768 |
| TimesFM-200M | 0.758 | 0.810 | 0.514 | 0.798 |
