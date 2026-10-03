import argparse
import urllib.request
import urllib.error
import time
from pathlib import Path


# ============================================================
# PiProject v4
# Full Reference Verification
# ============================================================

REFERENCE_URL = "https://files.pilookup.com/pi/10000000.txt"

CALCULATED_FILE = "pi_10000000.txt"
REFERENCE_FILE = "reference_pi.txt"

CHUNK_SIZE = 1024 * 1024  # 1 MB


# ============================================================
# Download Reference
# ============================================================

def download_reference(filename=REFERENCE_FILE):

    print("\nDownloading reference...")
    print(f"URL: {REFERENCE_URL}")

    start = time.perf_counter()

    request = urllib.request.Request(
        REFERENCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/138.0.0.0 "
                "Safari/537.36"
            ),
            "Accept": "*/*",
            "Connection": "keep-alive",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            total = response.headers.get("Content-Length")

            if total:
                total = int(total)
                print(f"Expected size : {total:,} bytes")

            downloaded = 0

            with open(
                filename,
                "wb",
                buffering=1024 * 1024
            ) as f:

                while True:

                    chunk = response.read(CHUNK_SIZE)

                    if not chunk:
                        break

                    f.write(chunk)

                    downloaded += len(chunk)

                    if total:
                        percent = (
                            downloaded / total
                        ) * 100

                        print(
                            f"\rDownloading: "
                            f"{percent:6.2f}% "
                            f"({downloaded:,} bytes)",
                            end="",
                            flush=True
                        )
                    else:
                        print(
                            f"\rDownloaded: "
                            f"{downloaded:,} bytes",
                            end="",
                            flush=True
                        )

        print()

    except urllib.error.HTTPError as e:

        print(
            f"\n❌ HTTP Error {e.code}: "
            f"{e.reason}"
        )

        return None

    except urllib.error.URLError as e:

        print(
            "\n❌ Connection error:"
        )

        print(e.reason)

        return None

    except TimeoutError:

        print(
            "\n❌ Download timed out."
        )

        return None

    elapsed = time.perf_counter() - start

    size = Path(filename).stat().st_size

    print(
        f"Reference saved : {filename}"
    )

    print(
        f"File size       : {size:,} bytes"
    )

    print(
        f"Download time   : {elapsed:.4f} seconds"
    )

    return filename


# ============================================================
# Normalize a chunk
# ============================================================

def normalize_chunk(data):

    """
    Remove formatting characters so both files can be
    compared regardless of whether they contain:

        3.14159265...

    or:

        314159265...

    Whitespace/newlines are also ignored.
    """

    if isinstance(data, bytes):

        data = data.replace(
            b"\r", b""
        )

        data = data.replace(
            b"\n", b""
        )

        data = data.replace(
            b" ", b""
        )

        data = data.replace(
            b"\t", b""
        )

        data = data.replace(
            b".", b""
        )

    return data


# ============================================================
# Count digits
# ============================================================

def count_digits(filename):

    total = 0

    with open(
        filename,
        "rb",
        buffering=CHUNK_SIZE
    ) as f:

        while True:

            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            chunk = normalize_chunk(chunk)

            total += len(chunk)

    return total


# ============================================================
# Full Verification
# ============================================================

def verify_full(
    calculated_file,
    reference_file
):

    print()
    print("=" * 60)
    print("                    VERIFICATION")
    print("=" * 60)

    print(
        f"Calculated file : {calculated_file}"
    )

    print(
        f"Reference file  : {reference_file}"
    )

    print(
        "\nComparing files..."
    )

    start = time.perf_counter()

    matched = 0
    mismatched = 0
    first_mismatch = None

    calculated_digits = 0
    reference_digits = 0

    # --------------------------------------------------------
    # Open both files
    # --------------------------------------------------------

    with open(
        calculated_file,
        "rb",
        buffering=CHUNK_SIZE
    ) as calculated:

        with open(
            reference_file,
            "rb",
            buffering=CHUNK_SIZE
        ) as reference:

            calculated_data = b""
            reference_data = b""

            calculated_pos = 0
            reference_pos = 0

            while True:

                # Fill calculated buffer
                if not calculated_data:

                    raw = calculated.read(
                        CHUNK_SIZE
                    )

                    if raw:
                        calculated_data = (
                            normalize_chunk(raw)
                        )

                # Fill reference buffer
                if not reference_data:

                    raw = reference.read(
                        CHUNK_SIZE
                    )

                    if raw:
                        reference_data = (
                            normalize_chunk(raw)
                        )

                # Both ended
                if (
                    not calculated_data
                    and not reference_data
                ):
                    break

                # One ended before the other
                if not calculated_data:

                    extra = len(
                        reference_data
                    )

                    mismatched += extra

                    if first_mismatch is None:
                        first_mismatch = (
                            matched
                            + mismatched
                            - extra
                        )

                    reference_digits += extra
                    reference_data = b""

                    continue

                if not reference_data:

                    extra = len(
                        calculated_data
                    )

                    mismatched += extra

                    if first_mismatch is None:
                        first_mismatch = (
                            matched
                            + mismatched
                            - extra
                        )

                    calculated_digits += extra
                    calculated_data = b""

                    continue

                # ------------------------------------------------
                # Compare available bytes
                # ------------------------------------------------

                length = min(
                    len(calculated_data),
                    len(reference_data)
                )

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

                                first_mismatch = (
                                    matched
                                    + mismatched
                                    - 1
                                )

                calculated_digits += length
                reference_digits += length

                calculated_data = (
                    calculated_data[length:]
                )

                reference_data = (
                    reference_data[length:]
                )

                # Progress every ~1 MB
                total_processed = min(
                    calculated_digits,
                    reference_digits
                )

                print(
                    f"\rCompared: "
                    f"{total_processed:,} digits",
                    end="",
                    flush=True
                )

    elapsed = time.perf_counter() - start

    print("\n")

    print(
        f"Calculated : {calculated_digits:,}"
    )

    print(
        f"Reference  : {reference_digits:,}"
    )

    print(
        f"Matched    : {matched:,}"
    )

    print(
        f"Mismatched : {mismatched:,}"
    )

    print(
        f"\nVerification time: "
        f"{elapsed:.4f} seconds"
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    if (
        mismatched == 0
        and calculated_digits == reference_digits
    ):

        print()
        print("✅ VERIFIED!")

        print(
            f"Semua {matched:,} digit "
            "cocok dengan reference."
        )

        return True

    print()
    print("❌ VERIFICATION FAILED!")

    if first_mismatch is not None:

        print(
            f"First mismatch position: "
            f"{first_mismatch:,}"
        )

    if calculated_digits != reference_digits:

        print(
            "\n⚠️ File memiliki jumlah digit "
            "yang berbeda."
        )

    return False


# ============================================================
# Main
# ============================================================

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

    if not Path(
        calculated_file
    ).exists():

        print(
            f"\n❌ File tidak ditemukan:"
        )

        print(
            calculated_file
        )

        return

    calculated_size = Path(
        calculated_file
    ).stat().st_size

    print(
        f"\nCalculated file size: "
        f"{calculated_size:,} bytes"
    )

    # --------------------------------------------------------
    # Download reference
    # --------------------------------------------------------

    if args.reference:
        reference_file = args.reference
        if not Path(reference_file).exists():
            print(f"\n❌ Reference file tidak ditemukan: {reference_file}")
            return
        print(f"\nUsing local reference: {reference_file}")
    else:
        reference_file = download_reference()

    if reference_file is None:

        print(
            "\n❌ Reference gagal di-download."
        )

        print(
            "Verification dibatalkan."
        )

        return

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verify_full(
        calculated_file,
        reference_file
    )


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":
    main()

