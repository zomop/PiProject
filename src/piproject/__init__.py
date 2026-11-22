"""PiProject — High-performance π computation and independent verification.

PiProject computes π to millions of digits using the Chudnovsky algorithm
with binary splitting and GMPY2 arbitrary-precision arithmetic, and verifies
results through an independent verification engine.

Project: https://github.com/zomop/PiProject
"""

__version__ = "2.0.0"
__project__ = "PiProject"

# ---------------------------------------------------------------------------
# Verification statuses (explicit, never ambiguous)
# ---------------------------------------------------------------------------

CALCULATED = "CALCULATED"
STRUCTURE_VALID = "STRUCTURE_VALID"
PREFIX_VERIFIED = "PREFIX_VERIFIED"
FULLY_VERIFIED = "FULLY_VERIFIED"
INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED"
VERIFICATION_FAILED = "VERIFICATION_FAILED"

__all__ = [
    "__version__",
    "__project__",
    "CALCULATED",
    "STRUCTURE_VALID",
    "PREFIX_VERIFIED",
    "FULLY_VERIFIED",
    "INDEPENDENTLY_VERIFIED",
    "VERIFICATION_FAILED",
]
