# PiProject Architecture

## Overview

PiProject is a high-performance π computation and verification system.
It replaces the legacy single-file scripts with a modular Python package.

## Package Structure

```
src/piproject/
├── __init__.py       # Package metadata and verification statuses
├── compute.py        # Computation engine (Chudnovsky + binary splitting)
├── verify.py         # Independent verification engine
├── bbp.py            # BBP hexadecimal spot checks (independent algorithm)
├── cli.py            # Professional command-line interface
```

### compute.py — Computation Engine

- **Algorithm:** Chudnovsky formula with binary splitting
- **Arithmetic:** GMPY2 `mpz` (arbitrary-precision integers)
- **Output:** Truncated (not rounded) to exactly N fractional digits
- **Guard digits:** 20 guard digits absorb truncation error
- **Global state:** Does NOT mutate gmpy2 context precision on import

### verify.py — Independent Verification Engine

- Algorithmically independent of `compute.py`
- Explicit statuses: `CALCULATED`, `STRUCTURE_VALID`, `PREFIX_VERIFIED`,
  `FULLY_VERIFIED`, `INDEPENDENTLY_VERIFIED`, `VERIFICATION_FAILED`
- Never reports `FULLY_VERIFIED` based on a prefix check alone
- Supports file-to-file comparison, BBP spot checks, and SHA-256 integrity

### bbp.py — BBP Hexadecimal Spot Checks

- **Algorithm:** Bailey–Borwein–Plouffe formula
- **Independence:** Completely separate from Chudnovsky/binary splitting
- **Use case:** Arbitrary-position spot checks (not full verification)

### cli.py — Command-Line Interface

Commands: `calculate`, `verify`, `benchmark`, `inspect`, `hash`
- Progress reporting and resource estimates
- Clear error messages and exit codes
- SHA-256 fingerprints for reproducibility

## Design Principles

1. **Correctness first:** Never sacrifice accuracy for speed.
2. **Independent verification:** The verification engine does not trust the computation engine.
3. **Explicit statuses:** Verification status is always unambiguous.
4. **Reproducibility:** SHA-256 fingerprints and environment documentation.
5. **No global side effects:** Importing the package does not mutate global state.
