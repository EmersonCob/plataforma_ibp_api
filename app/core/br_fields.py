from __future__ import annotations


def digits_only(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(char for char in str(value) if char.isdigit())
    return digits or None


def normalize_cpf(value: str | None) -> str | None:
    digits = digits_only(value)
    if not digits:
        return None
    return digits[:11]


def normalize_phone(value: str | None) -> str | None:
    digits = digits_only(value)
    if not digits:
        return None
    if len(digits) > 11 and digits.startswith("55"):
        digits = digits[-11:]
    return digits[:11]


def normalize_zip_code(value: str | None) -> str | None:
    digits = digits_only(value)
    if not digits:
        return None
    return digits[:8]


def format_cpf(value: str | None) -> str | None:
    digits = normalize_cpf(value)
    if not digits:
        return None
    if len(digits) < 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def format_phone(value: str | None) -> str | None:
    digits = normalize_phone(value)
    if not digits:
        return None
    if len(digits) <= 2:
        return digits
    if len(digits) <= 6:
        return f"({digits[:2]}) {digits[2:]}"
    if len(digits) <= 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return f"({digits[:2]}) {digits[2:7]}-{digits[7:11]}"


def format_zip_code(value: str | None) -> str | None:
    digits = normalize_zip_code(value)
    if not digits:
        return None
    if len(digits) <= 5:
        return digits
    return f"{digits[:5]}-{digits[5:8]}"
