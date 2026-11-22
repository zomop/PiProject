# Algorithms

## Chudnovsky Algorithm

The primary computation engine uses the Chudnovsky formula:

```
1/pi = 12 * sum_{k=0}^{inf} (-1)^k * (6k)! * (545140134*k + 13591409) /
             ((3k)! * (k!)^3 * (640320)^(3k + 3/2))
```

Equivalently:

```
pi = 426880 * sqrt(10005) * Q / T
```

where `P`, `Q`, `T` are computed via binary splitting over the series term
ratio. Each term yields approximately 14.18 correct decimal digits.

## Binary Splitting

Binary splitting recursively divides the series range [a, b) into halves,
computing (P, Q, T) triplets for each half and combining them:

```
P = P1 * P2
Q = Q1 * Q2
T = T1 * Q2 + P1 * T2
```

This reduces the number of large-integer multiplications compared to naive
term-by-term summation.

## BBP Formula (Independent Spot Checks)

The Bailey–Borwein–Plouffe formula computes hexadecimal digits of pi at
arbitrary positions without computing preceding digits:

```
pi = sum_{k=0}^{inf} 1/16^k * (4/(8k+1) - 2/(8k+4) - 1/(8k+5) - 1/(8k+6))
```

This is algorithmically independent of Chudnovsky and is used for spot-checking
individual positions, not full digit-range verification.

## Precision Management

- Guard digits (default: 20) are computed beyond the requested count
- Truncation error is confined to the discarded guard digits
- The result is truncated (not rounded) to exactly N fractional digits
- gmpy2 global precision is never mutated
