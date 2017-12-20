import argparse
from collections import namedtuple
from datetime import datetime

from core.config import config_from_path
from core.generate import generate_usage_data, generate_storage_data, generate_compute_data
from core.output import write_storage_summary, write_compute_summary, write_raw_data, write_summary_data, \
    write_summary_comparisons
from core.summarize import summarize_storage_data, summarize_compute_data, compare_summaries, incremental_summaries
from core.writers import ConsoleWriter
from core.writers import ExcelWriter
import pandas as pd

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


SummaryData = namedtuple('SummaryData', 'storage compute')


if __name__ == '__main__':
    parser = argparse.ArgumentParser('CommCare Cluster Model')
    parser.add_argument('config', help='Path to config file')
    parser.add_argument('-o', '--output', help='Write output to Excel file at this path.')

    args = parser.parse_args()

    pd.options.display.float_format = '{:.1f}'.format

    config = config_from_path(args.config)
    usage = generate_usage_data(config)
    compute = generate_compute_data(config, usage)
    storage = generate_storage_data(config, usage, compute)

    if config.summary_dates:
        summary_dates = config.summary_date_vals
    else:
        summary_dates = [usage.iloc[-1].name]  # summarize at final date

    is_excel = bool(args.output)
    if is_excel:
        writer = ExcelWriter(args.output)
    else:
        writer = ConsoleWriter()

    summaries = {}
    for date in summary_dates:
        storage_summary = summarize_storage_data(config, date, storage)
        compute_summary = summarize_compute_data(config, date, compute)
        summaries[date] = SummaryData(storage_summary, compute_summary)

    if len(summary_dates) == 1:
        date = summary_dates[0]
        summary_data = summaries[date]
        write_summary_data(config, writer, date, summary_data)
    else:
        summary_comparisons = compare_summaries(summaries)
        incrementals = incremental_summaries(summary_comparisons, summary_dates)
        write_summary_comparisons(config, writer, incrementals, prefix='Incremental ')
        write_summary_comparisons(config, writer, summary_comparisons)

        if is_excel:
            for date, summary_data in summaries.items():
                write_summary_data(config, writer, date, summary_data)

    if is_excel:
        # only write raw data if writing to Excel
        write_raw_data(writer, usage, storage, compute)

        with open(args.config, 'r') as f:
            config_string = f.read()
            writer.write_config_string(config_string)
    writer.save()
