"""Tests for the independent verification engine (piproject.verify)."""

import hashlib
from pathlib import Path

import pytest

import piproject.verify as verify_mod
from piproject import (
    CALCULATED,
    CALCULATED,
    FULLY_VERIFIED,
    INDEPENDENTLY_VERIFIED,
    PREFIX_VERIFIED,
    STRUCTURE_VALID,
    VERIFICATION_FAILED,
)
from piproject.bbp import bbp_vs_decimal
from piproject.verify import (
    VerificationReport,
    count_digits_in_file,
    normalize_bytes,
    read_decimal_digits,
    sha256_bytes,
    sha256_file,
    validate_structure,
    verify_files,
    verify_prefix_builtin,
    verify_pi,
    verify_pi_file,
)


# ---------------------------------------------------------------------------
# normalize_bytes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        (b"3.14159", b"314159"),
        (b"3\n.14 15\r\n9\t", b"314159"),
        (b"", b""),
        (b"   ", b""),
        (b"..12..34..", b"1234"),
    ],
)
def test_normalize_bytes(raw, expected):
    assert normalize_bytes(raw) == expected


# ---------------------------------------------------------------------------
# sha256
# ---------------------------------------------------------------------------

def test_sha256_bytes():
    assert sha256_bytes(b"hello") == hashlib.sha256(b"hello").hexdigest()


def test_sha256_file(tmp_path):
    p = tmp_path / "data.txt"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert sha256_file(p) == expected


# ---------------------------------------------------------------------------
# count_digits_in_file
# ---------------------------------------------------------------------------

def test_count_digits_in_file(tmp_path):
    p = tmp_path / "digits.txt"
    p.write_bytes(b"3.14159\n26535\n")
    assert count_digits_in_file(p) == 11  # 31415926535


# ---------------------------------------------------------------------------
# read_decimal_digits
# ---------------------------------------------------------------------------

def test_read_decimal_digits(tmp_path):
    p = tmp_path / "pi.txt"
    p.write_bytes(b"3.14159\n26535")
    digits = read_decimal_digits(p, expected_count=11)
    assert digits == "31415926535"


def test_read_decimal_digits_wrong_count(tmp_path):
    p = tmp_path / "pi.txt"
    p.write_bytes(b"3.14159")
    with pytest.raises(ValueError):
        read_decimal_digits(p, expected_count=100)


# ---------------------------------------------------------------------------
# validate_structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "s, digits, valid",
    [
        ("3.14159", 5, True),
        ("3.14", 2, True),
        ("4.14159", 5, False),   # wrong integer part
        ("3.14", 5, False),      # wrong length
        ("3.1415a", 5, False),   # non-digit
        ("314159", 5, False),    # no decimal point
    ],
)
def test_validate_structure(s, digits, valid):
    ok, reason = validate_structure(s, digits)
    assert ok == valid, f"Expected valid={valid}, got reason={reason}"


# ---------------------------------------------------------------------------
# verify_prefix_builtin
# ---------------------------------------------------------------------------

def test_verify_prefix_builtin_accepts():
    status, checked = verify_prefix_builtin("3.14159", 5)
    assert status == FULLY_VERIFIED
    assert checked == 5


def test_verify_prefix_builtin_rejects_wrong_digit():
    status, _ = verify_prefix_builtin("3.14150", 5)
    assert status == VERIFICATION_FAILED


def test_verify_prefix_builtin_beyond_1000():
    """Digits beyond 1000 are PREFIX_VERIFIED."""
    # Construct a string with correct first 1000 digits
    from piproject.verify import PI_DECIMAL_DIGITS_1000

    s = "3." + PI_DECIMAL_DIGITS_1000 + "0" * 500
    status, checked = verify_prefix_builtin(s, 1500)
    assert status == PREFIX_VERIFIED
    assert checked == 1000


# ---------------------------------------------------------------------------
# verify_files
# ---------------------------------------------------------------------------

def test_verify_files_match(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    digits = "314159265358979323846264338327950288419716939937510"
    calc.write_bytes(digits.encode())
    ref.write_bytes(digits.encode())

    report = verify_files(calc, ref)
    assert report.status == FULLY_VERIFIED
    assert report.digits_matched == len(digits)
    assert report.digits_mismatched == 0


def test_verify_files_mismatch(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(b"314159")
    ref.write_bytes(b"314150")

    report = verify_files(calc, ref)
    assert report.status == VERIFICATION_FAILED
    assert report.digits_mismatched > 0


def test_verify_files_length_mismatch(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(b"314159")       # 6 digits
    ref.write_bytes(b"3141592653")    # 10 digits

    report = verify_files(calc, ref)
    assert report.status == VERIFICATION_FAILED


def test_verify_files_formatting_insensitive(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(b"3.14159\n26535")
    ref.write_bytes(b"31 41 59 26 535")

    report = verify_files(calc, ref)
    assert report.status == FULLY_VERIFIED


# ---------------------------------------------------------------------------
# verify_pi (string pipeline)
# ---------------------------------------------------------------------------

def test_verify_pi_full_match():
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    report = verify_pi(pi, 100)
    assert report.status == FULLY_VERIFIED
    assert report.digits_compared == 100


def test_verify_pi_rejects_corrupted():
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    corrupted = pi[:-1] + ("1" if pi[-1] != "1" else "2")
    report = verify_pi(corrupted, 100)
    assert report.status == VERIFICATION_FAILED


def test_verify_pi_structure_invalid():
    report = verify_pi("not pi", 5)
    assert report.status == VERIFICATION_FAILED


def test_verify_pi_with_reference(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    ref = tmp_path / "ref.txt"
    ref.write_bytes(pi.encode())  # full "3.14159..." format

    report = verify_pi(pi, 100, reference_path=ref)
    assert report.status == FULLY_VERIFIED


# ---------------------------------------------------------------------------
# Corruption detection (full-file verification)
# ---------------------------------------------------------------------------

def _make_calc_ref_pair(tmp_path, decimal_digits: str, corrupt_ref: bool = False):
    """Write a calculated file and matching reference file."""
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(len(decimal_digits))
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(pi.encode())
    ref.write_bytes(pi.encode())
    return calc, ref


def test_verify_corrupted_digit_near_beginning(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Corrupt the 3rd decimal digit (position 3)
    corrupted = pi[:4] + ("9" if pi[4] != "9" else "8") + pi[5:]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(corrupted.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED
    assert report.digits_mismatched > 0
    assert report.first_mismatch_position is not None
    assert report.first_mismatch_position < 10


def test_verify_corrupted_digit_around_1001(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(2000)
    # Corrupt a digit around position 1001 in the decimal part.
    # In the normalized file (dots removed), the integer part "3" occupies
    # position 0, so decimal index 1001 corresponds to normalized position 1002.
    idx = 1001  # position in decimal part
    orig = pi[idx + 2]  # +2 for "3."
    repl = "9" if orig != "9" else "8"
    corrupted = pi[: idx + 2] + repl + pi[idx + 3:]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(corrupted.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED
    # Normalized position = decimal index + 1 (for the "3" integer part)
    assert report.first_mismatch_position == idx + 1


def test_verify_corrupted_digit_near_end(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Corrupt the last decimal digit
    last_idx = len(pi) - 1
    orig = pi[last_idx]
    repl = "9" if orig != "9" else "8"
    corrupted = pi[:last_idx] + repl
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(corrupted.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED
    assert report.digits_mismatched >= 1


def test_verify_missing_digits(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Truncate the last 10 digits
    truncated = pi[:-10]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(truncated.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED


def test_verify_extra_digits(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Append extra digits
    extended = pi + "12345"
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(extended.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED


def test_verify_truncated_file(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Write only half the file
    half = pi[: len(pi) // 2]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(half.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED


def test_verify_invalid_characters(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Insert a letter
    invalid = pi[:10] + "x" + pi[11:]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(invalid.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    # normalize_bytes removes dots and whitespace but not letters,
    # so the letter 'x' will cause a mismatch
    assert report.status == VERIFICATION_FAILED


def test_verify_unexpected_whitespace(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Insert whitespace in the middle WITHOUT removing a digit
    with_space = pi[:10] + " \n\t" + pi[10:]
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(with_space.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    # normalize_bytes removes whitespace, so this should still match
    assert report.status == FULLY_VERIFIED


def test_verify_incorrect_decimal_point_placement(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    # Move the decimal point
    wrong_point = pi.replace(".", "", 1) + ".5"
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(wrong_point.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == VERIFICATION_FAILED


# ---------------------------------------------------------------------------
# BBP decimal-to-hex relationship tests
# ---------------------------------------------------------------------------

def test_bbp_vs_decimal_match():
    import sys

    sys.set_int_max_str_digits(100000)
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(5000)
    _, _, decimal_digits = pi.partition(".")

    # Decimal precision (5000) supports hex positions up to ~5000/1.21 ≈ 4132
    results = bbp_vs_decimal(decimal_digits, [1, 10, 100, 120], num_digits=5)
    for pos, (bbp, dec_hex, match) in results.items():
        assert match is True, f"Position {pos}: BBP={bbp} dec_hex={dec_hex}"


def test_bbp_vs_decimal_insufficient_precision():
    from piproject.bbp import bbp_vs_decimal

    # Only 10 decimal digits — not enough to resolve hex position 100
    results = bbp_vs_decimal("1415926535", [100], num_digits=5)
    bbp, dec_hex, match = results[100]
    assert match is False
    assert dec_hex.startswith("ERROR:")


def test_decimal_to_hex_at_known_positions():
    from piproject.bbp import decimal_to_hex_at

    # Known hex digits of pi: 243f6a8885a308d313198a2e03707344...
    # Use enough decimal digits (computed independently)
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(2000)
    _, _, decimal_digits = pi.partition(".")

    # Position 1: should be "243f6"
    assert decimal_to_hex_at(decimal_digits, 1, 5) == "243f6"
    # Position 10: should be "5a308"
    assert decimal_to_hex_at(decimal_digits, 10, 5) == "5a308"
    # Position 100: should be "c29b7"
    assert decimal_to_hex_at(decimal_digits, 100, 5) == "c29b7"


def test_verify_pi_report_is_serializable():
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(50)
    report = verify_pi(pi, 50)
    d = report.to_dict()
    assert "status" in d
    assert "digits_compared" in d
    j = report.to_json()
    assert isinstance(j, str)


# ---------------------------------------------------------------------------
# BBP spot checks
# ---------------------------------------------------------------------------

def test_verify_bbp_spot_checks():
    report = verify_mod.verify_bbp_spot_checks([1, 10, 100])
    assert report.status == INDEPENDENTLY_VERIFIED
    assert report.details["all_match"] is True


def test_verify_bbp_spot_checks_single():
    report = verify_mod.verify_bbp_spot_checks([1])
    assert report.status == INDEPENDENTLY_VERIFIED


# ---------------------------------------------------------------------------
# verify_pi_file
# ---------------------------------------------------------------------------

def test_verify_pi_file_match(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(100)
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(pi.encode())
    ref.write_bytes(pi.encode())

    report = verify_pi_file(calc, ref)
    assert report.status == FULLY_VERIFIED


def test_verify_pi_file_missing(tmp_path):
    report = verify_pi_file(tmp_path / "nonexistent.txt", tmp_path / "ref.txt")
    assert report.status == VERIFICATION_FAILED


# ---------------------------------------------------------------------------
# VerificationReport
# ---------------------------------------------------------------------------

def test_verification_report_is_fully_verified():
    # Only FULLY_VERIFIED means every digit was compared against a reference.
    r = VerificationReport(status=FULLY_VERIFIED)
    assert r.is_fully_verified() is True

    # INDEPENDENTLY_VERIFIED (e.g. BBP spot checks) confirms the algorithm at
    # sampled positions only and is NOT full verification of the output.
    r = VerificationReport(status=INDEPENDENTLY_VERIFIED)
    assert r.is_fully_verified() is False

    r = VerificationReport(status=PREFIX_VERIFIED)
    assert r.is_fully_verified() is False

    r = VerificationReport(status=VERIFICATION_FAILED)
    assert r.is_fully_verified() is False

    r = VerificationReport(status=STRUCTURE_VALID)
    assert r.is_fully_verified() is False

    r = VerificationReport(status=CALCULATED)
    assert r.is_fully_verified() is False
