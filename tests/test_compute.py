"""Tests for the computation engine (piproject.compute)."""

import hashlib
import sys

import gmpy2
import pytest

import piproject.compute as compute
from piproject import (
    FULLY_VERIFIED,
    PREFIX_VERIFIED,
    VERIFICATION_FAILED,
)


# ---------------------------------------------------------------------------
# binary_split
# ---------------------------------------------------------------------------

def test_binary_split_base_case_zero():
    P, Q, T = compute.binary_split(0, 1)
    assert P == gmpy2.mpz(1)
    assert Q == gmpy2.mpz(1)
    assert T == gmpy2.mpz(13591409)


def test_binary_split_base_case_nonzero():
    P, Q, T = compute.binary_split(2, 3)
    k = gmpy2.mpz(2)
    expected_P = (6 * k - 5) * (2 * k - 1) * (6 * k - 1)
    expected_Q = k**3 * compute.C3_OVER_24
    expected_T = expected_P * (compute.A + compute.B * k)
    assert P == expected_P
    assert Q == expected_Q
    assert T == expected_T


def test_binary_split_sign_alternation():
    _, _, T_even = compute.binary_split(2, 3)
    _, _, T_odd = compute.binary_split(3, 4)
    assert T_even > 0
    assert T_odd < 0


def test_binary_split_associativity():
    P_all, Q_all, T_all = compute.binary_split(0, 8)
    P1, Q1, T1 = compute.binary_split(0, 4)
    P2, Q2, T2 = compute.binary_split(4, 8)
    assert P_all == P1 * P2
    assert Q_all == Q1 * Q2
    assert T_all == T1 * Q2 + P1 * T2


# ---------------------------------------------------------------------------
# calculate_pi correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("digits", [1, 2, 5, 10, 50, 100, 250, 500, 1000])
def test_calculate_pi_matches_known_digits(digits):
    """The full result must match known pi digits for digits <= 1000."""
    pi, _ = compute.calculate_pi(digits)
    integer_part, _, decimal_part = pi.partition(".")
    assert integer_part == "3"
    assert len(decimal_part) == digits
    assert decimal_part.isdigit()
    assert decimal_part == compute.PI_DECIMAL_DIGITS_1000[:digits]


@pytest.mark.parametrize("digits", [1, 5, 50, 100, 500, 1000])
def test_calculate_pi_matches_independent(digits, reference_pi_decimals):
    """Cross-check against independent decimal/Machin implementation."""
    pi, _ = compute.calculate_pi(digits)
    _, _, decimal_part = pi.partition(".")
    assert decimal_part == reference_pi_decimals(digits)


@pytest.mark.parametrize("digits", [1, 7, 100])
def test_calculate_pi_format(digits):
    """Result is always '<integer>.<exactly digits fractionals>'."""
    pi, _ = compute.calculate_pi(digits)
    assert pi.count(".") == 1
    integer_part, _, decimal_part = pi.partition(".")
    assert integer_part == "3"
    assert len(decimal_part) == digits


@pytest.mark.parametrize("digits", [1000, 10000])
def test_calculate_pi_large_matches_independent(digits, reference_pi_decimals):
    """Cross-check larger values against independent computation."""
    pi, _ = compute.calculate_pi(digits)
    _, _, decimal_part = pi.partition(".")
    assert decimal_part == reference_pi_decimals(digits)


def test_calculate_pi_rejects_zero():
    with pytest.raises(ValueError):
        compute.calculate_pi(0)


def test_calculate_pi_rejects_negative():
    with pytest.raises(ValueError):
        compute.calculate_pi(-5)


# ---------------------------------------------------------------------------
# verify_prefix
# ---------------------------------------------------------------------------

def test_verify_prefix_accepts_correct():
    pi, _ = compute.calculate_pi(100)
    status, checked = compute.verify_prefix(pi, 100)
    assert status == FULLY_VERIFIED
    assert checked == 100


def test_verify_prefix_small_digit():
    """Regression: verify_prefix must not false-negative on small results."""
    pi, _ = compute.calculate_pi(5)
    status, checked = compute.verify_prefix(pi, 5)
    assert status == FULLY_VERIFIED
    assert checked == 5


def test_verify_prefix_rejects_corrupted():
    pi, _ = compute.calculate_pi(100)
    corrupted = pi[:-1] + ("1" if pi[-1] != "1" else "2")
    status, _ = compute.verify_prefix(corrupted, 100)
    assert status == VERIFICATION_FAILED


def test_verify_prefix_beyond_1000_is_prefix_only():
    """Digits beyond 1000 are PREFIX_VERIFIED, not FULLY_VERIFIED."""
    pi, _ = compute.calculate_pi(1500)
    status, checked = compute.verify_prefix(pi, 1500)
    assert status == PREFIX_VERIFIED
    assert checked == 1000


def test_verify_prefix_false_positive_beyond_1000():
    """Corrupting a digit beyond position 1000 must NOT pass as FULLY_VERIFIED."""
    pi, _ = compute.calculate_pi(2000)
    # Corrupt a digit at position 1500 (after the 1000-digit prefix)
    idx = 1500  # 0-indexed in decimal part
    orig = pi[idx + 2]  # +2 for "3."
    repl = "9" if orig != "9" else "8"
    corrupted = pi[: idx + 2] + repl + pi[idx + 3:]
    status, checked = compute.verify_prefix(corrupted, 2000)
    assert status == PREFIX_VERIFIED  # prefix check passes
    assert checked == 1000


# ---------------------------------------------------------------------------
# save/streaming
# ---------------------------------------------------------------------------

def test_calculate_pi_streaming_writes_file(tmp_pi_file):
    pi, elapsed = compute.calculate_pi_streaming(50, output=tmp_pi_file)
    assert tmp_pi_file.exists()
    assert tmp_pi_file.read_text(encoding="ascii") == pi
    assert elapsed > 0


# ---------------------------------------------------------------------------
# gmpy2 global state
# ---------------------------------------------------------------------------

def test_compute_does_not_mutate_gmpy2_precision(gmpy2_precision):
    before = gmpy2.get_context().precision
    compute.calculate_pi(50)
    after = gmpy2.get_context().precision
    assert after == before


# ---------------------------------------------------------------------------
# SHA-256 reproducibility
# ---------------------------------------------------------------------------

def test_calculate_pi_sha256_stable():
    """The SHA-256 of the output must be stable across runs."""
    import piproject.verify as verify_mod

    pi1, _ = compute.calculate_pi(250)
    pi2, _ = compute.calculate_pi(250)
    assert pi1 == pi2
    h1 = hashlib.sha256(pi1.split(".")[1].encode()).hexdigest()
    h2 = hashlib.sha256(pi2.split(".")[1].encode()).hexdigest()
    assert h1 == h2
