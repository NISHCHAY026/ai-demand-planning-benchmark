import os, time, numpy as np
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
for v in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[v] = '8'
import timesfm

t = time.time()
tfm = timesfm.TimesFm(
    hparams=timesfm.TimesFmHparams(
        backend='cpu', per_core_batch_size=256,
        horizon_len=8, context_len=512,
    ),
    checkpoint=timesfm.TimesFmCheckpoint(
        huggingface_repo_id='google/timesfm-1.0-200m-pytorch'),
)
print('loaded timesfm-1.0-200m in %.1fs' % (time.time() - t))

# batched 1-step throughput
B = 256
rng = np.random.RandomState(0)
inputs = [rng.poisson(3, size=60).astype(np.float32) for _ in range(B)]
freq = [0] * B
t = time.time()
pf, _ = tfm.forecast(inputs, freq=freq)
dt = time.time() - t
pf = np.asarray(pf)
print('forecast OK  point.shape', pf.shape, '  step1[0..3]=', np.round(pf[:4, 0], 3))
print('batch B=%d horizon-call %.2fs  (%.0f series/s for a full forecast call)' % (B, dt, B/dt))
