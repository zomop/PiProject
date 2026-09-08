from decimal import Decimal, getcontext
import time


def calculate_pi(digits):
    # Extra precision untuk mencegah error di digit terakhir
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

    # Tepat jumlah digit yang diminta
    pi = format(pi, f".{digits}f")

    return pi, elapsed


# =========================
# PiProject
# =========================

print("=== PiProject ===")
print("Real π Calculator\n")

try:
    digits = int(input("Berapa digit π? "))

    if digits <= 0:
        raise ValueError("Jumlah digit harus lebih dari 0.")

except ValueError:
    print("Input tidak valid.")
    exit()


print("\nCalculating...")
print("Mohon tunggu...\n")

pi, elapsed = calculate_pi(digits)


# =========================
# Simpan hasil
# =========================

filename = f"pi_{digits}.txt"

with open(filename, "w", encoding="utf-8") as f:
    f.write(pi)


# =========================
# Hasil
# =========================

print("π =")
print(pi)

print("\n=========================")
print(f"Time  : {elapsed:.4f} seconds")
print(f"Digits: {digits:,}")
print(f"Speed : {digits / elapsed:,.0f} digits/sec")
print(f"Saved : {filename}")
print("=========================")