from decimal import Decimal, getcontext
import time


# ============================================================
# PiProject v3
# Chudnovsky Formula + Binary Splitting
# ============================================================


def binary_split(a, b):
    """
    Binary splitting untuk Chudnovsky.

    Menghasilkan P, Q, T untuk range [a, b).
    """

    if b - a == 1:

        if a == 0:
            P = 1
            Q = 1
            T = 13591409

        else:
            P = (
                (6 * a - 5)
                * (2 * a - 1)
                * (6 * a - 1)
            )

            # Chudnovsky:
            # Q = a^3 * 640320^3 / 24
            Q = (
                a ** 3
                * 640320 ** 3
                // 24
            )

            T = P * (
                13591409
                + 545140134 * a
            )

            # (-1)^a
            if a % 2:
                T = -T

        return P, Q, T

    m = (a + b) // 2

    P1, Q1, T1 = binary_split(a, m)
    P2, Q2, T2 = binary_split(m, b)

    P = P1 * P2
    Q = Q1 * Q2

    T = (
        T1 * Q2
        + P1 * T2
    )

    return P, Q, T


# ============================================================
# Calculate Pi
# ============================================================

def calculate_pi(digits):

    # Chudnovsky menghasilkan ±14 digit per term
    terms = digits // 14 + 1

    # Extra precision
    getcontext().prec = digits + 30

    start = time.perf_counter()

    print(f"\nTerms required : {terms:,}")
    print("Running binary splitting...")

    P, Q, T = binary_split(0, terms)

    print("Calculating square root...")

    C = (
        Decimal(426880)
        * Decimal(10005).sqrt()
    )

    pi = (
        C
        * Decimal(Q)
        / Decimal(T)
    )

    elapsed = time.perf_counter() - start

    # Format tepat sejumlah digit setelah decimal
    pi_string = format(
        pi,
        f".{digits}f"
    )

    return pi_string, elapsed


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 55)
    print("                 PiProject v3")
    print("       Chudnovsky + Binary Splitting")
    print("=" * 55)

    try:

        digits = int(
            input(
                "\nBerapa digit π yang ingin dihitung? "
            )
        )

    except ValueError:

        print("\n❌ Input harus berupa angka.")
        return

    if digits <= 0:

        print(
            "\n❌ Jumlah digit harus lebih dari 0."
        )
        return

    if digits > 10_000_000:

        print(
            "\n⚠️ Target di atas 10 juta digit "
            "bisa membutuhkan RAM sangat besar."
        )

        confirm = input(
            "Tetap lanjut? (y/n): "
        ).lower()

        if confirm != "y":

            print("Dibatalkan.")
            return

    print("\nCalculating π...")
    print(
        "Method: Chudnovsky + Binary Splitting"
    )

    try:

        pi, elapsed = calculate_pi(
            digits
        )

    except MemoryError:

        print(
            "\n❌ RAM tidak cukup."
        )
        return

    except Exception as e:

        print(
            "\n❌ Calculation error:"
        )
        print(e)
        return

    # ========================================================
    # Save
    # ========================================================

    filename = f"pi_{digits}.txt"

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(pi)

    except OSError as e:

        print(
            "\n❌ Gagal menyimpan file:"
        )
        print(e)
        return

    # ========================================================
    # Benchmark
    # ========================================================

    total_digits = len(
        pi.replace(".", "")
    )

    decimal_digits = len(
        pi.split(".")[1]
    )

    speed = (
        decimal_digits
        / elapsed
    )

    # ========================================================
    # Result
    # ========================================================

    print("\n")
    print("=" * 55)
    print("                    RESULT")
    print("=" * 55)

    print(
        f"Digits requested : {digits:,}"
    )

    print(
        f"Total digits     : {total_digits:,}"
    )

    print(
        f"Decimal digits   : {decimal_digits:,}"
    )

    print(
        f"\nTime             : "
        f"{elapsed:.4f} seconds"
    )

    print(
        f"Speed            : "
        f"{speed:,.2f} digits/sec"
    )

    print(
        f"\nSaved            : "
        f"{filename}"
    )

    print("=" * 55)

    # ========================================================
    # Preview
    # ========================================================

    print("\nπ preview:")

    if len(pi) > 120:

        print(
            pi[:120]
            + "..."
        )

    else:

        print(pi)

    print(
        "\n✅ Calculation complete."
    )


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":
    main()