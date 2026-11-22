# Reproducibility

## Test Environment

| Attribute | Value |
|-----------|-------|
| OS | Linux 6.1.158+ x86_64 GNU/Linux |
| Python | 3.11.2 |
| GMPY2 | 2.3.2 |
| CPU | x86_64 |

## Benchmark Results

| Digits | Best Time | Throughput |
|--------|-----------|------------|
| 1,000 | 0.1 ms | ~8.7M digits/sec |
| 10,000 | 1.7 ms | ~5.7M digits/sec |
| 100,000 | 34.8 ms | ~2.9M digits/sec |
| 1,000,000 | 627.5 ms | ~1.6M digits/sec |

Times are best of 3 runs on the test environment. Your results may vary.

## SHA-256 Fingerprints (verified)

| Digits | SHA-256 (decimal digits) |
|--------|-------------------------|
| 1,000 | 808b01bd3137f0fd50877c7ad44b2a97478666390780372803859749172292bd |
| 10,000 | 7406a2be66766f832c8d1e1b66491ef7b2f366b0393d21c4684181044b507ab5 |
| 100,000 | 5ebe8007d764bce33aba7a85a0da0924e96663fbb2e0fd089b9e8cd3be482bc2 |
| 1,000,000 | 7806ee47461b49ef1f578e14461b2c83c09c6d7a9a914275da1d71e9cbbf7069 |

These hashes were verified against two independent methods:
1. Independent decimal/Machin computation (1K, 10K, 100K digits)
2. IonicaBizau/pi-decimals reference (1M digits)

## Running Benchmarks

```bash
piproject benchmark --digits 100000 --repeats 3
```

Results are saved to `benchmarks/benchmark_<digits>.json`.
