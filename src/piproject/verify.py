"""Independent verification engine for PiProject.

This module is *independent* of the computation engine in ``compute.py``.
It verifies pi digit strings against trusted references using multiple
methods and reports explicit verification statuses:

    CALCULATED        - value was computed, no verification performed
    STRUCTURE_VALID   - passes structural checks (format, length, digits)
    PREFIX_VERIFIED   - matches known reference for the checked prefix only
    FULLY_VERIFIED    - every digit compared against a trustworthy reference
    INDEPENDENTLY_VERIFIED - confirmed by an independent algorithm (e.g. BBP)
    VERIFICATION_FAILED - a mismatch or error was detected

Never report FULLY_VERIFIED when only a prefix has been checked.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reuse statuses from the package __init__
from piproject import (
    CALCULATED,
    FULLY_VERIFIED,
    INDEPENDENTLY_VERIFIED,
    PREFIX_VERIFIED,
    STRUCTURE_VALID,
    VERIFICATION_FAILED,
)

CHUNK_SIZE = 1024 * 1024  # 1 MB


@dataclass
class VerificationReport:
    """A complete, reproducible verification report."""

    status: str = CALCULATED
    digits_requested: int = 0
    digits_compared: int = 0
    digits_matched: int = 0
    digits_mismatched: int = 0
    first_mismatch_position: Optional[int] = None
    reference_source: Optional[str] = None
    reference_sha256: Optional[str] = None
    calculated_sha256: Optional[str] = None
    verification_time: float = 0.0
    method: str = ""
    details: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "digits_requested": self.digits_requested,
            "digits_compared": self.digits_compared,
            "digits_matched": self.digits_matched,
            "digits_mismatched": self.digits_mismatched,
            "first_mismatch_position": self.first_mismatch_position,
            "reference_source": self.reference_source,
            "reference_sha256": self.reference_sha256,
            "calculated_sha256": self.calculated_sha256,
            "verification_time": self.verification_time,
            "method": self.method,
            "details": self.details,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def is_fully_verified(self) -> bool:
        # Only FULLY_VERIFIED means every digit was compared against a
        # trustworthy reference. INDEPENDENTLY_VERIFIED (e.g. BBP spot checks)
        # confirms the algorithm at sampled positions only and is NOT full
        # verification of the output.
        return self.status == FULLY_VERIFIED


# ============================================================================
# Reference management
# ============================================================================

@dataclass
class ReferenceInfo:
    """Metadata about a reference file."""

    path: Path
    sha256: str
    digit_count: int
    source: str  # URL or description of provenance
    notes: str = ""


def sha256_file(path: Path, chunk_size: int = CHUNK_SIZE) -> str:
    """Return the SHA-256 hex digest of a file (streamed, constant memory)."""

    digest = hashlib.sha256()
    with path.open("rb", buffering=chunk_size) as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def normalize_bytes(data: bytes) -> bytes:
    """Remove formatting characters (whitespace, dots) from a byte string."""
    return (
        data.replace(b"\r", b"")
        .replace(b"\n", b"")
        .replace(b" ", b"")
        .replace(b"\t", b"")
        .replace(b".", b"")
    )


def count_digits_in_file(path: Path, chunk_size: int = CHUNK_SIZE) -> int:
    """Count normalized digits in a file."""
    total = 0
    with path.open("rb", buffering=chunk_size) as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            total += len(normalize_bytes(chunk))
    return total


def read_decimal_digits(path: Path, expected_count: Optional[int] = None) -> str:
    """Read a file and return its normalized decimal digits as a string.

    If ``expected_count`` is given and the file contains a different number
    of digits, a ValueError is raised.
    """

    digits = bytearray()
    with path.open("rb", buffering=CHUNK_SIZE) as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digits.extend(normalize_bytes(chunk))

    text = digits.decode("ascii")
    if expected_count is not None and len(text) != expected_count:
        raise ValueError(
            f"Expected {expected_count:,} digits, found {len(text):,}"
        )
    return text


# ============================================================================
# Structural validation
# ============================================================================

def validate_structure(pi_string: str, digits: int) -> Tuple[bool, str]:
    """Check that ``pi_string`` is structurally valid.

    Returns (is_valid, reason).
    """

    if not isinstance(pi_string, str):
        return False, "input is not a string"

    if "." not in pi_string:
        return False, "missing decimal point"

    integer_part, _, decimal_part = pi_string.partition(".")

    if integer_part != "3":
        return False, f"integer part is {integer_part!r}, expected '3'"

    if len(decimal_part) != digits:
        return False, (
            f"expected {digits:,} fractional digits, found {len(decimal_part):,}"
        )

    if not decimal_part.isdigit():
        return False, "fractional part contains non-digit characters"

    return True, ""


# ============================================================================
# Prefix verification (built-in known digits)
# ============================================================================

# First 1,000 decimal digits of pi (after the decimal point).
# Source: https://www.piday.org/million/ — independent of compute.py.
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


def verify_prefix_builtin(pi_string: str, digits: int) -> Tuple[str, int]:
    """Verify against the built-in 1,000-digit reference.

    Returns (status, checked_count).
    """

    ok, reason = validate_structure(pi_string, digits)
    if not ok:
        return VERIFICATION_FAILED, 0

    _, _, decimal_part = pi_string.partition(".")

    check_len = min(digits, len(PI_DECIMAL_DIGITS_1000))
    if decimal_part[:check_len] != PI_DECIMAL_DIGITS_1000[:check_len]:
        return VERIFICATION_FAILED, 0

    if digits <= len(PI_DECIMAL_DIGITS_1000):
        return FULLY_VERIFIED, digits

    return PREFIX_VERIFIED, check_len


# ============================================================================
# Full file-to-file verification
# ============================================================================

def verify_files(
    calculated_path: Path,
    reference_path: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> VerificationReport:
    """Compare a calculated file against a reference file digit by digit.

    Both files are normalized (whitespace and dots removed) before comparison.
    """

    report = VerificationReport(
        status=CALCULATED,
        method="file_to_file",
        reference_source=str(reference_path),
    )

    start = time.perf_counter()

    if not calculated_path.exists():
        report.status = VERIFICATION_FAILED
        report.details["error"] = f"calculated file not found: {calculated_path}"
        report.verification_time = time.perf_counter() - start
        return report

    if not reference_path.exists():
        report.status = VERIFICATION_FAILED
        report.details["error"] = f"reference file not found: {reference_path}"
        report.verification_time = time.perf_counter() - start
        return report

    # Hash both files
    report.calculated_sha256 = sha256_file(calculated_path, chunk_size)
    report.reference_sha256 = sha256_file(reference_path, chunk_size)

    calculated_digits = 0
    reference_digits = 0
    matched = 0
    mismatched = 0
    first_mismatch: Optional[int] = None

    with calculated_path.open("rb", buffering=chunk_size) as calc, \
            reference_path.open("rb", buffering=chunk_size) as ref:

        calc_data = b""
        ref_data = b""

        while True:
            if not calc_data:
                raw = calc.read(chunk_size)
                if raw:
                    calc_data = normalize_bytes(raw)

            if not ref_data:
                raw = ref.read(chunk_size)
                if raw:
                    ref_data = normalize_bytes(raw)

            if not calc_data and not ref_data:
                break

            if not calc_data:
                extra = len(ref_data)
                mismatched += extra
                if first_mismatch is None:
                    first_mismatch = matched + mismatched - extra
                reference_digits += extra
                ref_data = b""
                continue

            if not ref_data:
                extra = len(calc_data)
                mismatched += extra
                if first_mismatch is None:
                    first_mismatch = matched + mismatched - extra
                calculated_digits += extra
                calc_data = b""
                continue

            length = min(len(calc_data), len(ref_data))
            c = calc_data[:length]
            r = ref_data[:length]

            if c == r:
                matched += length
            else:
                for i in range(length):
                    if c[i] == r[i]:
                        matched += 1
                    else:
                        mismatched += 1
                        if first_mismatch is None:
                            first_mismatch = matched + mismatched - 1

            calculated_digits += length
            reference_digits += length
            calc_data = calc_data[length:]
            ref_data = ref_data[length:]

    elapsed = time.perf_counter() - start

    report.digits_requested = calculated_digits
    report.digits_compared = min(calculated_digits, reference_digits)
    report.digits_matched = matched
    report.digits_mismatched = mismatched
    report.first_mismatch_position = first_mismatch
    report.verification_time = elapsed
    report.details = {
        "calculated_digits": calculated_digits,
        "reference_digits": reference_digits,
        "chunk_size": chunk_size,
    }

    if mismatched == 0 and calculated_digits == reference_digits:
        report.status = FULLY_VERIFIED
    elif mismatched > 0:
        report.status = VERIFICATION_FAILED
    else:
        # Length mismatch with no character mismatches in overlap
        report.status = VERIFICATION_FAILED

    return report


# ============================================================================
# BBP independent spot checks
# ============================================================================

from piproject.bbp import (
    bbp_vs_decimal,
    decimal_to_hex_at,
    spot_check_positions,
)  # noqa: E402


def verify_bbp_spot_checks(
    positions: List[int],
    num_digits: int = 5,
) -> VerificationReport:
    """Run BBP hexadecimal spot checks at the given positions.

    This is algorithmically independent of the Chudnovsky computation engine.
    Results are spot checks, not full verification.
    """

    report = VerificationReport(
        status=CALCULATED,
        method="bbp_spot_check",
    )

    start = time.perf_counter()
    results = spot_check_positions(positions)
    elapsed = time.perf_counter() - start

    all_match = all(m for _, _, m in results.values())

    report.details = {
        "positions": positions,
        "num_digits_per_position": num_digits,
        "results": {
            str(pos): {"bbp": bbp, "reference": ref, "match": m}
            for pos, (bbp, ref, m) in results.items()
        },
        "all_match": all_match,
    }
    report.verification_time = elapsed

    if all_match:
        report.status = INDEPENDENTLY_VERIFIED
        report.digits_compared = len(positions) * num_digits
        report.digits_matched = len(positions) * num_digits
    else:
        report.status = VERIFICATION_FAILED

    return report


# ============================================================================
# Complete verification pipeline
# ============================================================================

def verify_pi(
    pi_string: str,
    digits: int,
    *,
    reference_path: Optional[Path] = None,
    bbp_positions: Optional[List[int]] = None,
) -> VerificationReport:
    """Run the full verification pipeline on a pi string.

    Steps:
        1. Structural validation  -> STRUCTURE_VALID or VERIFICATION_FAILED
        2. Built-in prefix check  -> PREFIX_VERIFIED (or FULLY_VERIFIED if <=1000)
        3. Optional file-to-file reference comparison -> FULLY_VERIFIED
        4. Optional BBP spot checks -> INDEPENDENTLY_VERIFIED (supplemental)

    The final status reflects the strongest verification achieved.
    """

    report = VerificationReport(
        status=CALCULATED,
        digits_requested=digits,
        method="pipeline",
    )

    start = time.perf_counter()

    # Step 1: Structure
    ok, reason = validate_structure(pi_string, digits)
    if not ok:
        report.status = VERIFICATION_FAILED
        report.details["structure_error"] = reason
        report.verification_time = time.perf_counter() - start
        return report

    report.status = STRUCTURE_VALID

    # Step 2: Built-in prefix
    prefix_status, checked = verify_prefix_builtin(pi_string, digits)
    report.digits_compared = checked
    report.digits_matched = checked

    if prefix_status == VERIFICATION_FAILED:
        report.status = VERIFICATION_FAILED
        report.verification_time = time.perf_counter() - start
        return report

    report.status = prefix_status

    # Step 3: Full reference comparison (if a file is provided)
    if reference_path is not None:
        _, _, decimal_part = pi_string.partition(".")
        # Write to a temp file for comparison
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as tmp:
            # Write the full pi_string ("3.14159...") so it matches the
            # reference file format after normalization.
            tmp.write(pi_string)
            tmp_path = Path(tmp.name)

        try:
            file_report = verify_files(tmp_path, reference_path)
            report.calculated_sha256 = file_report.calculated_sha256
            report.reference_sha256 = file_report.reference_sha256
            report.reference_source = str(reference_path)
            report.digits_compared = file_report.digits_compared
            report.digits_matched = file_report.digits_matched
            report.digits_mismatched = file_report.digits_mismatched
            report.first_mismatch_position = file_report.first_mismatch_position
            report.details["file_verification"] = file_report.to_dict()

            if file_report.status == FULLY_VERIFIED:
                report.status = FULLY_VERIFIED
            elif file_report.status == VERIFICATION_FAILED:
                report.status = VERIFICATION_FAILED
        finally:
            tmp_path.unlink(missing_ok=True)

    # Step 4: BBP spot checks (supplemental, independent).
    # Two related checks are performed:
    #   (a) Pure BBP vs published hex reference — confirms the algorithm
    #       independently of the computation engine.
    #   (b) BBP vs decimal-to-hex conversion of the calculated output —
    #       establishes a real relationship between the decimal result and
    #       independent BBP computation.
    # Neither changes the main verification status or implies full verification.
    if bbp_positions:
        bbp_details = {}

        # (a) Pure BBP vs published reference
        pure_report = verify_bbp_spot_checks(bbp_positions)
        bbp_details["pure_bbp_vs_reference"] = pure_report.to_dict()

        # (b) BBP vs decimal-to-hex of the calculated output
        _, _, decimal_part = pi_string.partition(".")
        try:
            decimal_vs_bbp = bbp_vs_decimal(decimal_part, bbp_positions)
            bbp_details["bbp_vs_decimal"] = {
                str(pos): {
                    "bbp": bbp,
                    "decimal_hex": dec_hex,
                    "match": match,
                }
                for pos, (bbp, dec_hex, match) in decimal_vs_bbp.items()
            }
            bbp_details["decimal_to_bbp_all_match"] = all(
                m for _, _, m in decimal_vs_bbp.values()
            )
        except ValueError as exc:
            bbp_details["decimal_to_bbp_error"] = str(exc)

        report.details["bbp_spot_checks"] = bbp_details

    report.verification_time = time.perf_counter() - start
    return report


def verify_pi_file(
    calculated_path: Path,
    reference_path: Path,
    *,
    bbp_positions: Optional[List[int]] = None,
) -> VerificationReport:
    """Verify a calculated pi file against a reference file.

    Reads the calculated file, extracts decimal digits, and runs the
    full verification pipeline.
    """

    report = VerificationReport(
        status=CALCULATED,
        method="file_pipeline",
        reference_source=str(reference_path),
    )

    start = time.perf_counter()

    if not calculated_path.exists():
        report.status = VERIFICATION_FAILED
        report.details["error"] = f"calculated file not found: {calculated_path}"
        report.verification_time = time.perf_counter() - start
        return report

    if not reference_path.exists():
        report.status = VERIFICATION_FAILED
        report.details["error"] = f"reference file not found: {reference_path}"
        report.verification_time = time.perf_counter() - start
        return report

    # Hash both files
    report.calculated_sha256 = sha256_file(calculated_path)
    report.reference_sha256 = sha256_file(reference_path)

    # Full file-to-file verification
    file_report = verify_files(calculated_path, reference_path)
    report.digits_compared = file_report.digits_compared
    report.digits_matched = file_report.digits_matched
    report.digits_mismatched = file_report.digits_mismatched
    report.first_mismatch_position = file_report.first_mismatch_position
    report.details["file_verification"] = file_report.to_dict()

    if file_report.status == FULLY_VERIFIED:
        report.status = FULLY_VERIFIED
        report.digits_requested = file_report.digits_compared
    else:
        report.status = VERIFICATION_FAILED

    # Optional BBP spot checks (supplemental, independent).
    # BBP never changes the main verification status or implies full verification.
    if bbp_positions:
        bbp_details = {}

        # (a) Pure BBP vs published reference
        pure_report = verify_bbp_spot_checks(bbp_positions)
        bbp_details["pure_bbp_vs_reference"] = pure_report.to_dict()

        # (b) BBP vs decimal-to-hex of the calculated output
        try:
            decimal_digits = read_decimal_digits(calculated_path)
            # Strip integer part "3" if present
            if decimal_digits.startswith("3"):
                decimal_digits = decimal_digits[1:]
            decimal_vs_bbp = bbp_vs_decimal(decimal_digits, bbp_positions)
            bbp_details["bbp_vs_decimal"] = {
                str(pos): {
                    "bbp": bbp,
                    "decimal_hex": dec_hex,
                    "match": match,
                }
                for pos, (bbp, dec_hex, match) in decimal_vs_bbp.items()
            }
            bbp_details["decimal_to_bbp_all_match"] = all(
                m for _, _, m in decimal_vs_bbp.values()
            )
        except (ValueError, OSError) as exc:
            bbp_details["decimal_to_bbp_error"] = str(exc)

        report.details["bbp_spot_checks"] = bbp_details

    report.verification_time = time.perf_counter() - start
    return report


__all__ = [
    "CALCULATED",
    "STRUCTURE_VALID",
    "PREFIX_VERIFIED",
    "FULLY_VERIFIED",
    "INDEPENDENTLY_VERIFIED",
    "VERIFICATION_FAILED",
    "VerificationReport",
    "ReferenceInfo",
    "sha256_file",
    "sha256_bytes",
    "normalize_bytes",
    "count_digits_in_file",
    "read_decimal_digits",
    "validate_structure",
    "verify_prefix_builtin",
    "verify_files",
    "verify_bbp_spot_checks",
    "verify_pi",
    "verify_pi_file",
]
