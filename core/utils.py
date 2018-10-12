import math
import re

byte_map = {
    'KB': 1000.0,
    'MB': 1000.0 ** 2,
    'GB': 1000.0 ** 3,
    'TB': 1000.0 ** 4
}


def format_date(date):
    return date.strftime('%Y-%m-%d')


def to_storage_display_unit(unit):
    bytes_per_unit = byte_map[unit]

    def _inner(bytes_, bytes_per_unit=bytes_per_unit):
        return bytes_ / bytes_per_unit

    return _inner


def from_storage_display_unit(unit):
    bytes_per_unit = byte_map[unit]

    def _inner(bytes_, bytes_per_unit=bytes_per_unit):
        return bytes_ * bytes_per_unit

    return _inner


def storage_display_to_bytes(display_value):
    pattern = re.compile('(?P<value>\d+)\s*(?P<units>(?:K|M|G|T)B)')
    match = pattern.match(display_value)
    if not match:
        return int(display_value)
    value = match.group('value')
    units = match.group('units')
    return from_storage_display_unit(units)(value)


def tenth_round(value):
    """Remove some precision by rounding to the power of 10 nearest
    to 10% of the value
    """
    if not value:
        return value
    tenth = value * 0.1
    pow = round(math.log10(tenth))
    round_val = 10 ** pow
    return math.ceil(value / round_val) * round_val
