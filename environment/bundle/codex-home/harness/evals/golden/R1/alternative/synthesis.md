# Observed tradeoff

The target in DESIGN-OLD was 2x throughput, but BENCH-NEW measured 120 against 100:
(120−100)/100 = 20%. Latency moved in the opposite direction: p95 rose by 40%,
from 100 ms to 140 ms. Thus a lower-latency claim conflicts with this measurement.
Only one observation is available (LIMITS). The twofold goal is unsupported, and
whether every workload is faster remains unestablished. This is no human study.
