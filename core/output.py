SUMMARY_SHEET = 'Summary (%s)'


def _format_date(date):
    return date.strftime('%Y-%m-%d')


def write_storage_summary(writer, summary_date, storage_by_cat, storage_by_type):
    storage_by_cat = storage_by_cat[['Size', 'Buffer', 'Total', 'Group']]  # select columns
    writer.write_data_frame(storage_by_cat, SUMMARY_SHEET % _format_date(summary_date), 'Storage Category')
    writer.write_data_frame(storage_by_type, SUMMARY_SHEET % _format_date(summary_date), 'Storage Type')


def write_compute_summary(writer, summary_date, compute_summary):
    writer.write_data_frame(compute_summary, SUMMARY_SHEET % _format_date(summary_date), 'Service')


def write_raw_data(writer, usage, storage):
    writer.write_data_frame(usage, 'Usage', 'Dates')
    writer.write_data_frame(storage, 'Storage', 'Dates')

