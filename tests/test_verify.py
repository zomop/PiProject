"""Tests for the independent verification engine (piproject.verify)."""

import hashlib
from pathlib import Path

import pytest

import piproject.verify as verify_mod
from piproject import (
    CALCULATED,
    FULLY_VERIFIED,
    INDEPENDENTLY_VERIFIED,
    PREFIX_VERIFIED,
    STRUCTURE_VALID,
    VERIFICATION_FAILED,
)
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
    r = VerificationReport(status=FULLY_VERIFIED)
    assert r.is_fully_verified() is True

    r = VerificationReport(status=INDEPENDENTLY_VERIFIED)
    assert r.is_fully_verified() is True

    r = VerificationReport(status=PREFIX_VERIFIED)
    assert r.is_fully_verified() is False

    r = VerificationReport(status=VERIFICATION_FAILED)
    assert r.is_fully_verified() is False
