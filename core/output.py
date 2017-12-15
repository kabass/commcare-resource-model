SUMMARY_SHEET = 'Summary'


def write_storage_summary(writer, storage_by_cat, storage_by_type):
    storage_by_cat = storage_by_cat[['Size', 'Buffer', 'Total', 'Is SSD']]  # select columns
    writer.write_data_frame(storage_by_cat, SUMMARY_SHEET, 'Storage Category')
    writer.write_data_frame(storage_by_type, SUMMARY_SHEET, 'Storage Type')


def write_compute_summary(writer, compute_summary):
    writer.write_data_frame(compute_summary, SUMMARY_SHEET, 'Service')


def write_raw_data(writer, usage, storage):
    writer.write_data_frame(usage, 'Usage', 'Dates')
    writer.write_data_frame(storage, 'Storage', 'Dates')

