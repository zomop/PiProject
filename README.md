[PiProject README.md](https://github.com/user-attachments/files/31954758/PiProject.README.md)

# PiProject

## About This Project

**PiProject** is an open-source Python project created by **zomop** on **September 8, 2026**.

The project focuses on high-precision computation of **π (pi)** using **Python** and **GMPY2**, with techniques such as the **Chudnovsky algorithm** and **binary splitting**.

PiProject also includes a verification tool for comparing calculated digits against a reference. The project has successfully calculated and verified **10,000,000 digits of π**, with **0 mismatches**.

This project is open source and available for anyone to study, modify, improve, and contribute to.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [FAQ](#faq)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Features

- High-precision calculation of π
- Chudnovsky algorithm
- Binary splitting
- GMPY2 arbitrary-precision arithmetic
- Calculation of millions of digits
- Digit-by-digit verification
- Reference comparison
- Automatic output to a `.txt` file
- Open-source and free to modify

### Tech Stack

- **Python 3**
- **GMPY2**
- **Chudnovsky Algorithm**
- **Binary Splitting**

## Installation

Clone the repository:

```bash
git clone https://github.com/zomop/PiProject.git
cd PiProject
```

Install the required Python dependency:

```bash
pip install -r requirements.txt
```

## Usage

Run the latest π calculator:

```bash
python pi_project_v4.py
```

The program calculates π using the Chudnovsky algorithm and saves the result to a text file.

To verify the calculated result:

```bash
python verify.py
```

The verification tool compares the calculated digits against a reference and reports the number of matched and mismatched digits.

### Example

```text
3.14159265358979323846264338327950288419716939937510582097494459230781...
```

### Verification Result

```text
==============================
VERIFICATION
==============================
Calculated : 10,000,000
Reference  : 10,000,000
Matched    : 10,000,000
Mismatched : 0

Verification time: 0.0474 seconds

✅ VERIFIED!
```

The result contains **10,000,000 characters** including the `3` before the decimal point.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch:

```bash
git checkout -b feature/amazing-feature
```

3. Commit your changes:

```bash
git commit -m "Add amazing feature"
```

4. Push to the branch:

```bash
git push origin feature/amazing-feature
```

5. Open a Pull Request

You can contribute by improving calculation performance, reducing memory usage, improving verification, adding features, or improving documentation.

## FAQ

#### How many digits can PiProject calculate?

PiProject has been tested successfully with **10,000,000 digits of π**.

#### How is π calculated?

The project uses the **Chudnovsky algorithm** combined with **binary splitting** and GMPY2 for high-precision arithmetic.

#### Is the 10-million-digit result verified?

Yes. The calculated result was compared against a reference with **10,000,000 characters**, resulting in **10,000,000 matches and 0 mismatches**.

#### Can I modify the project?

Yes. PiProject is open source and can be studied, modified, and improved according to the repository's license.

## Acknowledgments

- **GMPY2** — High-performance arbitrary-precision arithmetic
- **Chudnovsky Brothers** — Chudnovsky algorithm for calculating π
- **Python** — Programming language used for the project
- Reference data used for verification

## License

This project is open source.

A license file should be included in the repository to define the permissions for using, modifying, and distributing the code.

---

Made with ❤️ by **[zomop](https://github.com/zomop)**

**September 8, 2026**
