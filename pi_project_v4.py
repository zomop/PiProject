import gmpy2
import time
import sys
from pathlib import Path

gmpy2.get_context().precision = 128


# ============================================================
# PiProject v4
# Chudnovsky + Binary Splitting + GMP
# Designed for large calculations
# ============================================================

C = 640320
C3_OVER_24 = C**3 // 24
A = 13591409
B = 545140134


def binary_split(a, b):
    """
    Chudnovsky binary splitting.
    Returns P, Q, T.
    """

    if b - a == 1:
        if a == 0:
            return (
                gmpy2.mpz(1),
                gmpy2.mpz(1),
                gmpy2.mpz(A),
            )

        k = gmpy2.mpz(a)

        P = (
            (6 * k - 5)
            * (2 * k - 1)
            * (6 * k - 1)
        )

        Q = k**3 * C3_OVER_24

        T = P * (A + B * k)

        if a & 1:
            T = -T

        return P, Q, T

    m = (a + b) // 2

    P1, Q1, T1 = binary_split(a, m)
    P2, Q2, T2 = binary_split(m, b)

    P = P1 * P2
    Q = Q1 * Q2
    T = T1 * Q2 + P1 * T2

    return P, Q, T


def calculate_pi(digits):
    start = time.perf_counter()

    # Chudnovsky ≈ 14 digits / term
    terms = digits // 14 + 1

    print()
    print(f"Terms required : {terms:,}")
    print("Running binary splitting...")

    P, Q, T = binary_split(0, terms)

    print("Binary splitting complete.")
    print("Calculating square root...")

    # Scale factor:
    # pi = 426880 * sqrt(10005) * Q / T
    #
    # Use GMP integer arithmetic instead of Decimal.

    scale = gmpy2.mpz(10) ** (digits + 20)

    sqrt_10005 = gmpy2.isqrt(
        gmpy2.mpz(10005) * scale * scale
    )

    numerator = (
        gmpy2.mpz(426880)
        * sqrt_10005
        * Q
    )

    pi_scaled = numerator // T

    # Convert scaled integer into decimal representation
    s = str(pi_scaled)

    # Remove guard digits
    s = s[:-20]

    if len(s) <= digits:
        s = s.zfill(digits + 1)

    integer_part = s[:-digits]
    decimal_part = s[-digits:]

    pi_string = integer_part + "." + decimal_part

    elapsed = time.perf_counter() - start

    return pi_string, elapsed


def verify_pi(pi_string, digits):
    """
    Basic sanity verification:
    - correct decimal length
    - starts with known digits
    """

    expected_prefix = (
        "3.14159265358979323846264338327950288419716939937510"
    )

    if not pi_string.startswith(expected_prefix):
        return False

    if len(pi_string.split(".")[1]) != digits:
        return False

    return True


def save_pi(pi_string, digits):
    filename = Path(f"pi_{digits}.txt")

    print(f"Saving: {filename}")

    with filename.open(
        "w",
        encoding="ascii",
        buffering=1024 * 1024,
    ) as f:
        f.write(pi_string)

    return filename


def main():

    print("=" * 60)
    print("                    PiProject v4")
    print("       Chudnovsky + Binary Splitting + GMP")
    print("=" * 60)

    try:
        digits = int(
            input("\nBerapa digit π yang ingin dihitung? ")
        )

    except ValueError:
        print("\n❌ Input harus berupa angka.")
        return

    if digits <= 0:
        print("\n❌ Digit harus lebih dari 0.")
        return

    if digits > 10_000_000:
        print(
            "\n⚠️ Target lebih dari 10 juta digit "
            "bisa membutuhkan RAM besar."
        )

        confirm = input(
            "Tetap lanjut? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("Dibatalkan.")
            return

    print("\nCalculating π...")
    print("Method: Chudnovsky + Binary Splitting + GMP")

    try:
        pi, elapsed = calculate_pi(digits)

    except MemoryError:
        print("\n❌ RAM tidak cukup.")
        return

    except Exception as e:
        print("\n❌ Calculation error:")
        print(type(e).__name__, e)
        return

    print("\nCalculation complete.")

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    print("\nVerifying...")

    verified = verify_pi(pi, digits)

    if not verified:
        print("❌ Verification FAILED!")
        return

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:
        filename = save_pi(pi, digits)

    except OSError as e:
        print("\n❌ Gagal menyimpan file:")
        print(e)
        return

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_digits = len(pi.replace(".", ""))
    decimal_digits = len(pi.split(".")[1])

    speed = decimal_digits / elapsed

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("                       RESULT")
    print("=" * 60)

    print(f"Digits requested : {digits:,}")
    print(f"Total digits     : {total_digits:,}")
    print(f"Decimal digits   : {decimal_digits:,}")
    print()
    print(f"Time             : {elapsed:.4f} seconds")
    print(f"Speed            : {speed:,.2f} digits/sec")
    print()
    print(f"Saved            : {filename}")

    print("=" * 60)

    print("\nπ preview:")
    print(pi[:120] + "...")

    print("\n" + "=" * 60)
    print("✅ VERIFIED!")
    print("=" * 60)


if __name__ == "__main__":
    main()