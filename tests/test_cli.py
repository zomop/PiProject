"""Tests for the CLI (piproject.cli) using subprocess."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PIPROJECT = [sys.executable, "-m", "piproject.cli"]


def run_piproject(*args, cwd=None):
    """Run the piproject CLI as a subprocess."""
    result = subprocess.run(
        PIPROJECT + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result


# ---------------------------------------------------------------------------
# calculate
# ---------------------------------------------------------------------------

def test_cli_calculate(tmp_path):
    out = tmp_path / "pi_50.txt"
    result = run_piproject(
        "calculate", "--digits", "50", "--output", str(out), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    content = out.read_text(encoding="ascii")
    assert content.startswith("3.")
    assert len(content.split(".")[1]) == 50


def test_cli_calculate_rejects_zero():
    result = run_piproject("calculate", "--digits", "0")
    assert result.returncode != 0


def test_cli_calculate_no_output(tmp_path):
    result = run_piproject("calculate", "--digits", "25", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Throughput" in result.stdout


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def test_cli_verify_match(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(50)
    calc = tmp_path / "calc.txt"
    ref = tmp_path / "ref.txt"
    calc.write_bytes(pi.encode())
    ref.write_bytes(pi.encode())

    result = run_piproject(
        "verify", "--input", str(calc), "--reference", str(ref), cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert "FULLY VERIFIED" in result.stdout or "FULLY_VERIFIED" in result.stdout


def test_cli_verify_missing_input():
    result = run_piproject("verify", "--input", "/nonexistent/file.txt")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------

def test_cli_benchmark(tmp_path):
    result = run_piproject(
        "benchmark", "--digits", "100", "--repeats", "1", cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert "Best:" in result.stdout
    assert "Throughput" in result.stdout


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

def test_cli_inspect(tmp_path):
    from piproject.compute import calculate_pi

    pi, _ = calculate_pi(50)
    f = tmp_path / "pi.txt"
    f.write_bytes(pi.encode())

    result = run_piproject("inspect", "--input", str(f), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Fractional digits:" in result.stdout
    assert "SHA-256" in result.stdout


# ---------------------------------------------------------------------------
# hash
# ---------------------------------------------------------------------------

def test_cli_hash(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes(b"hello world")

    result = run_piproject("hash", "--input", str(f), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "SHA-256" in result.stdout


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

def test_cli_version():
    result = run_piproject("--version")
    assert result.returncode == 0
    assert "PiProject v" in result.stdout


# ---------------------------------------------------------------------------
# no command
# ---------------------------------------------------------------------------

def test_cli_no_command():
    result = run_piproject()
    assert result.returncode != 0
