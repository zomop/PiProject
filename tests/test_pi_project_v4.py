"""Tests for pi_project_v4.py (Chudnovsky + binary splitting + GMP)."""

import os
import subprocess
import sys

import gmpy2
import pytest

import pi_project_v4 as m


# ---------------------------------------------------------------------------
# calculate_pi correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("digits", [1, 2, 5, 10, 50, 100, 250, 500, 1000])
def test_calculate_pi_matches_known_digits(digits):
    """The full result must match known pi digits for digits <= 1000."""

    pi, _ = m.calculate_pi(digits)

    integer_part, _, decimal_part = pi.partition(".")
    assert integer_part == "3"
    assert len(decimal_part) == digits
    assert decimal_part.isdigit()
    assert decimal_part == m.PI_DECIMAL_DIGITS_1000[:digits]


@pytest.mark.parametrize("digits", [1, 5, 50, 100, 500, 1000])
def test_calculate_pi_matches_independent_reference(digits, reference_pi_decimals):
    """Cross-check against an independent decimal/Machin implementation."""

    pi, _ = m.calculate_pi(digits)
    _, _, decimal_part = pi.partition(".")
    assert decimal_part == reference_pi_decimals(digits)


def test_calculate_pi_format_and_length():
    """Result is always '<integer>.<exactly digits fractionals>'."""

    for digits in (1, 7, 100):
        pi, _ = m.calculate_pi(digits)
        assert pi.count(".") == 1
        integer_part, _, decimal_part = pi.partition(".")
        assert integer_part == "3"
        assert len(decimal_part) == digits


# ---------------------------------------------------------------------------
# binary_split
# ---------------------------------------------------------------------------

def test_binary_split_base_case_zero():
    P, Q, T = m.binary_split(0, 1)
    assert P == gmpy2.mpz(1)
    assert Q == gmpy2.mpz(1)
    assert T == gmpy2.mpz(13591409)


def test_binary_split_base_case_nonzero():
    P, Q, T = m.binary_split(2, 3)
    k = gmpy2.mpz(2)
    expected_P = (6 * k - 5) * (2 * k - 1) * (6 * k - 1)
    expected_Q = k**3 * m.C3_OVER_24
    expected_T = expected_P * (m.A + m.B * k)  # sign: a=2 is even -> positive
    assert P == expected_P
    assert Q == expected_Q
    assert T == expected_T


def test_binary_split_sign_alternation():
    # a odd -> T negated
    P_even, _, T_even = m.binary_split(2, 3)
    P_odd, _, T_odd = m.binary_split(3, 4)
    assert T_even > 0
    assert T_odd < 0


def test_binary_split_associativity():
    """Splitting [0, n) directly equals combining [0, m) and [m, n)."""

    P_all, Q_all, T_all = m.binary_split(0, 8)
    P1, Q1, T1 = m.binary_split(0, 4)
    P2, Q2, T2 = m.binary_split(4, 8)

    assert P_all == P1 * P2
    assert Q_all == Q1 * Q2
    assert T_all == T1 * Q2 + P1 * T2


# ---------------------------------------------------------------------------
# verify_pi
# ---------------------------------------------------------------------------

def test_verify_pi_accepts_correct_result():
    pi, _ = m.calculate_pi(100)
    assert m.verify_pi(pi, 100) is True


def test_verify_pi_rejects_wrong_digit():
    pi, _ = m.calculate_pi(100)
    corrupted = pi[:-1] + ("1" if pi[-1] != "1" else "2")
    assert m.verify_pi(corrupted, 100) is False


def test_verify_pi_rejects_wrong_length():
    pi, _ = m.calculate_pi(100)
    # 99 fractional digits -> wrong length
    assert m.verify_pi(pi[:-1], 100) is False


def test_verify_pi_rejects_wrong_integer_part():
    pi, _ = m.calculate_pi(100)
    assert m.verify_pi("4" + pi[1:], 100) is False


def test_verify_pi_small_digit_no_false_negative():
    # Regression: previously verify_pi(5) returned False for a correct
    # 5-digit result because the fixed prefix was longer than the output.
    pi, _ = m.calculate_pi(5)
    assert m.verify_pi(pi, 5) is True


def test_verify_pi_rejects_non_string_and_malformed():
    assert m.verify_pi(None, 10) is False
    assert m.verify_pi("3.14", 10) is False   # wrong length
    assert m.verify_pi("3.14159abc", 10) is False  # non-digits


# ---------------------------------------------------------------------------
# save_pi
# ---------------------------------------------------------------------------

def test_save_pi_writes_exact_contents(tmp_output):
    pi, _ = m.calculate_pi(25)
    saved = m.save_pi(pi, 25, filename=tmp_output)
    assert saved == tmp_output
    assert tmp_output.read_text(encoding="ascii") == pi


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_digits_and_output(tmp_output, monkeypatch, capsys):
    argv = ["--digits", "40", "--output", str(tmp_output)]
    code = m.main(argv)
    assert code == 0
    assert tmp_output.exists()
    content = tmp_output.read_text(encoding="ascii")
    content_int, _, content_dec = content.partition(".")
    assert content_int == "3"
    assert len(content_dec) == 40
    assert content_dec == m.PI_DECIMAL_DIGITS_1000[:40]


def test_cli_rejects_nonpositive_digits(monkeypatch, capsys):
    code = m.main(["--digits", "0"])
    assert code == 1
    out = capsys.readouterr().out
    assert "greater than 0" in out


def test_cli_rejects_invalid_digits(monkeypatch, capsys):
    # argparse exits non-zero on a non-integer --digits.
    with pytest.raises(SystemExit):
        m.main(["--digits", "not-a-number"])


def test_cli_verification_catches_corruption(monkeypatch, capsys, tmp_output):
    # Feed a wrong digit count: --digits 3 but verify expects correct first 3
    # decimals (141). A correct calc of 3 digits is "3.141" -> verifies.
    # To force failure we monkeypatch verify_pi.
    monkeypatch.setattr(m, "verify_pi", lambda pi, d: False)
    code = m.main(["--digits", "10", "--output", str(tmp_output)])
    assert code == 1


def test_interactive_fallback_monkeypatched(monkeypatch, tmp_output):
    # No --digits -> use input() fallback; write via --output.
    monkeypatch.setattr("builtins.input", lambda prompt="": "20")
    code = m.main(["--output", str(tmp_output)])
    assert code == 0
    assert tmp_output.read_text(encoding="ascii") == (
        "3." + m.PI_DECIMAL_DIGITS_1000[:20]
    )


def test_module_import_does_not_prompt(capsys):
    # Importing must not call input() or exit (regression for pie-style bug).
    import importlib
    importlib.reload(m)
    out = capsys.readouterr().out
    assert out == ""


# ---------------------------------------------------------------------------
# No global GMPY2 state mutation on import
# ---------------------------------------------------------------------------

def test_import_does_not_change_gmpy2_precision():
    before = gmpy2.get_context().precision
    import importlib
    importlib.reload(m)
    after = gmpy2.get_context().precision
    assert after == before
