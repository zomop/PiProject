"""Shared fixtures for PiProject tests."""

from decimal import Decimal, getcontext
from pathlib import Path

import gmpy2
import pytest

import piproject.compute as compute
import piproject.verify as verify


@pytest.fixture
def tmp_pi_file(tmp_path: Path) -> Path:
    """Provide a writable pi output path in a temp directory."""
    return tmp_path / "pi_test.txt"


@pytest.fixture
def reference_pi_decimals():
    """Return a function that computes `digits` decimal digits of pi
    using an independent decimal/Machin implementation."""

    def _compute(digits: int) -> str:
        getcontext().prec = digits + 80

        def atan_inv(x: int) -> Decimal:
            term = Decimal(1) / Decimal(x)
            x_sq = Decimal(1) / (Decimal(x) * Decimal(x))
            total = Decimal(0)
            power = term
            k = 0
            while True:
                denom = 2 * k + 1
                t = power / denom
                if t < Decimal(10) ** (-(digits + 70)):
                    break
                total += t if k % 2 == 0 else -t
                power *= x_sq
                k += 1
            return total

        pi = Decimal(16) * atan_inv(5) - Decimal(4) * atan_inv(239)
        s = format(pi, "f")
        if "." in s:
            _, frac = s.split(".")
        else:
            frac = ""
        return frac[:digits]

    return _compute


@pytest.fixture
def gmpy2_precision():
    """Ensure gmpy2 precision is not mutated by tests."""
    before = gmpy2.get_context().precision
    yield
    after = gmpy2.get_context().precision
    assert after == before, "gmpy2 global precision was mutated"
