import math

BYTES_PER_GB = 1000.0 ** 3


def format_date(date):
    return date.strftime('%Y-%m-%d')


def bytes_to_gb(bytes):
    return bytes / BYTES_PER_GB


def tenth_round(value):
    """Remove some precision by rounding to the power of 10 nearest
    to 10% of the value
    """
    tenth = value * 0.1
    pow = round(math.log10(tenth))
    round_val = 10 ** pow
    return math.ceil(value / round_val) * round_val
