"""Computation engine for PiProject.

Implements the Chudnovsky algorithm with binary splitting using GMPY2
arbitrary-precision integer arithmetic. This is the primary calculation
engine; it is independent of the verification engine in ``verify.py``.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import gmpy2

from piproject import (
    FULLY_VERIFIED,
    PREFIX_VERIFIED,
    VERIFICATION_FAILED,
)

# ============================================================================
# Chudnovsky constants
# ============================================================================

# Chudnovsky algorithm:
#   1/pi = 12 * sum_{k=0}^{inf} (-1)^k * (6k)! * (545140134*k + 13591409) /
#                        ((3k)! * (k!)^3 * (640320)^(3k + 3/2))
# Equivalently:
#   pi = 426880 * sqrt(10005) * Q / T
# where P, Q, T come from binary splitting over the series term ratio.

C = 640320
C3_OVER_24 = C**3 // 24
A = 13591409
B = 545140134

# Each Chudnovsky term yields roughly 14.18 decimal digits.
DIGITS_PER_TERM = 14

# Guard digits appended during computation to absorb floor/truncation error.
GUARD_DIGITS = 20

# First 1,000 decimal digits of pi (after the decimal point), computed with
# an independent decimal/Machin implementation and cross-checked against
# https://www.piday.org/million/. Used for prefix verification.
PI_DECIMAL_DIGITS_1000 = (
    "14159265358979323846264338327950288419716939937510582097494459230781"
    "64062862089986280348253421170679821480865132823066470938446095505822"
    "31725359408128481117450284102701938521105559644622948954930381964428"
    "810975665933446128475648233786783165271201909145648566923460348610454"
    "326648213393607260249141273724587006606315588174881520920962829254091"
    "715364367892590360011330530548820466521384146951941511609433057270365"
    "759591953092186117381932611793105118548074462379962749567351885752724"
    "891227938183011949129833673362440656643086021394946395224737190702179"
    "860943702770539217176293176752384674818467669405132000568127145263560"
    "827785771342757789609173637178721468440901224953430146549585371050792"
    "279689258923542019956112129021960864034418159813629774771309960518707"
    "211349999998372978049951059731732816096318595024459455346908302642522"
    "308253344685035261931188171010003137838752886587533208381420617177669"
    "147303598253490428755468731159562863882353787593751957781857780532171"
    "2268066130019278766111959092164201989"
)

assert len(PI_DECIMAL_DIGITS_1000) == 1000


# ============================================================================
# Binary splitting
# ============================================================================

def binary_split(a: int, b: int) -> Tuple[gmpy2.mpz, gmpy2.mpz, gmpy2.mpz]:
    """Chudnovsky binary splitting over the range [a, b).

    Returns the triplet (P, Q, T) such that:

        P = product of p_k
        Q = product of q_k
        T = sum of t_k * (product of p after k)

    where p_k, q_k, t_k are the Chudnovsky term components.
    """

    if b - a == 1:
        if a == 0:
            return (
                gmpy2.mpz(1),
                gmpy2.mpz(1),
                gmpy2.mpz(A),
            )

        k = gmpy2.mpz(a)

        P = (6 * k - 5) * (2 * k - 1) * (6 * k - 1)
        Q = k**3 * C3_OVER_24
        T = P * (A + B * k)

        if a & 1:
            T = -T

        return P, Q, T

    m = (a + b) // 2

    P1, Q1, T1 = binary_split(a, m)
    P2, Q2, T2 = binary_split(m, b)

    P = P1 * P2
    Q = Q1 * Q2
    T = T1 * Q2 + P1 * T2

    return P, Q, T


# ============================================================================
# Main computation
# ============================================================================

def calculate_pi(
    digits: int,
    *,
    guard_digits: int = GUARD_DIGITS,
) -> Tuple[str, float]:
    """Calculate `digits` decimal digits of pi.

    Uses the Chudnovsky algorithm with binary splitting and GMPY2 integer
    arithmetic. The result is truncated (not rounded) to exactly `digits`
    fractional digits.

    Parameters
    ----------
    digits:
        Number of decimal digits of pi to compute (after the decimal point).
        Must be greater than 0.
    guard_digits:
        Number of guard digits used internally to absorb truncation error.

    Returns
    -------
    (pi_string, elapsed_seconds)
        pi_string has the form "<integer_part>.<exactly `digits` fractional
        digits>", e.g. "3.14159...".
    """

    if digits <= 0:
        raise ValueError("digits must be greater than 0")

    start = time.perf_counter()

    # Number of terms needed: each term yields ~14.18 digits.
    terms = digits // DIGITS_PER_TERM + 1

    P, Q, T = binary_split(0, terms)

    # Scale factor: pi = 426880 * sqrt(10005) * Q / T
    # Compute with guard digits so truncation error is confined to the
    # discarded tail.
    scale = gmpy2.mpz(10) ** (digits + guard_digits)

    sqrt_10005 = gmpy2.isqrt(gmpy2.mpz(10005) * scale * scale)

    numerator = gmpy2.mpz(426880) * sqrt_10005 * Q

    pi_scaled = numerator // T  # floor(pi * 10^(digits + guard_digits))

    # Convert scaled integer to decimal string.
    s = str(pi_scaled)

    # Discard guard digits from the fractional (right) end.
    if len(s) > guard_digits:
        s = s[:-guard_digits]

    # s should now be exactly "3" + `digits` fractional digits
    # (length == digits + 1). Pad the fractional side with trailing zeros if
    # we came up short; never left-pad, which would corrupt the integer part.
    if len(s) < digits + 1:
        s = s.ljust(digits + 1, "0")
    elif len(s) > digits + 1:
        s = s[: digits + 1]

    integer_part = s[0]
    decimal_part = s[1:]

    pi_string = integer_part + "." + decimal_part

    elapsed = time.perf_counter() - start

    return pi_string, elapsed


def calculate_pi_streaming(
    digits: int,
    output: Optional[Path] = None,
    *,
    chunk_size: int = 1024 * 1024,
    guard_digits: int = GUARD_DIGITS,
) -> Tuple[str, float]:
    """Calculate pi and stream the result to an output file.

    This is a thin wrapper around :func:`calculate_pi` that writes the result
    to disk in chunks, avoiding holding an additional copy of the full string
    in memory beyond what the computation already produces.

    Returns (pi_string, elapsed_seconds).
    """

    pi_string, elapsed = calculate_pi(digits, guard_digits=guard_digits)

    if output is None:
        output = Path(f"pi_{digits}.txt")

    with output.open("w", encoding="ascii", buffering=chunk_size) as f:
        f.write(pi_string)

    return pi_string, elapsed


# ============================================================================
# Prefix verification (built into the computation engine for fast feedback)
# ============================================================================

def verify_prefix(pi_string: str, digits: int) -> Tuple[str, int]:
    """Verify a pi string against the known first 1,000 decimal digits.

    This is a *prefix check only*. For ``digits > 1000`` it does not
    constitute full verification; use the independent verification engine
    in :mod:`piproject.verify` for that.

    Returns (status, checked_count) where status is one of the module-level
    status constants.
    """

    if not isinstance(pi_string, str) or "." not in pi_string:
        return VERIFICATION_FAILED, 0

    integer_part, _, decimal_part = pi_string.partition(".")

    if integer_part != "3":
        return VERIFICATION_FAILED, 0

    if len(decimal_part) != digits:
        return VERIFICATION_FAILED, 0

    if not decimal_part.isdigit():
        return VERIFICATION_FAILED, 0

    check_len = min(digits, len(PI_DECIMAL_DIGITS_1000))
    if decimal_part[:check_len] != PI_DECIMAL_DIGITS_1000[:check_len]:
        return VERIFICATION_FAILED, 0

    if digits <= len(PI_DECIMAL_DIGITS_1000):
        return FULLY_VERIFIED, digits

    return PREFIX_VERIFIED, check_len
