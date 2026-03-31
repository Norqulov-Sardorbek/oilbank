import re

UZ_CAR_REGEX = re.compile(
    r"^("
    r"(0[1-9]|[1-9][0-9])\s?[A-Z]\s?\d{3}\s?[A-Z]{2}|"  # Jismoniy: 01 A 123 BC
    r"(0[1-9]|[1-9][0-9])\s?[A-Z]\s?\d{6}|"  # Jismoniy 6 raqam: 01 A 123456 or 01O000000
    r"(0[1-9]|[1-9][0-9])\s?[A-Z]{3}\s?\d{3}|"  # Yuridik variant: 01 OOO 123
    r"(0[1-9]|[1-9][0-9])\s?\d{3}\s?[A-Z]{3}|"  # Yuridik: 01 123 ABC
    r"CMD\s?\d{3}|"  # Diplomatic
    r"D\s?\d{3}|"  # Diplomatic
    r"UN\s?\d{3}|"  # United Nations
    r"H\s?\d{4}|"  # Special
    r"(0[1-9]|[1-9][0-9])\s?\d{3}\s?[A-Z]{2}"  # 01 123 AB
    r")$"
)


def is_valid_uz_car_number(number: str) -> bool:
    """
    Check if the given number is a valid Uzbek car registration number.
    """
    if not number:
        return False
    normalized = number.upper().strip().replace("  ", " ")
    return bool(UZ_CAR_REGEX.match(normalized))
