import os
for v in ['OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENBLAS_NUM_THREADS']:
    os.environ[v] = '1'
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
import time, inspect, numpy as np, torch
torch.set_num_threads(1)
from chronos import BaseChronosPipeline

pipe = BaseChronosPipeline.from_pretrained(
    "amazon/chronos-bolt-small", device_map="cpu", dtype=torch.float32)
print("loaded. predict_quantiles sig:", str(inspect.signature(pipe.predict_quantiles)))

# single 1-step, positional inputs
ctx = torch.tensor(np.arange(1, 40, dtype=np.float32))
out = pipe.predict_quantiles(ctx, prediction_length=1, quantile_levels=[0.1, 0.5, 0.9])
print("return type:", type(out), "len:", (len(out) if isinstance(out, tuple) else 'NA'))
q, mean = out
print("q.shape", tuple(q.shape), "mean.shape", tuple(mean.shape))
print("median(0.5)=", round(float(q[0, 0, 1]), 3), "mean=", round(float(mean[0, 0]), 3))

# batched throughput: 500 series, 1-step
B = 500
batch = [torch.tensor(np.random.RandomState(i).poisson(3, size=40).astype(np.float32))
         for i in range(B)]
t = time.time()
q, mean = pipe.predict_quantiles(batch, prediction_length=1, quantile_levels=[0.5])
dt = time.time() - t
print("batch B=%d q.shape %s  %.2fs  (%.0f series/s)" % (B, tuple(q.shape), dt, B/dt))
