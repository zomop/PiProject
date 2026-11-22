"""BBP (Bailey–Borwein–Plouffe) hexadecimal digit extraction.

Algorithmically independent of the Chudnovsky/binary-splitting computation
engine. The BBP formula computes hexadecimal digits of pi at arbitrary
positions without computing preceding digits:

    pi = sum_{k=0}^{inf} 1/16^k * (4/(8k+1) - 2/(8k+4) - 1/(8k+5) - 1/(8k+6))

This module is used for *spot checks* — verifying individual hexadecimal
positions — not for full digit-range verification.
"""

from __future__ import annotations

from typing import Tuple

# Known hexadecimal digits of pi (after the point), from published sources.
# pi = 3.243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89...
KNOWN_HEX = (
    "243f6a8885a308d313198a2e03707344a4093822299f31d0082efa98ec4e6c89"
    "452821e638d01377be5466cf34e90c6cc0ac29b7c97c50dd3f84d5b5b5470917"
)


def mod_pow16(exp: int, mod: int) -> int:
    """Return 16^exp mod mod using modular exponentiation."""
    return pow(16, exp, mod)


def bbp_sum(n: int, j: int) -> float:
    """Compute the j-th component of the BBP sum modulo 1.

    S_j = sum_{k=0}^{inf} 16^(n-k) / (8k+j)  (mod 1)

    Split at k = n: for k <= n, 16^(n-k) is an integer; for k > n it is
    fractional. Modular exponentiation keeps the integer part bounded.
    """

    # Part 1: k = 0 to n
    s = 0.0
    for k in range(0, n + 1):
        denom = 8 * k + j
        pow16 = mod_pow16(n - k, denom)
        s += pow16 / denom
        s -= int(s)  # keep only the fractional part

    # Part 2: k = n+1 to infinity (terms become negligible quickly)
    k = n + 1
    while True:
        shift = k - n
        denom = 8 * k + j
        term = 1.0 / (denom * (16 ** shift))
        s += term
        s -= int(s)
        if term < 1e-17:
            break
        k += 1
        if k - n > 10_000:  # safety bound
            break

    return s % 1.0


def bbp_hex_digits(position: int, num_digits: int = 5) -> str:
    """Return `num_digits` hexadecimal digits of pi starting at `position`.

    Parameters
    ----------
    position:
        1-indexed position after the hexadecimal point. Position 1 returns
        the first hex digit after the point.
    num_digits:
        Number of hex digits to extract.

    Returns
    -------
    A lowercase hexadecimal string of length `num_digits`.
    """

    n = position - 1
    # pi = 4*S1 - 2*S4 - S5 - S6
    s = (
        4 * bbp_sum(n, 1)
        - 2 * bbp_sum(n, 4)
        - bbp_sum(n, 5)
        - bbp_sum(n, 6)
    ) % 1.0
    if s < 0:
        s += 1.0
    if s >= 1.0:
        s -= 1.0

    hex_digits = ""
    x = s
    for _ in range(num_digits):
        x *= 16
        digit = int(x)
        hex_digits += "0123456789abcdef"[digit]
        x -= digit

    return hex_digits


def check_position(position: int, num_digits: int = 5) -> Tuple[str, str, bool]:
    """Check a BBP position against the published reference.

    Returns (bbp_result, reference, match).
    """

    bbp = bbp_hex_digits(position, num_digits)
    ref = KNOWN_HEX[position - 1 : position - 1 + num_digits]
    match = bbp == ref
    return bbp, ref, match


def spot_check_positions(positions: list[int]) -> dict[int, Tuple[str, str, bool]]:
    """Run BBP spot checks at multiple positions.

    Returns a dict mapping position -> (bbp, reference, match).
    """
    results: dict[int, Tuple[str, str, bool]] = {}
    for pos in positions:
        results[pos] = check_position(pos)
    return results
