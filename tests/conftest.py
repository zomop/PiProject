"""Shared fixtures and helpers for PiProject tests."""

from decimal import Decimal, getcontext

import pytest


@pytest.fixture
def tmp_output(tmp_path):
    """Provide a writable output path inside a temporary directory."""
    return tmp_path / "pi_test.txt"


# ---------------------------------------------------------------------------
# Independent pi reference (decimal / Machin-like)
#
# Used to cross-check pi_project_v4.calculate_pi against a genuinely
# independent implementation so the tests are not self-referential.
# ---------------------------------------------------------------------------

def _reference_pi_decimals(digits: int) -> str:
    """Return `digits` decimal digits of pi (after the point) via Machin.

    pi/4 = 4*atan(1/5) - atan(1/239), evaluated with the `decimal` module.
    Independent of gmpy2 and of the binary-splitting implementation.
    """

    getcontext().prec = digits + 80

    def atan_inverse(n):
        x = Decimal(1) / Decimal(n)
        x_squared = x * x
        total = Decimal(0)
        power = x
        k = 0
        while True:
            term = power / (2 * k + 1)
            if term < Decimal(10) ** -(digits + 70):
                break
            total += term if k % 2 == 0 else -term
            power *= x_squared
            k += 1
        return total

    pi = Decimal(16) * atan_inverse(5) - Decimal(4) * atan_inverse(239)
    # compute a few guard decimals, then truncate (matching calculate_pi's
    # floor behaviour) rather than rounding the final digit.
    guard = 20
    s = format(pi, f".{digits + guard}f")
    return s.split(".")[1][:digits]


@pytest.fixture
def reference_pi_decimals():
    return _reference_pi_decimals
