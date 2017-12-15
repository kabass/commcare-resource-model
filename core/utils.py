BYTES_PER_GB = 1000.0 ** 3


def format_date(date):
    return date.strftime('%Y-%m-%d')


def bytes_to_gb(bytes):
    return bytes / BYTES_PER_GB
