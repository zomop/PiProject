"""BBP (Bailey–Borwein–Plouffe) hexadecimal digit extraction.

Algorithmically independent of the Chudnovsky/binary-splitting computation
engine. The BBP formula computes hexadecimal digits of pi at arbitrary
positions without computing preceding digits:

    pi = sum_{k=0}^{inf} 1/16^k * (4/(8k+1) - 2/(8k+4) - 1/(8k+5) - 1/(8k+6))

This module is used for *spot checks* — verifying individual hexadecimal
positions — not for full digit-range verification.

It also provides decimal-to-hexadecimal conversion so that BBP spot checks can
be validated *against* a calculated decimal output, establishing a real
relationship between the two representations rather than comparing BBP against
a hardcoded string alone.
"""

from __future__ import annotations

import sys
from typing import Tuple

# Known hexadecimal digits of pi (after the point), from published sources.
# pi = 3.243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89...
KNOWN_HEX = (
    "243f6a8885a308d313198a2e03707344a4093822299f31d0082efa98ec4e6c89"
    "452821e638d01377be5466cf34e90c6cc0ac29b7c97c50dd3f84d5b5b5470917"
)

# log10(16) ≈ 1.20412 — decimal digits needed per hex digit position.
_DECIMALS_PER_HEX_POSITION = 1.21


def _ensure_int_str_digits(needed: int) -> None:
    """Raise if Python's int<->str digit limit is too low for `needed` digits."""
    limit = sys.get_int_max_str_digits()
    if needed > limit:
        raise ValueError(
            f"Need {needed:,} digits but int<->str limit is {limit:,}. "
            "Call sys.set_int_max_str_digits() with a higher value first."
        )


def decimal_to_hex_at(
    decimal_digits: str,
    position: int,
    num_digits: int = 1,
) -> str:
    """Convert decimal digits of pi to hexadecimal digits at a given position.

    Given `decimal_digits` (the fractional digits of pi as a string), returns
    `num_digits` hexadecimal digits starting at 1-indexed `position` after the
    hexadecimal point.

    Mathematically: if `value = floor(pi * 10^D)` where D = len(decimal_digits),
    then the hex digits at positions `position`..`position+num_digits-1` are
    approximately `floor(16^(position+num_digits-1) * value / 10^D) mod 16^num_digits`.

    This is accurate only when D > position * log10(16) ≈ position * 1.204,
    i.e. when enough decimal digits are available to resolve the requested hex
    position. A ValueError is raised if the precision is insufficient.

    Parameters
    ----------
    decimal_digits:
        Fractional decimal digits of pi (no "3.", no decimal point).
    position:
        1-indexed hexadecimal position after the point. Position 1 is the
        first hex digit after the point.
    num_digits:
        Number of hex digits to extract.

    Returns
    -------
    A lowercase hexadecimal string of length `num_digits`.

    Raises
    ------
    ValueError
        If the input is invalid or the decimal precision is insufficient for
        the requested position.
    """

    if not decimal_digits or not decimal_digits.isdigit():
        raise ValueError("decimal_digits must be a non-empty string of digits")

    if position < 1:
        raise ValueError("position must be >= 1")

    if num_digits < 1:
        raise ValueError("num_digits must be >= 1")

    num_decimals = len(decimal_digits)

    # Precision requirement: D > position * log10(16) to resolve position.
    needed_decimals = int(position * _DECIMALS_PER_HEX_POSITION) + num_digits + 2
    if num_decimals < needed_decimals:
        raise ValueError(
            f"Insufficient decimal precision: need > {needed_decimals:,} "
            f"decimal digits to resolve hex position {position}, "
            f"but only {num_decimals:,} available."
        )

    _ensure_int_str_digits(num_decimals + 4 * (position + num_digits - 1))

    # value = floor(pi * 10^num_decimals) = int("3" + decimal_digits)
    value = int("3" + decimal_digits)
    pow10 = 10 ** num_decimals

    # floor(16^(position+num_digits-1) * value / 10^num_decimals)
    # gives hex digits covering positions 1..position+num_digits-1.
    scaled = value << (4 * (position + num_digits - 1))  # * 16^(position+num_digits-1)
    combined = scaled // pow10

    # Extract just the requested window: positions position..position+num_digits-1
    window = combined % (16 ** num_digits)
    return format(window, f"0{num_digits}x")


def bbp_vs_decimal(
    decimal_digits: str,
    positions: list[int],
    num_digits: int = 5,
) -> dict[int, Tuple[str, str, bool]]:
    """Compare BBP hex digits against decimal-to-hex conversion.

    This establishes a real relationship between a calculated decimal output
    and independent BBP computation: if the decimal digits are correct, their
    hexadecimal conversion must match BBP at the same positions.

    Returns a dict mapping position -> (bbp, decimal_hex, match).
    """
    results: dict[int, Tuple[str, str, bool]] = {}
    for pos in positions:
        bbp = bbp_hex_digits(pos, num_digits)
        try:
            dec_hex = decimal_to_hex_at(decimal_digits, pos, num_digits)
        except ValueError as exc:
            dec_hex = f"ERROR: {exc}"
        match = bbp == dec_hex if not dec_hex.startswith("ERROR") else False
        results[pos] = (bbp, dec_hex, match)
    return results


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
