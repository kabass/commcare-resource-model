from core.utils import format_date

COMPARISONS_SHEET = 'Comparisons'
SUMMARY_SHEET = 'Summary (%s)'

STORAGE_GROUP_INDEX = 'Storage Group'
STORAGE_CAT_INDEX = 'Storage Category'
SERVICE_INDEX = 'Service'


def write_summary_comparisons(config, writer, comparisons, prefix=''):
    storage_by_cat, storage_by_group, compute = comparisons
    sheet = '%s%s' % (prefix, COMPARISONS_SHEET)

    storage_cat_header = '%sStorage by Category (%s)' % (prefix, config.storage_display_unit)
    writer.write_data_frame(storage_by_cat, sheet, STORAGE_CAT_INDEX, storage_cat_header, has_total_row=True)

    storage_group_header = '%sStorage by Group (%s)' % (prefix, config.storage_display_unit)
    writer.write_data_frame(storage_by_group, sheet, STORAGE_GROUP_INDEX, storage_group_header)
    comparison_header = '%sCompute' % prefix
    writer.write_data_frame(compute, sheet, SERVICE_INDEX, comparison_header, has_total_row=True)


def write_summary_data_new(config, writer, summary_date, summary_data):
    writer.write_data_frame(summary_data.service_summary, SUMMARY_SHEET % format_date(summary_date), 'Service', 'Service Summary', has_total_row=True)
    storage_group_header = 'Storage by Group (%s)' % config.storage_display_unit
    writer.write_data_frame(summary_data.storage_by_group, SUMMARY_SHEET % format_date(summary_date), STORAGE_GROUP_INDEX, storage_group_header)


def write_usage_data(writer, usage):
    writer.write_data_frame(usage, 'Usage', 'Dates')

