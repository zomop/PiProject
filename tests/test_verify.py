"""Tests for verify.py (reference comparison)."""

import hashlib

import pytest

import verify as v


# ---------------------------------------------------------------------------
# normalize_chunk
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
def test_normalize_chunk(raw, expected):
    assert v.normalize_chunk(raw) == expected


# ---------------------------------------------------------------------------
# count_digits
# ---------------------------------------------------------------------------

def test_count_digits(tmp_path):
    p = tmp_path / "digits.txt"
    p.write_bytes(b"3.14159\n26535\n")
    assert v.count_digits(p) == 11  # 31415926535


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------

def test_sha256_file(tmp_path):
    p = tmp_path / "data.txt"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert v.sha256_file(p) == expected


# ---------------------------------------------------------------------------
# verify_full
# ---------------------------------------------------------------------------

def _write_digits(path, digits_str):
    path.write_bytes(digits_str.encode("ascii"))


def test_verify_full_match(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    digits = "314159265358979323846264338327950288419716939937510"
    _write_digits(calc, digits)
    _write_digits(ref, digits)

    ok = v.verify_full(calc, ref)
    assert ok is True


def test_verify_full_mismatch(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    _write_digits(calc, "314159")
    _write_digits(ref, "314150")  # last digit differs

    ok = v.verify_full(calc, ref)
    assert ok is False


def test_verify_full_length_mismatch(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    _write_digits(calc, "314159")        # 6 digits
    _write_digits(ref, "3141592653")     # 10 digits

    ok = v.verify_full(calc, ref)
    assert ok is False


def test_verify_full_formatting_insensitive(tmp_path):
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    # Different formatting (spaces/newlines/dots) but same digits.
    _write_digits(calc, "3.14159\n26535")
    _write_digits(ref, "31 41 59 26 535")

    ok = v.verify_full(calc, ref)
    assert ok is True


# ---------------------------------------------------------------------------
# main argument handling (no network)
# ---------------------------------------------------------------------------

import sys


def _run_main(argv):
    old_argv = sys.argv
    sys.argv = argv
    try:
        return v.main()
    finally:
        sys.argv = old_argv


def test_main_missing_calculated_file():
    code = _run_main(["verify.py", "--calculated", "does_not_exist.txt"])
    assert code == 1


def test_main_missing_local_reference():
    code = _run_main(
        ["verify.py", "--calculated", "does_not_exist.txt",
         "--reference", "no_such_ref.txt"]
    )
    assert code == 1
