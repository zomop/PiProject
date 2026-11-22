"""Professional command-line interface for PiProject.

Usage:

    piproject calculate --digits 1000000 --output pi_1000000.txt
    piproject verify --input pi.txt --reference reference.txt
    piproject benchmark --digits 1000000
    piproject inspect --input pi.txt
    piproject hash --input pi.txt
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from piproject import (
    CALCULATED,
    FULLY_VERIFIED,
    INDEPENDENTLY_VERIFIED,
    PREFIX_VERIFIED,
    STRUCTURE_VALID,
    VERIFICATION_FAILED,
    __version__,
)
from piproject.bbp import spot_check_positions
from piproject.compute import GUARD_DIGITS, calculate_pi, calculate_pi_to_file
from piproject.verify import (
    VerificationReport,
    sha256_file,
    verify_files,
    verify_pi,
    verify_pi_file,
)


# ============================================================================
# Helpers
# ============================================================================

def _format_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    if seconds < 60:
        return f"{seconds:.3f} s"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}m {s:.1f}s"


def _format_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _status_color(status: str) -> str:
    """Return an ANSI-colored status string (no-op on non-TTY)."""
    if not sys.stdout.isatty():
        return status
    colors = {
        VERIFICATION_FAILED: "\033[31m",   # red
        FULLY_VERIFIED: "\033[32m",        # green
        INDEPENDENTLY_VERIFIED: "\033[32m", # green
        PREFIX_VERIFIED: "\033[33m",       # yellow
        STRUCTURE_VALID: "\033[36m",       # cyan
        CALCULATED: "\033[0m",             # default
    }
    reset = "\033[0m"
    return f"{colors.get(status, '')}{status}{reset}"


# ============================================================================
# Commands
# ============================================================================

def cmd_calculate(args: argparse.Namespace) -> int:
    digits = args.digits
    output = Path(args.output) if args.output else None

    if digits <= 0:
        print("Error: --digits must be greater than 0.", file=sys.stderr)
        return 1

    print(f"PiProject v{__version__}")
    print(f"Calculating {digits:,} decimal digits of pi...")
    print("Method: Chudnovsky + Binary Splitting + GMPY2")

    try:
        if output:
            pi_string, elapsed = calculate_pi_to_file(
                digits, output=output
            )
        else:
            pi_string, elapsed = calculate_pi(digits)
    except MemoryError:
        print("Error: not enough memory.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Calculation error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    decimal_part = pi_string.split(".")[1]
    total_digits = len(pi_string.replace(".", ""))

    print(f"Calculation complete in {_format_time(elapsed)}.")
    print(f"Total digits: {total_digits:,}")
    print(f"Decimal digits: {len(decimal_part):,}")
    print(f"Throughput: {len(decimal_part) / elapsed:,.0f} digits/sec")
    print(f"SHA-256 (decimals): {__import__('hashlib').sha256(decimal_part.encode()).hexdigest()}")

    if output:
        print(f"Saved to: {output} ({_format_size(output.stat().st_size)})")

    # Built-in prefix verification
    from piproject.verify import verify_prefix_builtin, STRUCTURE_VALID

    status, checked = verify_prefix_builtin(pi_string, digits)
    print(f"\nPrefix verification ({checked:,} digits checked): {_status_color(status)}")

    if status == VERIFICATION_FAILED:
        print("Verification FAILED!", file=sys.stderr)
        return 1

    print(f"\nPi preview: {pi_string[:80]}...")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    reference_path = Path(args.reference) if args.reference else None

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    if reference_path and not reference_path.exists():
        print(f"Error: reference file not found: {reference_path}", file=sys.stderr)
        return 1

    print(f"PiProject v{__version__}")
    print(f"Verifying: {input_path}")
    if reference_path:
        print(f"Reference: {reference_path}")

    # Read input and count digits
    from piproject.verify import read_decimal_digits

    # Read decimal part. The file may contain "3.14159..." format where the
    # leading "3" is the integer part. count_digits_in_file counts ALL
    # normalized digits (including "3"), so fractional digits = total - 1.
    try:
        all_digits = read_decimal_digits(input_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Strip the integer part "3" to get only fractional digits
    if all_digits.startswith("3"):
        decimal_digits = all_digits[1:]
    else:
        decimal_digits = all_digits

    digits = len(decimal_digits)
    print(f"Digits in input: {digits:,}")

    pi_string = "3." + decimal_digits

    # BBP positions
    bbp_positions = None
    if args.bbp:
        bbp_positions = [int(p) for p in args.bbp.split(",")]

    report = verify_pi(
        pi_string,
        digits,
        reference_path=reference_path,
        bbp_positions=bbp_positions,
    )

    print(f"\nVerification report:")
    print(f"  Status: {_status_color(report.status)}")
    print(f"  Method: {report.method}")
    print(f"  Digits requested: {report.digits_requested:,}")
    print(f"  Digits compared: {report.digits_compared:,}")
    print(f"  Digits matched: {report.digits_matched:,}")
    print(f"  Digits mismatched: {report.digits_mismatched:,}")
    print(f"  Verification time: {_format_time(report.verification_time)}")
    if report.reference_source:
        print(f"  Reference: {report.reference_source}")
    if report.reference_sha256:
        print(f"  Reference SHA-256: {report.reference_sha256}")
    if report.calculated_sha256:
        print(f"  Calculated SHA-256: {report.calculated_sha256}")
    if report.first_mismatch_position is not None:
        print(f"  First mismatch position: {report.first_mismatch_position:,}")

    if report.details.get("bbp_spot_checks"):
        bbp = report.details["bbp_spot_checks"]
        pure = bbp.get("pure_bbp_vs_reference", {})
        pure_details = pure.get("details", {})
        pure_results = pure_details.get("results", {})
        all_match_pure = all(r["match"] for r in pure_results.values()) if pure_results else False
        print(f"\n  BBP vs published reference: {'all match' if all_match_pure else 'MISMATCH'}")
        for pos, r in pure_results.items():
            print(f"    Position {pos}: BBP={r['bbp']} ref={r['reference']} match={r['match']}")

        dec_vs_bbp = bbp.get("bbp_vs_decimal", {})
        if dec_vs_bbp:
            all_match_dec = all(r["match"] for r in dec_vs_bbp.values())
            print(f"  BBP vs decimal-to-hex: {'all match' if all_match_dec else 'MISMATCH'}")
            for pos, r in dec_vs_bbp.items():
                print(f"    Position {pos}: BBP={r['bbp']} dec_hex={r['decimal_hex']} match={r['match']}")

    if report.is_fully_verified():
        print(f"\nResult: FULLY VERIFIED ✓")
        return 0
    if report.status == VERIFICATION_FAILED:
        print(f"\nResult: VERIFICATION FAILED ✗", file=sys.stderr)
        return 1
    print(f"\nResult: {report.status} (not full verification)")
    return 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    digits = args.digits
    repeats = args.repeats

    print(f"PiProject v{__version__}")
    print(f"Benchmark: {digits:,} digits, {repeats} repeat(s)")
    print("Method: Chudnovsky + Binary Splitting + GMPY2")
    print()

    import platform

    print(f"Platform: {platform.platform()}")
    print(f"Python: {platform.python_version()}")
    import gmpy2
    print(f"GMPY2: {gmpy2.version()}")
    print()

    times: List[float] = []
    for i in range(repeats):
        print(f"  Run {i + 1}/{repeats}...", end="", flush=True)
        try:
            _, elapsed = calculate_pi(digits)
        except MemoryError:
            print(" FAILED (out of memory)")
            return 1
        times.append(elapsed)
        print(f" {_format_time(elapsed)}")

    print()
    print(f"Best:   {_format_time(min(times))}")
    print(f"Worst:  {_format_time(max(times))}")
    print(f"Average: {_format_time(sum(times) / len(times))}")
    print(f"Throughput: {digits / min(times):,.0f} digits/sec (best)")

    # Save benchmark result
    result = {
        "digits": digits,
        "repeats": repeats,
        "times": times,
        "best": min(times),
        "worst": max(times),
        "average": sum(times) / len(times),
        "throughput_best": digits / min(times),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "gmpy2": gmpy2.version(),
    }

    import json, datetime
    result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    bench_dir = Path("benchmarks")
    bench_dir.mkdir(exist_ok=True)
    out = bench_dir / f"benchmark_{digits}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\nBenchmark saved to: {out}")

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    from piproject.verify import read_decimal_digits, verify_prefix_builtin

    # Read all normalized digits (includes integer part "3")
    try:
        all_digits = read_decimal_digits(input_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Strip the integer part "3" to get only fractional digits
    if all_digits.startswith("3"):
        decimal_digits = all_digits[1:]
    else:
        decimal_digits = all_digits

    digits = len(decimal_digits)
    total_digits = len(all_digits)  # includes "3"
    size = input_path.stat().st_size

    print(f"PiProject v{__version__}")
    print(f"Inspecting: {input_path}")
    print(f"File size: {size:,} bytes ({_format_size(size)})")
    print(f"Total digits (incl. integer part): {total_digits:,}")
    print(f"Fractional digits: {digits:,}")

    print(f"First 50 decimals: {decimal_digits[:50]}")
    print(f"Last 50 decimals:  {decimal_digits[-50:]}")

    import hashlib
    print(f"SHA-256 (decimals): {hashlib.sha256(decimal_digits.encode()).hexdigest()}")
    print(f"SHA-256 (file): {sha256_file(input_path)}")

    # Check against built-in prefix
    pi_string = "3." + decimal_digits
    status, checked = verify_prefix_builtin(pi_string, min(digits, 1000))
    print(f"\nBuilt-in prefix check ({checked:,} digits): {status}")

    return 0


def cmd_hash(args: argparse.Namespace) -> int:
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    print(f"File: {input_path}")
    print(f"SHA-256: {sha256_file(input_path)}")

    # Also hash just the decimal digits
    from piproject.verify import count_digits_in_file, read_decimal_digits

    digits = count_digits_in_file(input_path)
    decimal_digits = read_decimal_digits(input_path)
    import hashlib
    print(f"SHA-256 (decimals only): {hashlib.sha256(decimal_digits.encode()).hexdigest()}")
    print(f"Digits: {digits:,}")

    return 0


# ============================================================================
# Argument parser
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piproject",
        description="PiProject — High-performance π computation and verification.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"PiProject v{__version__}",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # calculate
    p_calc = sub.add_parser("calculate", help="Calculate pi digits")
    p_calc.add_argument("--digits", type=int, required=True, help="Number of decimal digits")
    p_calc.add_argument("--output", help="Output file (default: pi_<digits>.txt)")
    p_calc.set_defaults(func=cmd_calculate)

    # verify
    p_ver = sub.add_parser("verify", help="Verify pi against a reference")
    p_ver.add_argument("--input", required=True, help="Calculated pi file")
    p_ver.add_argument("--reference", help="Reference file for full comparison")
    p_ver.add_argument(
        "--bbp",
        help="BBP spot-check positions (comma-separated, e.g. 1,10,100)",
    )
    p_ver.set_defaults(func=cmd_verify)

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark calculation speed")
    p_bench.add_argument("--digits", type=int, default=100000, help="Digits to compute")
    p_bench.add_argument("--repeats", type=int, default=3, help="Number of runs")
    p_bench.set_defaults(func=cmd_benchmark)

    # inspect
    p_inspect = sub.add_parser("inspect", help="Inspect a pi file")
    p_inspect.add_argument("--input", required=True, help="Pi file to inspect")
    p_inspect.set_defaults(func=cmd_inspect)

    # hash
    p_hash = sub.add_parser("hash", help="Compute SHA-256 of a pi file")
    p_hash.add_argument("--input", required=True, help="File to hash")
    p_hash.set_defaults(func=cmd_hash)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
