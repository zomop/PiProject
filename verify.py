import argparse
import hashlib
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


# ============================================================================
# PiProject v4
# Full Reference Verification
# ============================================================================

REFERENCE_URL = "https://files.pilookup.com/pi/10000000.txt"

CALCULATED_FILE = "pi_10000000.txt"
REFERENCE_FILE = "reference_pi.txt"

CHUNK_SIZE = 1024 * 1024  # 1 MB

# Network behaviour.
DOWNLOAD_TIMEOUT = 60        # seconds per read attempt
DOWNLOAD_RETRIES = 3         # total download attempts
DOWNLOAD_BACKOFF_BASE = 2    # seconds, doubled after each failure


# ============================================================================
# Download Reference
# ============================================================================

def sha256_file(filename):
    """Return the SHA-256 hex digest of a file (streamed, constant memory)."""

    digest = hashlib.sha256()
    with open(filename, "rb", buffering=CHUNK_SIZE) as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_reference(filename=REFERENCE_FILE):
    """Download the reference pi file with retries and backoff.

    Reuses an existing local reference file instead of re-downloading.
    Returns the local path on success, or None on failure.
    """

    if Path(filename).exists():
        size = Path(filename).stat().st_size
        print(f"\nUsing existing local reference: {filename} ({size:,} bytes)")
        return filename

    print("\nDownloading reference...")
    print(f"URL: {REFERENCE_URL}")

    last_error = None

    for attempt in range(1, DOWNLOAD_RETRIES + 1):

        start = time.perf_counter()

        request = urllib.request.Request(
            REFERENCE_URL,
            headers={
                "User-Agent": (
                    "PiProject/1.0 (+https://github.com/zomop/PiProject)"
                ),
                "Accept": "*/*",
                "Connection": "keep-alive",
            },
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=DOWNLOAD_TIMEOUT,
            ) as response:

                total = response.headers.get("Content-Length")
                if total:
                    total = int(total)
                    print(f"Expected size : {total:,} bytes")

                downloaded = 0

                with open(
                    filename,
                    "wb",
                    buffering=CHUNK_SIZE,
                ) as f:

                    while True:

                        chunk = response.read(CHUNK_SIZE)

                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            percent = (downloaded / total) * 100
                            if sys.stderr.isatty():
                                print(
                                    f"\rDownloading: "
                                    f"{percent:6.2f}% "
                                    f"({downloaded:,} bytes)",
                                    end="",
                                    flush=True,
                                )
                            else:
                                # Non-TTY (CI / captured logs): one line per MB.
                                if (
                                    downloaded // CHUNK_SIZE
                                    > (downloaded - len(chunk)) // CHUNK_SIZE
                                ):
                                    print(
                                        f"Downloaded: {downloaded:,} bytes"
                                    )
                        else:
                            if sys.stderr.isatty():
                                print(
                                    f"\rDownloaded: "
                                    f"{downloaded:,} bytes",
                                    end="",
                                    flush=True,
                                )

            print()

        except urllib.error.HTTPError as e:
            last_error = f"HTTP Error {e.code}: {e.reason}"
            print(f"\n❌ {last_error} (attempt {attempt}/{DOWNLOAD_RETRIES})")
        except urllib.error.URLError as e:
            last_error = f"Connection error: {e.reason}"
            print(f"\n❌ {last_error} (attempt {attempt}/{DOWNLOAD_RETRIES})")
        except TimeoutError:
            last_error = "Download timed out"
            print(f"\n❌ {last_error} (attempt {attempt}/{DOWNLOAD_RETRIES})")
        except OSError as e:
            last_error = f"File error: {e}"
            print(f"\n❌ {last_error} (attempt {attempt}/{DOWNLOAD_RETRIES})")

        if Path(filename).exists():
            # A partial file may remain; remove it before retrying.
            try:
                Path(filename).unlink()
            except OSError:
                pass

        if attempt < DOWNLOAD_RETRIES:
            backoff = DOWNLOAD_BACKOFF_BASE ** attempt
            print(f"Retrying in {backoff}s...")
            time.sleep(backoff)

        elapsed = time.perf_counter() - start

    print(f"\n❌ Reference download failed after {DOWNLOAD_RETRIES} attempts.")
    if last_error:
        print(f"Last error: {last_error}")
    print("Verification cancelled.")

    return None


# ============================================================================
# Normalize a chunk
# ============================================================================

def normalize_chunk(data):

    """
    Remove formatting characters so both files can be compared regardless of
    whether they contain:

        3.14159265...

    or:

        314159265...

    Whitespace/newlines are also ignored.
    """

    if isinstance(data, bytes):
        data = data.replace(b"\r", b"")
        data = data.replace(b"\n", b"")
        data = data.replace(b" ", b"")
        data = data.replace(b"\t", b"")
        data = data.replace(b".", b"")

    return data


# ============================================================================
# Count digits
# ============================================================================

def count_digits(filename):

    """Count the normalized digits in a file."""

    total = 0

    with open(
        filename,
        "rb",
        buffering=CHUNK_SIZE,
    ) as f:

        while True:

            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            chunk = normalize_chunk(chunk)

            total += len(chunk)

    return total


# ============================================================================
# Full Verification
# ============================================================================

def verify_full(calculated_file, reference_file):

    print()
    print("=" * 60)
    print("                    VERIFICATION")
    print("=" * 60)

    print(f"Calculated file : {calculated_file}")
    print(f"Reference file  : {reference_file}")

    print("\nComparing files...")

    start = time.perf_counter()

    matched = 0
    mismatched = 0
    first_mismatch = None

    calculated_digits = 0
    reference_digits = 0

    with open(calculated_file, "rb", buffering=CHUNK_SIZE) as calculated, \
            open(reference_file, "rb", buffering=CHUNK_SIZE) as reference:

        calculated_data = b""
        reference_data = b""

        while True:

            # Fill calculated buffer
            if not calculated_data:
                raw = calculated.read(CHUNK_SIZE)
                if raw:
                    calculated_data = normalize_chunk(raw)

            # Fill reference buffer
            if not reference_data:
                raw = reference.read(CHUNK_SIZE)
                if raw:
                    reference_data = normalize_chunk(raw)

            # Both ended
            if not calculated_data and not reference_data:
                break

            # One ended before the other
            if not calculated_data:
                extra = len(reference_data)
                mismatched += extra
                if first_mismatch is None:
                    first_mismatch = matched + mismatched - extra
                reference_digits += extra
                reference_data = b""
                continue

            if not reference_data:
                extra = len(calculated_data)
                mismatched += extra
                if first_mismatch is None:
                    first_mismatch = matched + mismatched - extra
                calculated_digits += extra
                calculated_data = b""
                continue

            # Compare available bytes
            length = min(len(calculated_data), len(reference_data))

            c = calculated_data[:length]
            r = reference_data[:length]

            # Fast equality path
            if c == r:
                matched += length
            else:
                # Find exact mismatches
                for i in range(length):
                    if c[i] == r[i]:
                        matched += 1
                    else:
                        mismatched += 1
                        if first_mismatch is None:
                            first_mismatch = matched + mismatched - 1

            calculated_digits += length
            reference_digits += length

            calculated_data = calculated_data[length:]
            reference_data = reference_data[length:]

            # Progress every ~1 MB (TTY only; CI logs stay readable)
            total_processed = min(calculated_digits, reference_digits)
            if sys.stderr.isatty() and total_processed // CHUNK_SIZE > (
                (total_processed - length) // CHUNK_SIZE
            ):
                print(
                    f"\rCompared: {total_processed:,} digits",
                    end="",
                    flush=True,
                )

    print("\n")

    print(f"Calculated : {calculated_digits:,}")
    print(f"Reference  : {reference_digits:,}")
    print(f"Matched    : {matched:,}")
    print(f"Mismatched : {mismatched:,}")

    elapsed = time.perf_counter() - start
    print(f"\nVerification time: {elapsed:.4f} seconds")

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    if mismatched == 0 and calculated_digits == reference_digits:
        print()
        print("✅ VERIFIED!")
        print(f"All {matched:,} digits match the reference.")
        return True

    print()
    print("❌ VERIFICATION FAILED!")

    if first_mismatch is not None:
        print(f"First mismatch position: {first_mismatch:,}")

    if calculated_digits != reference_digits:
        print("\n⚠️  The files have a different number of digits.")

    return False


# ============================================================================
# Main
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare a calculated pi file with a reference file."
    )
    parser.add_argument(
        "--calculated",
        default=CALCULATED_FILE,
        help=f"calculated file to verify (default: {CALCULATED_FILE})",
    )
    parser.add_argument(
        "--reference",
        help="use an existing reference file instead of downloading one",
    )
    parser.add_argument(
        "--sha256",
        help="expected SHA-256 of the reference file (establish from a trusted source)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    calculated_file = args.calculated

    print("=" * 60)
    print("               PiProject v4")
    print("             FULL VERIFICATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Check calculated file
    # --------------------------------------------------------

    if not Path(calculated_file).exists():
        print(f"\n❌ File not found: {calculated_file}")
        return 1

    calculated_size = Path(calculated_file).stat().st_size
    print(f"\nCalculated file size: {calculated_size:,} bytes")

    # --------------------------------------------------------
    # Resolve reference file
    # --------------------------------------------------------

    if args.reference:
        reference_file = args.reference
        if not Path(reference_file).exists():
            print(f"\n❌ Reference file not found: {reference_file}")
            return 1
        print(f"\nUsing local reference: {reference_file}")
    else:
        reference_file = download_reference()

    if reference_file is None:
        print("\n❌ Reference could not be obtained.")
        return 1

    # --------------------------------------------------------
    # Optional SHA-256 integrity check
    # --------------------------------------------------------

    if args.sha256:
        actual = sha256_file(reference_file)
        if actual.lower() != args.sha256.lower():
            print(f"\n❌ SHA-256 mismatch for reference file.")
            print(f"    expected: {args.sha256}")
            print(f"    actual:   {actual}")
            return 1
        print(f"\nSHA-256 verified: {actual}")

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    ok = verify_full(calculated_file, reference_file)

    return 0 if ok else 1


# ============================================================================
# Start
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())
