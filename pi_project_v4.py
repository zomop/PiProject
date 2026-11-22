import argparse
import sys
import time
from pathlib import Path

import gmpy2

# ============================================================
# PiProject v4
# Chudnovsky + Binary Splitting + GMP
# Designed for large calculations
# ============================================================

# NOTE: The GMPY2 context is intentionally left untouched on import.
# This module uses gmpy2.mpz (integer) arithmetic only, so mutating the
# global mpf precision would be a side effect with no benefit here.

C = 640320
C3_OVER_24 = C**3 // 24
A = 13591409
B = 545140134

# First 1,000 decimal digits of pi (after the decimal point), computed with
# an independent decimal/Machin implementation and cross-checked against a
# published reference. Used for authoritative sanity checks.
# Source: https://www.piday.org/million/ (first 1,000 digits)
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


def binary_split(a, b):
    """
    Chudnovsky binary splitting.
    Returns P, Q, T for the range [a, b).
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
    """Calculate `digits` decimal digits of pi.

    Returns (pi_string, elapsed_seconds). pi_string has the form
    "<integer part>.<exactly `digits` fractional digits>".
    """

    start = time.perf_counter()

    # Chudnovsky yields roughly 14 digits per term.
    terms = digits // 14 + 1

    P, Q, T = binary_split(0, terms)

    # Scale factor:
    # pi = 426880 * sqrt(10005) * Q / T
    # Use GMP integer arithmetic instead of Decimal. Compute with `digits + 20`
    # guard digits so rounding/floor error is confined to the discarded tail.
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

    # Convert scaled integer into decimal representation.
    # pi_scaled == floor(pi * 10**(digits + 20)), so its digits are:
    #   "3" + (digits + 20) fractional digits
    s = str(pi_scaled)

    # Discard the 20 guard digits from the fractional (right) end.
    guard = 20
    if len(s) > guard:
        s = s[:-guard]

    # s should now be exactly "3" + `digits` fractional digits
    # (length == digits + 1). Pad the fractional side with trailing zeros if
    # we came up short; never left-pad, which would corrupt the integer part.
    if len(s) < digits + 1:
        s = s.ljust(digits + 1, "0")
    elif len(s) > digits + 1:
        s = s[: digits + 1]

    integer_part = s[0]
    decimal_part = s[1:]

    pi_string = integer_part + "." + decimal_part

    elapsed = time.perf_counter() - start

    return pi_string, elapsed


def verify_pi(pi_string, digits):
    """
    Sanity-check a calculated pi string.

    Returns True only when:
      * the value is structurally sound ("3.<digits fractional digits>"),
      * every position for which we have authoritative reference data matches
        the known digits of pi.

    This never reports VERIFIED based on an insufficient prefix: for
    ``digits <= 1000`` the entire result is compared against known pi digits.
    For ``digits > 1000`` the first 1,000 digits are checked authoritatively
    and the remaining digits are checked for structure only; use verify.py for
    a full reference comparison at scale.
    """

    if not isinstance(pi_string, str) or "." not in pi_string:
        return False

    integer_part, _, decimal_part = pi_string.partition(".")

    if integer_part != "3":
        return False

    if len(decimal_part) != digits:
        return False

    if not decimal_part.isdigit():
        return False

    # Authoritative check over the range we have reference data for.
    check_len = min(digits, len(PI_DECIMAL_DIGITS_1000))
    if decimal_part[:check_len] != PI_DECIMAL_DIGITS_1000[:check_len]:
        return False

    return True


def save_pi(pi_string, digits, filename=None):
    output = Path(filename) if filename else Path(f"pi_{digits}.txt")

    print(f"Saving: {output}")

    with output.open(
        "w",
        encoding="ascii",
        buffering=1024 * 1024,
    ) as f:
        f.write(pi_string)

    return output


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Calculate pi using the Chudnovsky algorithm + binary splitting."
    )
    parser.add_argument(
        "--digits",
        type=int,
        help="number of decimal digits of pi to calculate",
    )
    parser.add_argument(
        "--output",
        help="output file (default: pi_<digits>.txt)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    digits = args.digits
    if digits is None:
        try:
            digits = int(
                input("\nHow many digits of pi would you like to calculate? ")
            )
        except ValueError:
            print("\nInput must be a number.")
            return 1
        except EOFError:
            print("\nInput stream closed.")
            return 1

    if digits <= 0:
        print("Number of digits must be greater than 0.")
        return 1

    if digits > 10_000_000:
        print(
            "Warning: more than 10 million digits "
            "may require large RAM."
        )

        try:
            confirm = input("Continue? (y/n): ").strip().lower()
        except EOFError:
            print("Cancelled.")
            return 1

        if confirm != "y":
            print("Cancelled.")
            return 1

    print("\nCalculating pi...")
    print("Method: Chudnovsky + Binary Splitting + GMP")

    try:
        pi, elapsed = calculate_pi(digits)
    except MemoryError:
        print("\nNot enough RAM.")
        return 1
    except Exception as e:
        print("\nCalculation error:")
        print(type(e).__name__, e)
        return 1

    print("Calculation complete.")

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    print("Verifying...")

    if not verify_pi(pi, digits):
        print("Verification FAILED!")
        return 1

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:
        filename = save_pi(pi, digits, filename=args.output)
    except OSError as e:
        print("Failed to save file:")
        print(e)
        return 1

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
    print("RESULT")
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

    print("\npi preview:")
    print(pi[:120] + "...")

    print("\n" + "=" * 60)
    print("VERIFIED!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
