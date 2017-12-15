import argparse

from core.config import config_from_path
from core.generate import generate_usage_data, generate_storage_data, generate_compute_data
from core.output import write_storage_summary, write_compute_summary, write_raw_data
from core.summarize import summarize_storage_data, summarize_compute_data
from core.writers import ConsoleWriter
from core.writers import ExcelWriter

SUMMARY_SHEET = 'Summary'


if __name__ == '__main__':
    parser = argparse.ArgumentParser('CommCare Cluster Model')
    parser.add_argument('config', help='Path to config file')
    parser.add_argument('-o', '--output', help='Write output to Excel file at this path.')

    args = parser.parse_args()

    config = config_from_path(args.config)
    usage = generate_usage_data(config)
    storage = generate_storage_data(config, usage)
    compute = generate_compute_data(config, usage)

    summary_date = storage.iloc[-1].name  # summarize at final date

    if args.output:
        writer = ExcelWriter(args.output)
    else:
        writer = ConsoleWriter()

    storage_by_cat, storage_by_type = summarize_storage_data(config, summary_date, storage)
    compute_summary = summarize_compute_data(config, summary_date, compute)
    write_storage_summary(writer, storage_by_cat, storage_by_type)
    write_compute_summary(writer, compute_summary)
    if args.output:
        # only write raw data if writing to Excel
        write_raw_data(writer, usage, storage)
    writer.save()
