# Verification Methodology

## Verification Statuses

PiProject uses explicit, unambiguous verification statuses:

| Status | Meaning |
|--------|---------|
| `CALCULATED` | Value was computed; no verification performed |
| `STRUCTURE_VALID` | Passes format/length/digit checks |
| `PREFIX_VERIFIED` | Matches known reference for checked prefix only |
| `FULLY_VERIFIED` | Every digit compared against a trustworthy reference |
| `INDEPENDENTLY_VERIFIED` | Confirmed by an independent algorithm (e.g. BBP) |
| `VERIFICATION_FAILED` | A mismatch or error was detected |

**Never** report `FULLY_VERIFIED` when only a prefix has been checked.

## Verification Pipeline

1. **Structural validation** — checks format, integer part = "3", exact digit count, all digits
2. **Built-in prefix check** — compares against the first 1,000 known decimal digits
3. **File-to-file reference comparison** — full digit-by-digit comparison against a reference file
4. **BBP spot checks** — independent hexadecimal digit verification at arbitrary positions

## Reference Integrity

- Reference files are validated with SHA-256 fingerprints
- The expected SHA-256 must come from a trustworthy source
- A matching SHA-256 establishes file identity, not mathematical correctness
- Reference provenance is tracked in verification reports

## Limitations

- The built-in prefix check covers only the first 1,000 digits
- For digits > 1,000, full verification requires an external reference file
- BBP spot checks confirm individual positions, not complete ranges
