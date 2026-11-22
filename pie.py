from decimal import Decimal, getcontext
import time
import sys


# =========================
# PiProject v1 (legacy)
# Arctan (Machin-like) formula
# =========================

# Legacy implementation: simple, dependency-free, but O(digits^2).
# Recommended only for small digit counts. Use pi_project_v4.py for
# large calculations (Chudnovsky + binary splitting + GMPY2).


def calculate_pi(digits):
    # Extra precision to avoid error in the last digits.
    getcontext().prec = digits + 20

    start = time.perf_counter()

    def arctan_inverse(n):
        x = Decimal(1) / Decimal(n)
        x_squared = x * x

        total = Decimal(0)
        power = x
        k = 0

        while True:
            term = power / (2 * k + 1)

            if term < Decimal(10) ** -(digits + 15):
                break

            if k % 2 == 0:
                total += term
            else:
                total -= term

            power *= x_squared
            k += 1

        return total

    pi = (
        Decimal(16) * arctan_inverse(5)
        - Decimal(4) * arctan_inverse(239)
    )

    elapsed = time.perf_counter() - start

    # Exactly the requested number of digits.
    pi = format(pi, f".{digits}f")

    return pi, elapsed


def main(argv=None):

    print("=== PiProject ===")
    print("Real π Calculator\n")

    try:
        digits = int(input("How many digits of pi? "))

        if digits <= 0:
            raise ValueError("Number of digits must be greater than 0.")

    except ValueError:
        print("Invalid input.")
        return 1
    except EOFError:
        print("Input stream closed.")
        return 1

    print("\nCalculating...")
    print("Please wait...\n")

    pi, elapsed = calculate_pi(digits)

    # =========================
    # Save result
    # =========================

    filename = f"pi_{digits}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(pi)

    # =========================
    # Result
    # =========================

    print("π =")
    print(pi)

    print("\n=========================")
    print(f"Time  : {elapsed:.4f} seconds")
    print(f"Digits: {digits:,}")
    print(f"Speed : {digits / elapsed:,.0f} digits/sec")
    print(f"Saved : {filename}")
    print("=========================")

    return 0


# =========================
# Start
# =========================

if __name__ == "__main__":
    sys.exit(main())
