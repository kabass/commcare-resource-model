from core.utils import format_date

COMPARISONS_SHEET = 'Comparisons'
SUMMARY_SHEET = 'Summary (%s)'

STORAGE_GROUP_INDEX = 'Storage Group'
STORAGE_CAT_INDEX = 'Storage Category'
SERVICE_INDEX = 'Service'


def write_summary_comparisons(config, writer, comparisons):
    storage_by_cat, storage_by_group, compute = comparisons

    storage_cat_header = 'Storage by Category (%s)' % config.storage_display_unit
    writer.write_data_frame(storage_by_cat, COMPARISONS_SHEET, STORAGE_CAT_INDEX, storage_cat_header, has_total_row=True)

    storage_group_header = 'Storage by Group (%s)'  % config.storage_display_unit
    writer.write_data_frame(storage_by_group, COMPARISONS_SHEET, STORAGE_GROUP_INDEX, storage_group_header)
    writer.write_data_frame(compute, COMPARISONS_SHEET, SERVICE_INDEX, 'Compute Comparison', has_total_row=True)


def write_summary_data(config, writer, summary_date, summary_data):
    write_storage_summary(config, writer, summary_date, summary_data.storage)
    write_compute_summary(writer, summary_date, summary_data.compute)


def write_storage_summary(config, writer, summary_date, storage_summary):
    storage_by_cat = storage_summary.by_category[
        ['Size', 'Storage Buffer', 'Estimation Buffer', 'Total', 'Rounded Total', 'Group']  # select columns
    ]
    storage_cat_header = 'Storage by Category (%s)' % config.storage_display_unit
    writer.write_data_frame(storage_by_cat, SUMMARY_SHEET % format_date(summary_date), STORAGE_CAT_INDEX, storage_cat_header)
    storage_group_header = 'Storage by Group (%s)' % config.storage_display_unit
    writer.write_data_frame(storage_summary.by_group, SUMMARY_SHEET % format_date(summary_date), STORAGE_GROUP_INDEX, storage_group_header)


def write_compute_summary(writer, summary_date, compute_summary):
    writer.write_data_frame(compute_summary, SUMMARY_SHEET % format_date(summary_date), SERVICE_INDEX, 'Compute')


def write_raw_data(writer, usage, storage, compute):
    writer.write_data_frame(usage, 'Usage', 'Dates')
    writer.write_data_frame(storage, 'Storage', 'Dates')
    writer.write_data_frame(compute, 'Compute', 'Dates')

